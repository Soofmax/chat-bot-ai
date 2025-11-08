import logging
from typing import List, Optional

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings

from shared.indexing import load_and_prepare_documents, initialize_vector_store

# --- Configuration ---
CLIENT_ID = "bms_ventouse"
CLIENT_DATA_FILE = f"./clients/{CLIENT_ID}/data.json"
CHROMA_COLLECTION_NAME = CLIENT_ID
CHROMA_DB_DIRECTORY = "./chroma_db"

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def verify_embedding_quality(vectorstore: Chroma, test_queries: Optional[List[str]] = None):
    """Vérifie la qualité des embeddings avec des requêtes tests"""
    if test_queries is None:
        test_queries = [
            "ventousage stationnement",
            "urgence tournage",
            "devis logistique",
            "références Netflix",
            "zone technique plateau",
        ]

    logger.info("Vérification de la qualité des embeddings...")
    for query in test_queries:
        results = vectorstore.similarity_search(query, k=2)
        logger.info(f"Requête: '{query}' -> Trouvé {len(results)} résultats")
        for i, doc in enumerate(results):
            logger.info(f"  Résultat {i+1}: {doc.metadata.get('source', 'Unknown')}")


# --- Script Principal ---
if __name__ == "__main__":
    try:
        # 1. Chargement et préparation des documents
        documents_to_index = load_and_prepare_documents(CLIENT_DATA_FILE)

        # 2. Embeddings
        embeddings = OllamaEmbeddings(model="nomic-embed-text")

        # 3. Initialisation du vector store
        vectorstore = initialize_vector_store(
            documents=documents_to_index,
            collection_name=CHROMA_COLLECTION_NAME,
            persist_directory=CHROMA_DB_DIRECTORY,
            embeddings=embeddings,
        )

        # 4. Vérification de qualité
        verify_embedding_quality(vectorstore)

        logger.info(f"✅ Base de connaissances vectorielle '{CHROMA_COLLECTION_NAME}' créée avec succès")
        logger.info(f"📁 Répertoire: {CHROMA_DB_DIRECTORY}")
        logger.info(f"📄 Documents indexés: {len(documents_to_index)}")

    except Exception as e:
        logger.error(f"❌ Erreur lors de la création de la base vectorielle: {e}")
        raise
