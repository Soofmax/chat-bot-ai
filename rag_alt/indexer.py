import logging
from typing import List

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings

from shared.indexing import load_and_prepare_documents, initialize_vector_store

# Configuration (RAG séparé)
CLIENT_ID = "template_client"  # Changez pour votre nouveau client
CLIENT_DATA_FILE = f"./rag_alt/clients/{CLIENT_ID}/data.json"
CHROMA_COLLECTION_NAME = f"rag_alt_{CLIENT_ID}"
CHROMA_DB_DIRECTORY = "./rag_alt/chroma_db_alt"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def verify(vectorstore: Chroma, queries: List[str] = None):
    if queries is None:
        queries = ["services", "devis", "urgence", "références"]
    for q in queries:
        res = vectorstore.similarity_search(q, k=2)
        logger.info(f"Requête: '{q}' -> {len(res)} résultats")


if __name__ == "__main__":
    docs = load_and_prepare_documents(CLIENT_DATA_FILE)
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    vs = initialize_vector_store(
        documents=docs,
        collection_name=CHROMA_COLLECTION_NAME,
        persist_directory=CHROMA_DB_DIRECTORY,
        embeddings=embeddings,
    )
    verify(vs)
    logger.info(f"OK — Base vectorielle '{CHROMA_COLLECTION_NAME}' créée dans {CHROMA_DB_DIRECTORY}")