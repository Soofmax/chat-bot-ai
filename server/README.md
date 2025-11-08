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
    - provider (HF | OPENAI | OLLAMA)
    - client_id, mode

Exemple:
```
curl -X POST https://votre-service.onrender.com/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Urgence tournage demain à Paris, pouvez-vous aider ?","client_id":"bms_ventouse","mode":"main"}'
```

## Choix du provider LLM/Embeddings

Par défaut (gratuit), l'API utilise des modèles open-source locaux (Hugging Face) téléchargeables automatiquement:
- LLM (génération): `google/flan-t5-small`
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2`

Variables d'environnement (déjà définies dans `render.yaml`):
- LLM_PROVIDER=HF
- HF_LLM_MODEL=google/flan-t5-small
- HF_EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2

Autres options (si besoin):
- OPENAI (payant):
  - LLM_PROVIDER=OPENAI
  - OPENAI_API_KEY=...
  - LLM_MODEL=gpt-4o-mini
  - EMBED_MODEL_OPENAI=text-embedding-3-small
- OLLAMA (auto-hébergement nécessaire):
  - LLM_PROVIDER=OLLAMA
  - OLLAMA_LLM_MODEL=tinyllama
  - OLLAMA_EMBED_MODEL=nomic-embed-text

## Déploiement sur Render

1) Connectez votre repo GitHub à Render.
2) Render détectera `render.yaml`. Choisissez "Blueprint".
3) Déployez (aucune clé API requise en mode HF).
4) Au premier appel, les modèles seront téléchargés et mis en cache sur l'instance.

Le service utilise la commande:
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
uvicorn server.app:app --host 0.0.0.0 --port 8000 --reload
```

Puis:
```
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Avez-vous des références ?"}'
```