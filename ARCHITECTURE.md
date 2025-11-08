# Architecture

## Overview

This repository provides a RAG (Retrieval-Augmented Generation) service with:

- Data: client-specific JSON files (`./clients/<id>/data.json` or `./rag_alt/clients/<id>/data.json`)
- Indexing: building vector stores (ChromaDB) with enriched `Document` metadata
- Retrieval: similarity with threshold (configurable)
- Generation: LLM provider (HF/OpenAI/Ollama) producing short professional responses with CTA
- API: FastAPI `/api/chat` endpoint with security controls
- CLI: `generer_reponse.py` (main and alt variants)

## Components

- `server/app.py`
  - Builds pipelines (embeddings + LLM + retriever + prompt)
  - Caches pipelines per `(mode, client_id)`
  - Security: path sanitization, API key auth, CORS restrictions, security headers
  - Health endpoint

- `server/config.py`
  - Centralized configuration (env-driven)
  - Models, directories, retriever params, API/CORS settings

- `indexer.py` / `rag_alt/indexer.py`
  - Loads JSON and creates `Document` list with metadata
  - Initializes Chroma collections
  - Verifies embedding quality

- `generer_reponse.py` / `rag_alt/generer_reponse.py`
  - CLI assistants with simplified prompt and quality checks

## Data Flow

1. Request → `/api/chat` with `question`, `client_id`, `mode`
2. `get_pipeline(mode, client_id)` returns cached or builds:
   - Embeddings (provider-dependent)
   - VectorStore (Chroma): open existing collection or create if empty
   - Retriever: `k` and `score_threshold` from config
   - Prompt: concise instruction and scenario
3. Pipeline executes:
   - Retrieve docs → enhance context → detect scenario → generate → parse output
4. Response JSON

## Security Measures

- Input validation: `client_id` regex + path containment
- Auth: API key middleware
- CORS: restricted origins
- Headers: HSTS, XFO, CSP
- Logs: structured logger and error handling

## Environment and Deployment

- Render (`render.yaml`): builds with `requirements.txt`, starts uvicorn
- Models: defaults to HF (`flan-t5-small` + `all-MiniLM-L6-v2`)
- Alternative providers supported (OpenAI, Ollama) via env

## Configuration Reference

See `server/config.py` and `.env.example` for all variables:
- LLM_PROVIDER, model names
- CHROMA_DIR_MAIN/ALT
- RETRIEVER_K / RETRIEVER_SCORE_THRESHOLD
- ALLOWED_ORIGINS, API_KEYS

## Future Enhancements

- Rate limiting (Redis)
- Observability (Sentry/Datadog)
- API versioning (`/v1`)
- Shared modules to reduce duplication between main and alt