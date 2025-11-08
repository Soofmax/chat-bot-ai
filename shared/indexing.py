import json
import logging
from typing import List, Dict, Any

import chromadb
from langchain_community.vectorstores import Chroma
from langchain.docstore.document import Document

logger = logging.getLogger(__name__)


class DataPreprocessor:
    @staticmethod
    def chunk_text(text: str, max_length: int = 500) -> List[str]:
        words = text.split()
        chunks = []
        current = []
        current_len = 0
        for w in words:
            current.append(w)
            current_len += len(w) + 1
            if current_len >= max_length:
                chunks.append(" ".join(current))
                current = []
                current_len = 0
        if current:
            chunks.append(" ".join(current))
        return chunks


def _safe_get(d: Dict[str, Any], path: List[str], default: Any = "") -> Any:
    cur: Any = d
    for p in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(p)
        if cur is None:
            return default
    return cur


def load_and_prepare_documents(filepath: str) -> List[Document]:
    """
    Unified loader that prepares Documents from the JSON client data file.
    Compatible with both main and alt structures.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    docs: List[Document] = []
    preproc = DataPreprocessor()

    # Entreprise info
    entreprise = data.get("entreprise", {})
    ent_name = entreprise.get("nom", "Entreprise")
    ent_city = entreprise.get("ville", "")
    ent_sector = entreprise.get("secteur", "")
    ent_slogan = entreprise.get("slogan", "")
    ent_desc = entreprise.get("description", "")

    info_sections = [
        f"Entreprise: {ent_name}",
        f"Ville: {ent_city}" if ent_city else "",
        f"Secteur: {ent_sector}" if ent_sector else "",
        f"Slogan: {ent_slogan}" if ent_slogan else "",
        f"Description: {ent_desc}" if ent_desc else "",
    ]
    info_text = "\n".join([s for s in info_sections if s])

    for ch in preproc.chunk_text(info_text, max_length=600):
        docs.append(
            Document(
                page_content=ch,
                metadata={"type": "entreprise_info", "source": filepath},
            )
        )

    # Personnalité AI / vocabulaire metier
    ai = data.get("ai_personality", {}) or data.get("personnalite_ai", {}) or {}
    vocab = ai.get("vocabulaire_metier", {})

    personality_text = (
        f"Ton: {ai.get('ton', '')}\nStyle: {ai.get('style', '')}\n"
        f"Vocabulaire: {json.dumps(vocab, ensure_ascii=False)}"
    )
    for ch in preproc.chunk_text(personality_text, max_length=500):
        docs.append(
            Document(
                page_content=ch,
                metadata={"type": "ai_personality", "source": filepath},
            )
        )

    # Services détaillés
    services = data.get("services_detailles", []) or data.get("services", [])
    for s in services:
        title = s.get("titre") or s.get("nom") or "Service"
        desc = s.get("description") or s.get("details") or ""
        capability = s.get("capacites") or s.get("capabilities") or []
        s_text = f"{title} — {desc}\nCapacités: {', '.join(capability) if isinstance(capability, list) else capability}"
        for ch in preproc.chunk_text(s_text, max_length=500):
            docs.append(Document(page_content=ch, metadata={"type": "service", "title": title, "source": filepath}))

    # Réponses stratégiques
    strategiques = ai.get("reponses_strategiques", {}) or {}
    for k, v in strategiques.items():
        if isinstance(v, dict):
            st_text = f"{k}: {json.dumps(v, ensure_ascii=False)}"
        elif isinstance(v, list):
            st_text = f"{k}: {', '.join(v)}"
        else:
            st_text = f"{k}: {v}"
        for ch in preproc.chunk_text(st_text, max_length=500):
            docs.append(Document(page_content=ch, metadata={"type": "reponse_strategique", "name": k, "source": filepath}))

    # Références prestigieuses
    refs = data.get("references_prestigieuses", []) or data.get("references", [])
    for r in refs:
        r_text = json.dumps(r, ensure_ascii=False)
        for ch in preproc.chunk_text(r_text, max_length=400):
            docs.append(Document(page_content=ch, metadata={"type": "reference", "source": filepath}))

    # Scénarios critiques
    scenarios = data.get("scenarios_critiques", {}) or {}
    for name, info in scenarios.items():
        sc_text = f"{name}: {json.dumps(info, ensure_ascii=False)}"
        for ch in preproc.chunk_text(sc_text, max_length=500):
            docs.append(Document(page_content=ch, metadata={"type": "scenario", "name": name, "source": filepath}))

    # Preuves sociales / témoignages
    preuves_sociales = data.get("preuves_sociales", {}) or {}
    temoignages = preuves_sociales.get("temoignages_metier", []) or []
    for t in temoignages:
        t_text = json.dumps(t, ensure_ascii=False)
        for ch in preproc.chunk_text(t_text, max_length=400):
            docs.append(Document(page_content=ch, metadata={"type": "temoignage", "source": filepath}))

    return docs


def initialize_vector_store(
    documents: List[Document],
    collection_name: str,
    persist_directory: str,
    embeddings,
) -> Chroma:
    """
    Initialize or reset a Chroma collection and persist documents.
    """
    client = chromadb.PersistentClient(path=persist_directory)
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        pass

    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=persist_directory,
        collection_metadata={"hnsw:space": "cosine"},
    )
    return vectorstore