import os
import json
import re
import logging
from functools import lru_cache
from typing import Dict, List, Any, Tuple

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_community.vectorstores import Chroma
from langchain_community.llms import Ollama as OllamaLLM
from langchain_community.embeddings import OllamaEmbeddings, HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate
from langchain.schema import BaseOutputParser

# Optional OpenAI provider
try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    HAS_OPENAI = True
except Exception:
    HAS_OPENAI = False

# Optional local HF text generation
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM

# Local modules
import indexer as main_indexer
import rag_alt.indexer as alt_indexer

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Settings
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "HF").upper()  # HF | OPENAI | OLLAMA
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")  # For OPENAI
EMBED_MODEL_OPENAI = os.getenv("EMBED_MODEL_OPENAI", "text-embedding-3-small")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "tinyllama")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
HF_LLM_MODEL = os.getenv("HF_LLM_MODEL", "google/flan-t5-small")
HF_EMBED_MODEL = os.getenv("HF_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

CHROMA_DIR_MAIN = os.getenv("CHROMA_DIR_MAIN", "/tmp/chroma_main")
CHROMA_DIR_ALT = os.getenv("CHROMA_DIR_ALT", "/tmp/chroma_alt")

# Ensure dirs exist
os.makedirs(CHROMA_DIR_MAIN, exist_ok=True)
os.makedirs(CHROMA_DIR_ALT, exist_ok=True)


class AdvancedOutputParser(BaseOutputParser):
    def __init__(self, brand_name: str):
        self.brand_name = brand_name

    def parse(self, text: str) -> str:
        t = re.sub(r"\[.*?\]", "", text)
        t = re.sub(r"\*+\s?", "", t)
        t = re.sub(r"\n+", "\n", t)

        for marker in ["MISSION", "VOCABULAIRE", "# "]:
            if marker in t:
                parts = re.split(r"Réponse\s*:|\*\*Réponse\s*:?\*\*", t)
                if len(parts) > 1:
                    t = parts[-1].strip()

        sentences = [s.strip() for s in t.split(". ") if s.strip()]
        uniq = []
        for s in sentences:
            if s not in uniq:
                uniq.append(s)
        res = ". ".join(uniq).strip()

        if len(res) < 25:
            return f"Merci pour votre message. L'équipe {self.brand_name} vous répond rapidement. Contact recommandé pour devis/précisions."
        return res


class ContextEnhancer:
    def __init__(self, client_data: Dict):
        self.client_data = client_data

    def enhance(self, docs: List[Any]) -> str:
        if not docs:
            ent = self.client_data.get("entreprise", {})
            return f"{ent.get('nom','Votre entreprise')} — {ent.get('slogan','')}"
        return "\n".join([d.page_content for d in docs[:3]])


def detect_scenario(q: str) -> str:
    ql = q.lower()
    if any(k in ql for k in ["urgent", "demain", "crise", "last minute"]):
        return "Urgence"
    if any(k in ql for k in ["prix", "devis", "budget", "tarif"]):
        return "Devis"
    if any(k in ql for k in ["référence", "reference", "portfolio"]):
        return "Références"
    return "Question générale"


class Pipeline:
    def __init__(self, mode: str, client_id: str, client_data: Dict[str, Any], retriever, llm, prompt: PromptTemplate):
        self.mode = mode
        self.client_id = client_id
        self.client_data = client_data
        self.retriever = retriever
        self.llm = llm
        self.prompt = prompt
        self.enhancer = ContextEnhancer(client_data)
        self.parser = AdvancedOutputParser(client_data.get("entreprise", {}).get("nom", "Votre entreprise"))

    def process(self, question: str) -> str:
        docs = self.retriever.get_relevant_documents(question)
        context = self.enhancer.enhance(docs)
        scen = detect_scenario(question)
        prompt_text = self.prompt.format(
            brand_name=self.client_data.get("entreprise", {}).get("nom", "Votre entreprise"),
            context=context,
            question=question,
            scenario=scen,
        )
        raw = self.llm.invoke(prompt_text)
        raw_text = getattr(raw, "content", raw)
        return self.parser.parse(raw_text)


def build_embeddings_and_llm() -> Tuple[Any, Any]:
    if LLM_PROVIDER == "OPENAI":
        if not HAS_OPENAI:
            raise RuntimeError("langchain-openai non disponible. Ajoutez-le à requirements.txt")
        emb = OpenAIEmbeddings(model=EMBED_MODEL_OPENAI)
        llm = ChatOpenAI(model=LLM_MODEL, temperature=0.6)
        return emb, llm

    if LLM_PROVIDER == "OLLAMA":
        emb = OllamaEmbeddings(model=OLLAMA_EMBED_MODEL)
        llm = OllamaLLM(model=OLLAMA_LLM_MODEL, temperature=0.7, num_predict=300, top_k=20, top_p=0.9)
        return emb, llm

    # HF local (gratuit)
    emb = HuggingFaceEmbeddings(model_name=HF_EMBED_MODEL)
    # Pipeline text2text (FLAN-T5)
    text2text = pipeline(
        "text2text-generation",
        model=HF_LLM_MODEL,
        tokenizer=HF_LLM_MODEL,
    )

    class HFLLMWrapper:
        def __init__(self, pipe):
            self.pipe = pipe

        def invoke(self, prompt: str) -> str:
            out = self.pipe(prompt, max_new_tokens=200, do_sample=True, temperature=0.7, top_p=0.9)
            return out[0]["generated_text"]

    llm = HFLLMWrapper(text2text)
    return emb, llm


def load_client_data(mode: str, client_id: str) -> Dict[str, Any]:
    if mode == "alt":
        path = f"./rag_alt/clients/{client_id}/data.json"
    else:
        path = f"./clients/{client_id}/data.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_documents(mode: str, client_data_path: str):
    if mode == "alt":
        return alt_indexer.load_and_prepare_documents(client_data_path)
    return main_indexer.load_and_prepare_documents(client_data_path)


def build_pipeline(mode: str, client_id: str) -> Pipeline:
    client_data = load_client_data(mode, client_id)
    emb, llm = build_embeddings_and_llm()

    if mode == "alt":
        persist_dir = os.path.join(CHROMA_DIR_ALT, client_id)
        collection = f"api_alt_{client_id}"
        docs = alt_indexer.load_and_prepare_documents(f"./rag_alt/clients/{client_id}/data.json")
    else:
        persist_dir = os.path.join(CHROMA_DIR_MAIN, client_id)
        collection = f"api_main_{client_id}"
        docs = main_indexer.load_and_prepare_documents(f"./clients/{client_id}/data.json")

    os.makedirs(persist_dir, exist_ok=True)
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=emb,
        collection_name=collection,
        persist_directory=persist_dir,
        collection_metadata={"hnsw:space": "cosine"},
    )

    retriever = vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": 3, "score_threshold": 0.3},
    )

    template = """Tu es l'assistant de {brand_name}.

CONTEXTE:
{context}

CLIENT DIT: "{question}"

SITUATION: {scenario}

Mission: Réponds en 2-3 phrases claires, professionnelles et orientées solution. Termine par un appel à l'action (contact, devis, etc.).
Réponse:"""

    prompt = PromptTemplate(template=template, input_variables=["brand_name", "context", "question", "scenario"])

    return Pipeline(mode=mode, client_id=client_id, client_data=client_data, retriever=retriever, llm=llm, prompt=prompt)


