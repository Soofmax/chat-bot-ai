import os
import json
import re
import logging
import time

from typing import Dict, Any, Tuple
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.middleware.base import BaseHTTPMiddleware

import chromadb

from langchain_community.vectorstores import Chroma
from langchain_community.llms import Ollama as OllamaLLM
from langchain_community.embeddings import OllamaEmbeddings, HuggingFaceEmbeddings
from langchain.prompts import PromptTemplate

# Optional OpenAI provider
try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    HAS_OPENAI = True
except Exception:
    HAS_OPENAI = False

# Optional local HF text generation
from transformers import pipeline

# Local modules (shared)
from shared.generation import AdvancedOutputParser, ContextEnhancer, detect_scenario
from shared.indexing import load_and_prepare_documents

# Settings (centralisées)
from .config import (
    LLM_PROVIDER,
    LLM_MODEL,
    EMBED_MODEL_OPENAI,
    OLLAMA_LLM_MODEL,
    OLLAMA_EMBED_MODEL,
    HF_LLM_MODEL,
    HF_EMBED_MODEL,
    CHROMA_DIR_MAIN,
    CHROMA_DIR_ALT,
    ALLOWED_ORIGINS,
    API_KEYS,
    RETRIEVER_K,
    RETRIEVER_SCORE_THRESHOLD,
    RATE_LIMIT_WINDOW_SEC,
    RATE_LIMIT_MAX_REQ,
    RATE_LIMIT_KEY,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Ensure dirs exist
os.makedirs(CHROMA_DIR_MAIN, exist_ok=True)
os.makedirs(CHROMA_DIR_ALT, exist_ok=True)

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

def build_documents(mode: str, client_data_path: str):
    return load_and_prepare_documents(client_data_path)

def build_pipeline(mode: str, client_id: str) -> Pipeline:
    safe_id = ensure_safe_client_id(client_id)
    client_data = load_client_data(mode, safe_id)
    emb, llm = build_embeddings_and_llm()

    if mode == "alt":
        base_dir = CHROMA_DIR_ALT
        persist_dir = os.path.join(base_dir, safe_id)
        collection = f"api_alt_{safe_id}"
        data_path = safe_client_path(mode, safe_id)
        docs_loader = load_and_prepare_documents
    else:
        base_dir = CHROMA_DIR_MAIN
        persist_dir = os.path.join(base_dir, safe_id)
        collection = f"api_main_{safe_id}"
        data_path = safe_client_path(mode, safe_id)
        docs_loader = load_and_prepare_documents

    os.makedirs(persist_dir, exist_ok=True)

    # Ouvrir la collection existante si possible
    try:
        vectorstore = Chroma(
            embedding_function=emb,
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
        search_kwargs={"k": RETRIEVER_K, "score_threshold": RETRIEVER_SCORE_THRESHOLD},
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

# Rate limiting storage (in-memory)
RL_BUCKETS: Dict[str, Tuple[float, int]] = {}

def _rate_limit_key(request, api_key: str) -> str:
    if RATE_LIMIT_KEY.lower() == "apikey" and api_key:
        return f"ak:{api_key}"
    # fallback to IP
    client_ip = getattr(request.client, "host", "unknown")
    return f"ip:{client_ip}"

# Auth API key + rate limit (si configurée)
@app.middleware("http")
async def require_api_key(request, call_next):
    if request.url.path.startswith("/api/") or request.url.path.startswith("/v1/"):
        auth = request.headers.get("Authorization", "")
        api_key = auth.split(" ", 1)[1] if auth.startswith("Bearer ") else ""
        # Auth (optionnel)
        if API_KEYS and (not api_key or api_key not in API_KEYS):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        # Rate limit
        key = _rate_limit_key(request, api_key)
        now = time.time()
        bucket = RL_BUCKETS.get(key)
        if not bucket or (now - bucket[0]) >= RATE_LIMIT_WINDOW_SEC:
            RL_BUCKETS[key] = (now, 1)
        else:
            count = bucket[1] + 1
            if count > RATE_LIMIT_MAX_REQ:
                return JSONResponse({"error": "Too Many Requests"}, status_code=429)
            RL_BUCKETS[key] = (bucket[0], count)
    return await call_next(request)

class ChatRequest(BaseModel):
    question: str
    client_id: str = "bms_ventouse"
    mode: str = "main"  # "main" | "alt"
    refresh: bool = False  # reconstruire la pipeline

def _handle_chat(req: ChatRequest) -> Dict[str, Any]:
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
        logger.error(f"Erreur /chat: {e}")
        return {"error": "Erreur serveur"}

@app.post("/api/chat")
def chat(req: ChatRequest):
    return _handle_chat(req)

@app.post("/v1/chat")
def chat_v1(req: ChatRequest):
    return _handle_chat(req)