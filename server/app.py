import os
import json
import re
import logging
import time
import uuid
import contextvars

from typing import Dict, Any, Tuple, Optional, Literal
from pathlib import Path

from fastapi import FastAPI, Request, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.middleware.base import BaseHTTPMiddleware

import chromadb

from langchain_community.vectorstores import Chroma
from langchain_community.llms import Ollama as OllamaLLM
from langchain_community.embeddings import OllamaEmbeddings, HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate

# Optional OpenAI provider
try:
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    HAS_OPENAI = True
except Exception:
    HAS_OPENAI = False

# Optional local HF text generation
from transformers import pipeline

# Optional JSON logging formatter
try:
    from pythonjsonlogger import jsonlogger
    HAS_JSON_LOGGER = True
except Exception:
    HAS_JSON_LOGGER = False

# Optional Prometheus instrumentation
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    HAS_PROM = True
except Exception:
    HAS_PROM = False

# Optional Redis-backed rate limiter (SlowAPI)
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
    from slowapi.middleware import SlowAPIMiddleware
    HAS_SLOWAPI = True
except Exception:
    HAS_SLOWAPI = False

# Local modules (shared)
from shared.generation import AdvancedOutputParser, ContextEnhancer, detect_scenario, DEFAULT_PROMPT_TEMPLATE
from shared.indexing import load_and_prepare_documents

# Settings (centralisées)
from .config import (
    ENV,
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
    REDIS_URL,
    RATE_LIMIT_RULE,
    API_KEYS_MAP,
)

# Correlation ID via contextvar
REQUEST_ID_CTX = contextvars.ContextVar("request_id", default="")

def _configure_logging():
    logger_ = logging.getLogger()
    level = logging.INFO
    logger_.setLevel(level)
    for h in list(logger_.handlers):
        logger_.removeHandler(h)
    handler = logging.StreamHandler()
    if HAS_JSON_LOGGER:
        formatter = jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s")
    else:
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s - rid=%(request_id)s")
    handler.setFormatter(formatter)
    logger_.addHandler(handler)

_configure_logging()
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
    emb: Any
    llm: Any

    if LLM_PROVIDER == "OPENAI":
        if not HAS_OPENAI:
            raise RuntimeError("langchain-openai non disponible. Ajoutez-le à requirements.txt")
        emb = OpenAIEmbeddings(model=EMBED_MODEL_OPENAI)
        llm = ChatOpenAI(model=LLM_MODEL, temperature=0.6)
    elif LLM_PROVIDER == "OLLAMA":
        emb = OllamaEmbeddings(model=OLLAMA_EMBED_MODEL)
        llm = OllamaLLM(model=OLLAMA_LLM_MODEL, temperature=0.7, num_predict=300, top_k=20, top_p=0.9)
    else:
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

def _get_prompt_template(client_data: Dict[str, Any]) -> str:
    """
    Retourne un template de prompt par client si défini, sinon le template par défaut.
    Doit contenir les variables: brand_name, context, question, scenario.
    """
    tmpl = client_data.get("prompt_template")
    required = {"brand_name", "context", "question", "scenario"}
    if isinstance(tmpl, str) and all(v in tmpl for v in required):
        return tmpl
    return DEFAULT_PROMPT_TEMPLATE

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
            embedding_function=emb,
            collection_name=collection,
            persist_directory=persist_dir,
            collection_metadata={"hnsw:space": "cosine"},
        )

    retriever = vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": RETRIEVER_K, "score_threshold": RETRIEVER_SCORE_THRESHOLD},
    )

    template = _get_prompt_template(client_data)
    prompt = PromptTemplate(template=template, input_variables=["brand_name", "context", "question", "scenario"])

    return Pipeline(mode=mode, client_id=safe_id, client_data=client_data, retriever=retriever, llm=llm, prompt=prompt)

# Cache mémoire des pipelines construits
PIPELINES: Dict[Tuple[str, str], Pipeline] = {}
# Rate limiting storage (in-memory) at module level
RL_BUCKETS: Dict[str, Tuple[float, int]] = {}

def get_pipeline(mode: str, client_id: str) -> Pipeline:
    key = (mode, client_id)
    if key not in PIPELINES:
        PIPELINES[key] = build_pipeline(mode, client_id)
    return PIPELINES[key]

# Router pour définir les endpoints indépendamment de l'instance FastAPI
router = APIRouter()

# Health-check
@router.get("/healthz")
def healthz():
    return {"status": "ok"}

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    client_id: str = "bms_ventouse"  # validation regex gérée par ensure_safe_client_id()
    mode: Literal["main", "alt"] = "main"
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

@router.post("/api/chat", tags=["chat"], responses={401: {"description": "Unauthorized"}, 429: {"description": "Too Many Requests"}})
def chat(req: ChatRequest):
    return _handle_chat(req)

@router.post("/v1/chat", tags=["chat"], responses={401: {"description": "Unauthorized"}, 429: {"description": "Too Many Requests"}})
def chat_v1(req: ChatRequest):
    return _handle_chat(req)

