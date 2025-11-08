import json
import re
import logging
from typing import Dict, List, Any
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.schema import BaseOutputParser

# Configuration (RAG séparé)
CLIENT_ID = "template_client"  # Changez pour votre nouveau client
CLIENT_DATA_FILE = f"./rag_alt/clients/{CLIENT_ID}/data.json"
CHROMA_COLLECTION_NAME = f"rag_alt_{CLIENT_ID}"
CHROMA_DB_DIRECTORY = "./rag_alt/chroma_db_alt"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class AdvancedOutputParser(BaseOutputParser):
    def __init__(self, brand_name: str):
        self.brand_name = brand_name

    def parse(self, text: str) -> str:
        t = re.sub(r"\[.*?\]", "", text)
        t = re.sub(r"\*+\s?", "", t)
        t = re.sub(r"\n+", "\n", t)

        # Supprime d'éventuelles sections de prompt leak
        for marker in ["MISSION", "VOCABULAIRE", "#"]:
            if marker in t:
                parts = re.split(r"Réponse\s*:|\*\*Réponse\s*:?\*\*", t)
                if len(parts) > 1:
                    t = parts[-1].strip()

        # Déduplique les phrases
        sentences = [s.strip() for s in t.split(". ") if s.strip()]
        uniq = []
        for s in sentences:
            if s not in uniq:
                uniq.append(s)
        res = ". ".join(uniq).strip()

        if len(res) < 25:
            return f"Merci pour votre message. L'équipe {self.brand_name} vous répond rapidement. Contact direct recommandé pour un devis ou une précision."

        return res


class ContextEnhancer:
    def __init__(self, client_data: Dict):
        self.client_data = client_data

    def enhance_context(self, docs: List[Any]) -> str:
        if not docs:
            ent = self.client_data.get("entreprise", {})
            return f"{ent.get('nom','Votre entreprise')} — {ent.get('slogan','')} | Services principaux disponibles. Contact 24/7 si précisé."
        parts = []
        for d in docs[:3]:
            parts.append(d.page_content)
        return "\n".join(parts)


class ResponseQualityChecker:
    def __init__(self, brand_name: str):
        self.brand_name = brand_name

    def check(self, response: str, min_length: int = 50) -> Dict[str, Any]:
        rlower = response.lower()
        checks = {
            "has_brand": (self.brand_name.lower() in rlower) or ("contact" in rlower),
            "sufficient_length": len(response) >= min_length,
            "has_cta": any(k in rlower for k in ["contact", "appel", "whatsapp", "email", "devis", "disponible"]),
            "no_prompt_leak": not any(k in response for k in ["MISSION", "VOCABULAIRE", "# "]),
        }
        checks["all_passed"] = all(checks.values())
        return checks


def load_client_data() -> Dict[str, Any]:
    with open(CLIENT_DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    logger.info(f"Données client chargées: {data.get('entreprise',{}).get('nom','(inconnu)')}")
    return data


def initialize_rag(client_data: Dict[str, Any]):
    brand_name = client_data.get("entreprise", {}).get("nom", "Votre entreprise")

    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    llm = Ollama(model="tinyllama", temperature=0.7, num_predict=300, top_k=20, top_p=0.9)

    vectorstore = Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_DIRECTORY,
    )

    retriever = vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": 3, "score_threshold": 0.3},
    )

    template = """Tu es l'assistant de {brand_name}.

CONTEXTE:
{context}

CLIENT DIT: "{question}"

SITUATION: {scenario}

Mission: Réponds en 2-3 phrases claires, professionnelles et orientées solution. Termine par un appel à l'action (contact, devis, etc.).

Réponse:"""

    prompt = PromptTemplate(
        template=template, input_variables=["brand_name", "context", "question", "scenario"]
    )

    enhancer = ContextEnhancer(client_data)
    parser = AdvancedOutputParser(brand_name)

    def detect_scenario(q: str) -> str:
        ql = q.lower()
        if any(k in ql for k in ["urgent", "demain", "crise", "last minute"]):
            return "Urgence"
        if any(k in ql for k in ["prix", "devis", "budget", "tarif"]):
            return "Devis"
        if any(k in ql for k in ["référence", "reference", "portfolio"]):
            return "Références"
        return "Question générale"

    def process(question: str) -> str:
        docs = retriever.get_relevant_documents(question)
        context = enhancer.enhance_context(docs)
        scen = detect_scenario(question)
        prompt_text = prompt.format(brand_name=brand_name, context=context, question=question, scenario=scen)
        raw = llm.invoke(prompt_text)
        return parser.parse(raw)

    return process, vectorstore, brand_name


def main():
    try:
        client_data = load_client_data()
        process, vectorstore, brand = initialize_rag(client_data)

        count = vectorstore._collection.count()
        logger.info(f"Base vectorielle (alt) contient {count} documents")

        print("\n" + "=" * 60)
        print(f"Assistant (RAG séparé) — {brand}")
        print("=" * 60)
        print("Exemples:")
        print(" - Urgence demain sur Paris, pouvez-vous aider ?")
        print(" - Besoin d'un devis rapide pour vos services")
        print(" - Avez-vous des références ?")
        print("Tapez 'quitter' pour sortir.")
        qc = ResponseQualityChecker(brand)

        while True:
            user = input("\nQuestion client: ").strip()
            if user.lower() in {"quitter", "exit", "quit"}:
                break
            if not user:
                continue
            print("\nGénération...")
            resp = process(user)
            print("\nRéponse:")
            print("-" * 50)
            print(resp)
            print("-" * 50)
            report = qc.check(resp)
            if not report["all_passed"]:
                logger.warning("Réponse potentiellement perfectible (alt)")

    except KeyboardInterrupt:
        print("\nArrêt.")
    except Exception as e:
        logger.error(f"Erreur: {e}")
        print("Impossible de démarrer l'assistant (alt). Vérifiez la configuration.")


if __name__ == "__main__":
    main()