# Cache mémoire des pipelines construits
PIPELINES: Dict[Tuple[str, str], Pipeline] = {}


def get_pipeline(mode: str, client_id: str) -> Pipeline:
    key = (mode, client_id)
    if key not in PIPELINES:
        PIPELINES[key] = build_pipeline(mode, client_id)
    return PIPELINES[key]


# FastAPI app
app = FastAPI(title="RAG API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # à restreindre en prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    client_id: str = "bms_ventouse"
    mode: str = "main"  # "main" | "alt"
    refresh: bool = False  # reconstruire la pipeline


@app.post("/api/chat")
def chat(req: ChatRequest):
    if req.mode not in {"main", "alt"}:
        return {"error": "mode invalide. Utilisez 'main' ou 'alt'."}

    if req.refresh:
        key = (req.mode, req.client_id)
        if key in PIPELINES:
            del PIPELINES[key]

    try:
        pipeline = get_pipeline(req.mode, req.client_id)
        response = pipeline.process(req.question)
        return {
            "client_id": req.client_id,
            "mode": req.mode,
            "provider": LLM_PROVIDER,
            "response": response,
        }
    except FileNotFoundError:
        return {"error": f"Fichier client introuvable pour {req.client_id} en mode {req.mode}."}
    except Exception as e:
        logger.error(f"Erreur /api/chat: {e}")
        return {"error": "Erreur serveur"}