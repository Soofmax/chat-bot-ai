import os

# Prefer re-exporting server config when available, fallback to env
try:
    from server.config import (
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
    )
except Exception:
    # Fallback to environment variables
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "HF").upper()  # HF | OPENAI | OLLAMA
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    EMBED_MODEL_OPENAI = os.getenv("EMBED_MODEL_OPENAI", "text-embedding-3-small")
    OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "tinyllama")
    OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    HF_LLM_MODEL = os.getenv("HF_LLM_MODEL", "google/flan-t5-small")
    HF_EMBED_MODEL = os.getenv("HF_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

    CHROMA_DIR_MAIN = os.getenv("CHROMA_DIR_MAIN", "/tmp/chroma_main")
    CHROMA_DIR_ALT = os.getenv("CHROMA_DIR_ALT", "/tmp/chroma_alt")

    ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
    API_KEYS = set(x.strip() for x in os.getenv("API_KEYS", "").split(",") if x.strip())

    RETRIEVER_K = int(os.getenv("RETRIEVER_K", "3"))
    RETRIEVER_SCORE_THRESHOLD = float(os.getenv("RETRIEVER_SCORE_THRESHOLD", "0.3"))