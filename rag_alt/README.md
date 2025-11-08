# RAG Alternatif (séparé)

Ce dossier contient une instance RAG indépendante, avec sa propre base vectorielle, ses scripts et ses données. Il ne partage rien avec l'instance principale à la racine du dépôt.

## Architecture

- Clients: `rag_alt/clients/`
- Indexation: `rag_alt/indexer.py` → base Chroma dans `rag_alt/chroma_db_alt`
- Génération: `rag_alt/generer_reponse.py` → LLM via Ollama
- Modèles:
  - Embeddings: `nomic-embed-text`
  - LLM: `tinyllama`

## Prérequis

- Ollama installé et démarré
```
ollama pull tinyllama
ollama pull nomic-embed-text
```
- Dépendances Python (les mêmes que le projet racine):
```
pip install -r requirements.txt
```

## Démarrage

1) Placez un client dans `rag_alt/clients/<votre_client>/data.json` en partant du template:
   - `rag_alt/clients/_template_client/data.json`

2) Dans `rag_alt/indexer.py` et `rag_alt/generer_reponse.py`, changez:
```
CLIENT_ID = "<votre_client>"
```

3) Indexez:
```
python rag_alt/indexer.py
```

4) Lancez l'assistant:
```
python rag_alt/generer_reponse.py
```

## Templates

- Données client: `rag_alt/clients/_template_client/data.json`
- Questions de base: `rag_alt/clients/_template_questions_base.md`