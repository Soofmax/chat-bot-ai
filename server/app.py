import os
import json
import re
import logging
from functools import lru_cache
from typing import Dict, List, Any, Tuple
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import chromadb

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
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
API_KEYS = set(x.strip() for x in os.getenv("API_KEYS", "").split(",") if x.strip())

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


# Sécurisation des chemins client pour éviter les traversals
SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

def ensure_safe_client_id(client_id: str) -> str:
    if not SAFE_ID.match(client_id):
        raise ValueError("client_id invalide")
    return client_id

def safe_client_path(mode: str, client_id: str) -> Path:
    safe_id = ensure_safe_client_id(client_id)
    base = Path("./rag_alt/clients" if mode == "alt" else "./clients").resolve()
    p = (base / safe_id / "data.json").resolve()
    if base not in p.parents:
        raise ValueError("Chemin client hors base autorisée")
    return p

def load_client_data(mode: str, client_id: str) -> Dict[str, Any]:
    path = safe_client_path(mode, client_id)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_documents(mode: str, client_data_path: str):
    if mode == "alt":
        return alt_indexer.load_and_prepare_documents(client_data_path)
    return main_indexer.load_and_prepare_documents(client_data_path)


def build_pipeline(mode: str, client_id: str) -> Pipeline:
    safe_id = ensure_safe_client_id(client_id)
    client_data = load_client_data(mode, safe_id)
    emb, llm = build_embeddings_and_llm()

    if mode == "alt":
        base_dir = CHROMA_DIR_ALT
        persist_dir = os.path.join(base_dir, safe_id)
        collection = f"api_alt_{safe_id}"
        data_path = safe_client_path(mode, safe_id)
        docs_loader = alt_indexer.load_and_prepare_documents
    else:
        base_dir = CHROMA_DIR_MAIN
        persist_dir = os.path.join(base_dir, safe_id)
        collection = f"api_main_{safe_id}"
        data_path = safe_client_path(mode, safe_id)
        docs_loader = main_indexer.load_and_prepare_documents

    os.makedirs(persist_dir, exist_ok=True)

    # Ouvrir la collection existante si possible
    try:
        vectorstore = Chroma(
            embedding=emb,
            collection_name=collection,
            persist_directory=persist_dir,
        )
        count = vectorstore._collection.count()
    except Exception:
        vectorstore = None
        count = 0

    # Construire la collection seulement si vide
    if not vectorstore or count == 0:
        docs = docs_loader(str(data_path))
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

    return Pipeline(mode=mode, client_id=safe_id, client_data=client_data, retriever=retriever, llm=llm, prompt=prompt)


# Cache mémoire des pipelines construits
PIPELINES: Dict[Tuple[str, str], Pipeline] = {}


def get_pipeline(mode: str, client_id: str) -> Pipeline:
    key = (mode, client_id)
    if key not in PIPELINES:
        PIPELINES[key] = build_pipeline(mode, client_id)
    return PIPELINES[key]


# FastAPI app
app = FastAPI(title="RAG API", version="1.0.0")

# CORS (piloté par env)
_allowed = [o.strip() for o in ALLOWED_ORIGINS.split(",")] if ALLOWED_ORIGINS else []
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed if _allowed else ["*"],
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# Headers de sécurité
from starlette.middleware.base import BaseHTTPMiddleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none';"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Health-check
@app.get("/healthz")
def healthz():
    return {"status": "ok"}

# Auth API key (si configurée)
@app.middleware("http")
async def require_api_key(request, call_next):
    if request.url.path.startswith("/api/"):
        auth = request.headers.get("Authorization", "")
        api_key = auth.split(" ", 1)[1] if auth.startswith("Bearer ") else ""
        # Si des clés sont configurées, les exiger
        if API_KEYS and (not api_key or api_key not in API_KEYS):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return await call_next(request)


class ChatRequest(BaseModel):
    question: str
    client_id: str = "bms_ventouse"
    mode: str = "main"  # "main" | "alt"
    refresh: bool = False  # reconstruire la pipeline


@app.post("/api/chat")
def chat(req: ChatRequest):
    if req.mode not in {"main", "alt"}:
        return {"error": "mode invalide. Utilisez 'main' ou 'alt'."}

    try:
        safe_id = ensure_safe_client_id(req.client_id)
    except ValueError:
        return {"error": "client_id invalide"}

    # Refresh optionnel : purge cache + collection persistée
    if req.refresh:
        key = (req.mode, safe_id)
        if key in PIPELINES:
            del PIPELINES[key]
        try:
            base_dir = CHROMA_DIR_ALT if req.mode == "alt" else CHROMA_DIR_MAIN
            persist_dir = os.path.join(base_dir, safe_id)
            collection = f"api_{'alt' if req.mode == 'alt' else 'main'}_{safe_id}"
            client = chromadb.PersistentClient(path=persist_dir)
            client.delete_collection(name=collection)
            logger.info(f"Collection '{collection}' supprimée pour refresh")
        except Exception as e:
            logger.info(f"Aucune collection à supprimer pour {safe_id}: {e}")

    try:
        pipeline = get_pipeline(req.mode, safe_id)
        response = pipeline.process(req.question)
        return {
            "client_id": safe_id,
            "mode": req.mode,
            "provider": LLM_PROVIDER,
            "response": response,
        }
    except FileNotFoundError:
        return {"error": f"Fichier client introuvable pour {safe_id} en mode {req.mode}."}
    except Exception as e:
        logger.error(f"Erreur /api/chat: {e}")
        return {"error": "Erreur serveur"}