# Middleware classes
class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        REQUEST_ID_CTX.set(rid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none';"
        return response

def build_app() -> FastAPI:
    app = FastAPI(title="RAG API", version="1.0.0")

    # Middlewares
    app.add_middleware(CorrelationIdMiddleware)

    allowed = [o.strip() for o in ALLOWED_ORIGINS.split(",")] if ALLOWED_ORIGINS else []
    if allowed and allowed != ["*"]:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed,
            allow_credentials=False,
            allow_methods=["POST", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization"],
        )
    else:
        # Fallback: echo Origin dynamiquement via regex, plutôt que "*"
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[],
            allow_origin_regex=".*",
            allow_credentials=False,
            allow_methods=["POST", "OPTIONS"],
            allow_headers=["Content-Type", "Authorization"],
        )

    app.add_middleware(SecurityHeadersMiddleware)

    # Startup gating: exigences production
    @app.on_event("startup")
    async def _startup_checks():
        # Sentry (optionnel)
        try:
            dsn = os.getenv("SENTRY_DSN", "")
            if dsn:
                import sentry_sdk  # type: ignore
                sentry_sdk.init(dsn=dsn, traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.0")))
                logger.info("Sentry initialisé")
        except Exception as e:
            logger.warning(f"Sentry non initialisé: {e}")

        if ENV == "production":
            if not API_KEYS:
                logger.error("API_KEYS manquant en production")
                raise RuntimeError("API_KEYS requis en production")
            if ALLOWED_ORIGINS == "*" or not ALLOWED_ORIGINS.strip():
                logger.error("ALLOWED_ORIGINS wildcard en production")
                raise RuntimeError("ALLOWED_ORIGINS doit être une liste d'origines autorisées en production")
        # Prometheus metrics: déplacé avant le startup pour éviter l'ajout de middleware après démarrage
        pass

    # Rate limiting: SlowAPI (Redis) si disponible, sinon fallback mémoire
    RL_BUCKETS.clear()

    def _rate_limit_key(request, api_key: str) -> str:
        if RATE_LIMIT_KEY.lower() == "apikey" and api_key:
            return f"ak:{api_key}"
        client_ip = getattr(request.client, "host", "unknown")
        return f"ip:{client_ip}"

    limiter_local: Optional[Any] = None
    if HAS_SLOWAPI and REDIS_URL:
        def _key_func(request: Request):
            auth = request.headers.get("Authorization", "")
            if RATE_LIMIT_KEY.lower() == "apikey" and auth.startswith("Bearer "):
                return auth.split(" ", 1)[1]
            return get_remote_address(request)

        limiter_local = Limiter(key_func=_key_func, storage_uri=REDIS_URL, default_limits=[RATE_LIMIT_RULE])
        app.state.limiter = limiter_local

        async def _rl_exceeded_handler(request: Request, exc: Exception):
            try:
                if isinstance(exc, RateLimitExceeded):  # type: ignore[arg-type]
                    return _rate_limit_exceeded_handler(request, exc)  # type: ignore[arg-type]
            except Exception:
                pass
            return JSONResponse({"error": "Too Many Requests"}, status_code=429)

        app.add_exception_handler(RateLimitExceeded, _rl_exceeded_handler)
        app.add_middleware(SlowAPIMiddleware)

    @app.middleware("http")
    async def require_api_key(request, call_next):
        class RequestIdFilter(logging.Filter):
            def filter(self, record):
                try:
                    record.request_id = REQUEST_ID_CTX.get()
                except Exception:
                    record.request_id = ""
                return True
        logging.getLogger().addFilter(RequestIdFilter())

        if request.url.path.startswith("/api/") or request.url.path.startswith("/v1/"):
            auth = request.headers.get("Authorization", "")
            api_key = auth.split(" ", 1)[1] if auth.startswith("Bearer ") else ""

            if (ENV == "production") or API_KEYS:
                if not api_key or api_key not in API_KEYS:
                    return JSONResponse({"error": "Unauthorized"}, status_code=401)

                requested_client = request.headers.get("client_id", "")
                try:
                    if not requested_client and request.headers.get("content-type","").startswith("application/json"):
                        body = await request.body()
                        data = json.loads(body.decode("utf-8") or "{}")
                        requested_client = str(data.get("client_id") or "")
                except Exception:
                    pass

                if API_KEYS_MAP:
                    allowed = API_KEYS_MAP.get(api_key, set())
                    if requested_client and requested_client not in allowed:
                        return JSONResponse({"error": "Forbidden"}, status_code=403)

            if not limiter_local:
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

    # Inclure le router
    app.include_router(router)

    # Prometheus metrics (avant démarrage)
    if HAS_PROM:
        try:
            Instrumentator().instrument(app).expose(app)
            logger.info("Prometheus metrics exposées sur /metrics")
        except Exception as e:
            logger.warning(f"Instrumentator non disponible: {e}")

    return app

# Instance par défaut
app = build_app()