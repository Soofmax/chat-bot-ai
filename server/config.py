import os

# Provider and models
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "HF").upper()  # HF | OPENAI | OLLAMA
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")  # For OPENAI
EMBED_MODEL_OPENAI = os.getenv("EMBED_MODEL_OPENAI", "text-embedding-3-small")
OLLAMA_LLM_MODEL = os.getenv("OLLAMA_LLM_MODEL", "tinyllama")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
HF_LLM_MODEL = os.getenv("HF_LLM_MODEL", "google/flan-t5-small")
HF_EMBED_MODEL = os.getenv("HF_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Vector store directories
CHROMA_DIR_MAIN = os.getenv("CHROMA_DIR_MAIN", "/tmp/chroma_main")
CHROMA_DIR_ALT = os.getenv("CHROMA_DIR_ALT", "/tmp/chroma_alt")

# API and security
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*")
API_KEYS = set(x.strip() for x in os.getenv("API_KEYS", "").split(",") if x.strip())

# Retrieval settings
RETRIEVER_K = int(os.getenv("RETRIEVER_K", "3"))
RETRIEVER_SCORE_THRESHOLD = float(os.getenv("RETRIEVER_SCORE_THRESHOLD", "0.3"))

# Rate limiting (basic in-memory)
RATE_LIMIT_WINDOW_SEC = int(os.getenv("RATE_LIMIT_WINDOW_SEC", "60"))
RATE_LIMIT_MAX_REQ = int(os.getenv("RATE_LIMIT_MAX_REQ", "60"))
RATE_LIMIT_KEY = os.getenv("RATE_LIMIT_KEY", "ip")  # "ip" or "apikey"