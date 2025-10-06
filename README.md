# CM-AI — Assistant RAG pour BMS

Assistant conversationnel RAG (Retrieval-Augmented Generation) pour répondre rapidement et professionnellement aux demandes clients en s'appuyant sur une base de connaissances vectorielle (Chroma) et un LLM local (Ollama).

## Architecture

- Données client JSON (profil, services, scénarios, références)
- Indexation → ChromaDB (embeddings via Ollama)
- Génération → LLM via Ollama (prompt compact, 2–3 phrases + CTA)
- Nettoyage / contrôle qualité des réponses

## Prérequis

- Python 3.10+
- Ollama installé et en cours d'exécution (https://ollama.com/download)
- Modèles Ollama à récupérer:
  - LLM: `tinyllama`
  - Embeddings: `nomic-embed-text`

Commande:
```
ollama pull tinyllama
ollama pull nomic-embed-text
```

## Installation

```
pip install -r requirements.txt
```

## Démarrage rapide

1) Indexer les données (crée/écrase la collection Chroma):
```
python indexer.py
```

2) Lancer l'assistant en ligne de commande:
```
python generer_reponse.py
```

Exemples de requêtes:
- "Urgence pour tournage demain à Paris"
- "Besoin devis pour logistique plateau"
- "Vous avez des références sur Netflix ?"
- "Problème autorisation mairie pour plateau"

## Configuration

- Identifiant client:
  - `CLIENT_ID` dans `indexer.py` et `generer_reponse.py` (par défaut: `bms_ventouse`)
- Répertoire ChromaDB:
  - `CHROMA_DB_DIRECTORY = "./chroma_db"`
- Collection:
  - `CHROMA_COLLECTION_NAME = CLIENT_ID`

## Ajouter un nouveau client

1) Créer un nouveau dossier:
```
clients/mon_client/
```

2) Copier et adapter le schéma JSON de `clients/bms_ventouse/data.json` (ou `clients/bms_logistique/data.json`) en conservant les clés suivantes au minimum:
- `entreprise` (nom, slogan, mission, valeurs, positioning)
- `client_info` (cibles, contacts, zone d'intervention, horaires)
- `services_detailles` (liste de services, description, détails)
- `ai_personality` (profile, tone, communication_style, vocabulaire_metier.mots_puissants, vocabulaire_metier.terms_techniques)
- `references_prestigieuses` (liste)
- `scenarios_critiques` (dictionnaire de scénarios)
- `preuves_sociales.temoignages_metier` (liste)

3) Mettre à jour `CLIENT_ID` dans les scripts, puis:
```
python indexer.py
python generer_reponse.py
```

## Détails techniques

- Embeddings: `OllamaEmbeddings(model="nomic-embed-text")`
- LLM: `Ollama(model="tinyllama")`
- Retrieval: similarité + seuil (k=3, score_threshold=0.3)
- Parser de sortie: suppression artefacts, déduplication, fallback propre
- Contrôles qualité: présence CTA, longueur minimale, absence de fuite de prompt

## Dépannage

- "Connection refused" → Lancer le serveur Ollama
- "model not found" → `ollama pull <model>`
- Rien n'est retourné par le retrieveur → Vérifier que `indexer.py` a été lancé et que `./chroma_db` contient la collection
- Problèmes d'embeddings → Vérifier que `nomic-embed-text` a bien été téléchargé

## Licence

Usage interne / projet client.