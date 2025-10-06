import json
import chromadb
import logging
from typing import List, Dict, Any
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain.docstore.document import Document

# Configuration (RAG séparé)
CLIENT_ID = "template_client"  # Changez pour votre nouveau client
CLIENT_DATA_FILE = f"./rag_alt/clients/{CLIENT_ID}/data.json"
CHROMA_COLLECTION_NAME = f"rag_alt_{CLIENT_ID}"
CHROMA_DB_DIRECTORY = "./rag_alt/chroma_db_alt"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class DataPreprocessor:
    @staticmethod
    def chunk_text(text: str, max_length: int = 500) -> List[str]:
        words = text.split()
        chunks, current = [], []
        for w in words:
            if len(" ".join(current + [w])) <= max_length:
                current.append(w)
            else:
                if current:
                    chunks.append(" ".join(current))
                current = [w]
        if current:
            chunks.append(" ".join(current))
        return chunks


def load_and_prepare_documents(filepath: str) -> List[Document]:
    logger.info(f"Chargement du fichier client: {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    docs: List[Document] = []
    prep = DataPreprocessor()

    # 1) Informations entreprise
    ent = data.get("entreprise", {})
    cli = data.get("client_info", {})
    info_sections = [
        f"Entreprise: {ent.get('nom','')}",
        f"Slogan: {ent.get('slogan','')}",
        f"Mission: {ent.get('mission','')}",
        f"Valeurs: {', '.join(ent.get('valeurs', []))}",
        f"Positionnement: {ent.get('positioning','')}",
        f"Cible: {cli.get('target_audience','')}",
        f"Zone: {cli.get('intervention_zone','')}",
        f"Horaires: {cli.get('business_hours','')}",
    ]
    for i, chunk in enumerate(prep.chunk_text(" | ".join(info_sections))):
        docs.append(Document(page_content=chunk, metadata={"source": "entreprise_info", "chunk": i, "type": "infos"}))

    # 2) Personnalité IA
    ai = data.get("ai_personality", {})
    vm = (ai.get("vocabulaire_metier") or {})
    personality_text = " | ".join([
        f"Profil: {ai.get('profile','')}",
        f"Ton: {ai.get('tone','')}",
        f"Style: {ai.get('communication_style','')}",
        f"Mots puissants: {', '.join(vm.get('mots_puissants', []))}",
        f"Termes techniques: {', '.join(vm.get('terms_techniques', []))}",
    ])
    for i, chunk in enumerate(prep.chunk_text(personality_text)):
        docs.append(Document(page_content=chunk, metadata={"source": "ai_personality", "chunk": i, "type": "comportement"}))

    # 3) Services
    for svc in data.get("services_detailles", []):
        details = svc.get("details", [])
        text = f"Service: {svc.get('name','')} | Description: {svc.get('description','')} | Détails: {'; '.join(details)}"
        docs.append(Document(page_content=text, metadata={"source": "service", "service_name": svc.get("name",""), "type": "offre_service"}))

    # 4) Réponses stratégiques (si présentes)
    rs = (ai.get("reponses_strategiques") or {})
    for name, val in rs.items():
        if isinstance(val, dict):
            for sub, resp in val.items():
                text = f"Scénario: {name}_{sub} | Réponse: {resp}"
                docs.append(Document(page_content=text, metadata={"source": "reponses_strategiques", "scenario": f"{name}_{sub}", "type": "reponse"}))
        elif isinstance(val, list):
            for i, resp in enumerate(val):
                text = f"Scénario: {name} | Réponse {i+1}: {resp}"
                docs.append(Document(page_content=text, metadata={"source": "reponses_strategiques", "scenario": name, "type": "reponse"}))

    # 5) Références
    for ref in data.get("references_prestigieuses", []):
        text = " | ".join([
            f"Référence: {ref.get('projet','')}",
            f"Client: {ref.get('client','')}",
            f"Type: {ref.get('type','')}",
            f"Spécificité: {ref.get('specificite','')}",
        ])
        docs.append(Document(page_content=text, metadata={"source": "references", "client": ref.get("client",""), "type": "reference"}))

    # 6) Scénarios critiques
    for name, info in (data.get("scenarios_critiques") or {}).items():
        decl = info.get("declencheur", [])
        text = f"Scénario critique: {name} | Déclencheurs: {', '.join(decl)} | Réponse: {info.get('reponse','')} | Action: {info.get('action','')} | CTA: {info.get('cta_prioritaire','')}"
        docs.append(Document(page_content=text, metadata={"source": "scenarios_critiques", "scenario_type": name, "type": "crise"}))

    # 7) Preuves sociales
    ps = (data.get("preuves_sociales") or {})
    for i, t in enumerate(ps.get("temoignages_metier", [])):
        docs.append(Document(page_content=f"Témoignage {i+1}: {t}", metadata={"source": "preuves_sociales", "type": "temoignage"}))

    logger.info(f"Documents préparés: {len(docs)}")
    return docs


def initialize_vector_store(documents: List[Document], collection_name: str, persist_directory: str) -> Chroma:
    logger.info("Création embeddings (nomic-embed-text via Ollama)...")
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # Purge collection
    client = chromadb.PersistentClient(path=persist_directory)
    try:
        client.delete_collection(name=collection_name)
        logger.info(f"Ancienne collection '{collection_name}' supprimée")
    except Exception:
        logger.info(f"Création nouvelle collection '{collection_name}'")

    vs = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=persist_directory,
        collection_metadata={"hnsw:space": "cosine"},
    )
    return vs


def verify(vectorstore: Chroma, queries: List[str] = None):
    if queries is None:
        queries = ["services", "devis", "urgence", "références"]
    for q in queries:
        res = vectorstore.similarity_search(q, k=2)
        logger.info(f"Requête: '{q}' -> {len(res)} résultats")


if __name__ == "__main__":
    docs = load_and_prepare_documents(CLIENT_DATA_FILE)
    vs = initialize_vector_store(docs, CHROMA_COLLECTION_NAME, CHROMA_DB_DIRECTORY)
    verify(vs)
    logger.info(f"OK — Base vectorielle '{CHROMA_COLLECTION_NAME}' créée dans {CHROMA_DB_DIRECTORY}")