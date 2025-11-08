import json
import logging
from typing import Dict, Any

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate

from shared.generation import AdvancedOutputParser, ContextEnhancer, detect_scenario, ResponseQualityChecker
from shared.config import OLLAMA_LLM_MODEL, OLLAMA_EMBED_MODEL, RETRIEVER_K, RETRIEVER_SCORE_THRESHOLD

# --- Configuration ---
CLIENT_ID = "bms_ventouse"
CLIENT_DATA_FILE = f"./clients/{CLIENT_ID}/data.json"
CHROMA_COLLECTION_NAME = CLIENT_ID
CHROMA_DB_DIRECTORY = "./chroma_db"

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ResponseQualityChecker:
    """Vérifie la qualité des réponses générées"""

    @staticmethod
    def check_response_quality(response: str, min_length: int = 50) -> Dict[str, Any]:
        checks = {
            "has_signature": "BMS" in response or "Ventouse" in response,
            "sufficient_length": len(response) >= min_length,
            "has_contact_cta": any(keyword in response.lower() for keyword in
                                   ['contact', 'appel', 'whatsapp', 'email', 'devis', 'disponible']),
            "no_prompt_leak": not any(leak in response for leak in
                                     ["MISSION", "VOCABULAIRE", "DIRECTIVES", "# 🎬"])
        }
        checks["all_passed"] = all(checks.values())
        return checks


def load_client_data() -> Dict[str, Any]:
    """Charge et valide les données client"""
    with open(CLIENT_DATA_FILE, 'r', encoding='utf-8') as f:
        client_data = json.load(f)
    logger.info(f"✅ Données client chargées pour {client_data['entreprise']['nom']}")
    return client_data


def initialize_rag_system(client_data: Dict[str, Any]):
    """Initialise le système RAG complet"""

    # 1. Initialisation des modèles
    logger.info("Initialisation des modèles Ollama...")
    embeddings = OllamaEmbeddings(model=OLLAMA_EMBED_MODEL)
    llm = Ollama(
        model=OLLAMA_LLM_MODEL,
        temperature=0.7,
        num_predict=300,
        top_k=20,
        top_p=0.9,
    )

    # 2. Connexion à la base vectorielle
    vectorstore = Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_DIRECTORY,
    )

    # 3. Retrieveur
    retriever = vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "k": RETRIEVER_K,
            "score_threshold": RETRIEVER_SCORE_THRESHOLD,
        },
    )
 )

    # 4. Template simplifié
    template = """Tu es l'assistant de BMS Ventouse, expert en logistique audiovisuelle.

INFORMATIONS ENTREPRISE:
{context}

CLIENT DIT: "{question}"

SITUATION: {scenario_type}

Ta mission: Réponds en 2-3 phrases courtes et professionnelles. Propose une solution concrète. Termine par un appel à l'action (contact, devis, etc.).

Réponse professionnelle:"""

    # 5. Composants
    context_enhancer = ContextEnhancer(client_data)
    output_parser = AdvancedOutputParser(client_data.get("entreprise", {}).get("nom", "BMS Ventouse"))

    # 6. Prompt
    prompt = PromptTemplate(
        template=template,
        input_variables=["context", "question", "scenario_type"],
    )

    # 7. Chaîne RAG
    def process_query(question: str) -> str:
        try:
            docs = retriever.get_relevant_documents(question)
            context = context_enhancer.enhance(docs)
            scenario = detect_scenario(question)

            logger.info(f"📄 Documents trouvés: {len(docs)}")
            logger.info(f"🎯 Scénario: {scenario}")

            prompt_text = prompt.format(
                context=context,
                question=question,
                scenario_type=scenario,
            )

            raw_response = llm.invoke(prompt_text)
            parsed_response = output_parser.parse(raw_response)
            return parsed_response
        except Exception as e:
            logger.error(f"Erreur traitement: {e}")
            return "Merci pour votre message ! Contactez BMS Ventouse pour une réponse personnalisée."

    return process_query, vectorstore


def main():
    """Fonction principale avec interface utilisateur améliorée"""

    try:
        client_data = load_client_data()
        process_query, vectorstore = initialize_rag_system(client_data)

        collection_count = vectorstore._collection.count()
        logger.info(f"📊 Base vectorielle contenant {collection_count} documents")

        print(f"\n{'='*60}")
        print(f"🤖 CM-AI - Assistant {client_data['entreprise']['nom']}")
        print(f"🎯 {client_data['entreprise']['slogan']}")
        print(f"{'='*60}")
        print("💡 Exemples de questions à tester :")
        print("   • 'Urgence pour tournage demain à Paris'")
        print("   • 'Besoin devis pour ventousage série TV'")
        print("   • 'Vous avez des références sur Netflix ?'")
        print("   • 'Problème autorisation mairie pour plateau'")
        print(f"{'='*60}")
        print("Tapez 'quitter' pour arrêter\n")

        quality_checker = ResponseQualityChecker()

        while True:
            try:
                avis_client = input("\n🎬 Commentaire client : ").strip()

                if avis_client.lower() in ['quitter', 'exit', 'quit']:
                    break

                if not avis_client:
                    continue

                print("\n🧠 Analyse en cours...")

                response = process_query(avis_client)
                quality_report = quality_checker.check_response_quality(response)

                print(f"\n✅ RÉPONSE GÉNÉRÉE :")
                print(f"{'─'*50}")
                print(response)
                print(f"{'─'*50}")

                if not quality_report["all_passed"]:
                    logger.warning("⚠️  Réponse sous-optimale détectée")
            except KeyboardInterrupt:
                print("\n\n👋 Arrêt demandé. Au revoir !")
                break
            except Exception as e:
                logger.error(f"❌ Erreur lors du traitement: {e}")
                print("❌ Désolé, une erreur s'est produite. Veuillez réessayer.")

    except Exception as e:
        logger.error(f"❌ Erreur initialisation: {e}")
        print("❌ Impossible de démarrer l'assistant. Vérifiez la configuration.")


if __name__ == "__main__":
    main()
