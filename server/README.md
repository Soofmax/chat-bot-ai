# Backend API (FastAPI) — Déploiement Render

Ce dossier contient l'API HTTP pour intégrer le RAG au site web client. Cette API peut être déployée facilement sur Render.

## Endpoints

- POST /api/chat
  - Body:
    - question (str, requis)
    - client_id (str, défaut: "bms_ventouse")
    - mode (str, "main" | "alt", défaut: "main")
    - refresh (bool, défaut: false) — force la reconstruction de la pipeline (réindexation et rechargement)
  - Réponse:
    - response (str)
    - provider (OPENAI ou OLLAMA)
    - client_id, mode

Exemple:
```
curl -X POST https://votre-service.onrender.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Urgence tournage demain à Paris, pouvez-vous aider ?","client_id":"bms_ventouse","mode":"main"}'
```

## Choix du provider LLM/Embeddings

Par défaut Render utilisera l'API OpenAI (recommandé). Vous pouvez basculer sur Ollama si vous auto-hébergez.

- OPENAI (par défaut)
  - Env vars:
    - LLM_PROVIDER=OPENAI
    - OPENAI_API_KEY=... (à configurer sur Render)
    - LLM_MODEL=gpt-4o-mini (modifiable)
    - EMBED_MODEL_OPENAI=text-embedding-3-small (modifiable)

- OLLAMA (si vous hébergez Ollama vous-même)
  - Env vars:
    - LLM_PROVIDER=OLLAMA
    - OLLAMA_LLM_MODEL=tinyllama
    - OLLAMA_EMBED_MODEL=nomic-embed-text
  - Et un serveur Ollama accessible depuis l’API (non recommandé sur Render directement).

## Déploiement sur Render

1) Connectez votre repo GitHub à Render.
2) Render détectera `render.yaml`. Choisissez "Blueprint".
3) Configurez les variables d'environnement dans Render:
   - OPENAI_API_KEY (Sync: false)
   - (optionnel) LLM_MODEL, EMBED_MODEL_OPENAI, LLM_PROVIDER
4) Déployez.

Le service utilisera la commande:
```
uvicorn server.app:app --host 0.0.0.0 --port $PORT
```

## Données clients et RAG "alt"

- RAG principal (mode="main"):
  - Données: `./clients/<client_id>/data.json`
- RAG alternatif (mode="alt"):
  - Données: `./rag_alt/clients/<client_id>/data.json`
  - Un template est disponible: `rag_alt/clients/_template_client/data.json`

L'API reconstruit en mémoire la base vectorielle à la première requête par `(mode, client_id)` et la met en cache. Utilisez `refresh=true` pour reconstruire la pipeline après une mise à jour de données.

## CORS

CORS est ouvert par défaut (allow_origins=["*"]). Restreignez à vos domaines en production si nécessaire.

## Développement local

```
pip install -r requirements.txt
export OPENAI_API_KEY=sk-xxx
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
```

Puis:
```
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Avez-vous des références ?"}'
```