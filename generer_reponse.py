import json
import re
from typing import Dict, List, Any, Optional
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.llms import Ollama
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough, RunnableLambda
from langchain.schema.output_parser import StrOutputParser
from langchain.schema import BaseOutputParser
import logging

# --- Configuration ---
CLIENT_ID = "bms_ventouse"
CLIENT_DATA_FILE = f"./clients/{CLIENT_ID}/data.json"
CHROMA_COLLECTION_NAME = CLIENT_ID
CHROMA_DB_DIRECTORY = "./chroma_db"

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedOutputParser(BaseOutputParser):
    """Parser avancé pour nettoyer et formater les réponses"""
    
    def parse(self, text: str) -> str:
        # Nettoyage des artefacts de génération
        cleaned_text = re.sub(r'\[.*?\]', '', text)
        cleaned_text = re.sub(r'\*+\s?', '', cleaned_text)
        cleaned_text = re.sub(r'\n+', '\n', cleaned_text)
        
        # Suppression du prompt si présent dans la réponse (CORRECTION CRITIQUE)
        if "# 🎬 MISSION" in cleaned_text or "VOCABULAIRE" in cleaned_text:
            # Le modèle a renvoyé le prompt - extraire seulement la réponse
            parts = cleaned_text.split("**Réponse :**")
            if len(parts) > 1:
                cleaned_text = parts[-1].strip()
            else:
                # Chercher après "Réponse:"
                parts = cleaned_text.split("Réponse:")
                if len(parts) > 1:
                    cleaned_text = parts[-1].strip()
        
        # Suppression des phrases répétées
        sentences = cleaned_text.split('. ')
        unique_sentences = []
        for sentence in sentences:
            if sentence and sentence not in unique_sentences:
                unique_sentences.append(sentence)
        
        result = '. '.join(unique_sentences).strip()
        
        # Si la réponse est trop courte ou contient encore du prompt, fallback
        if len(result) < 30 or "MISSION" in result or "VOCABULAIRE" in result:
            return "Merci pour votre message ! Notre équipe BMS Ventouse est à votre disposition. Contactez-nous au 06 XX XX XX XX pour une réponse personnalisée. 🎬"
        
        return result

class ContextEnhancer:
    """Améliore le contexte récupéré avec des métadonnées intelligentes"""
    
    def __init__(self, client_data: Dict):
        self.client_data = client_data
    
    def enhance_context(self, docs: List[Any]) -> str:
        """Enrichit le contexte avec des informations structurées"""
        if not docs:
            # FALLBACK CRITIQUE : Fournir un contexte de base quand aucun document n'est trouvé
            return f"""
BMS Ventouse - Expert logistique audiovisuelle
Services: Ventousage véhicules, gestion stationnement plateau, régie technique
Contact: Disponible 24/7 pour urgences tournage
Références: Netflix, Amazon Prime, grandes productions françaises
"""
        
        enhanced_parts = []
        for doc in docs[:3]:  # Limiter à 3 docs pour tinyllama
            source_type = doc.metadata.get('type', 'general')
            source_content = doc.page_content
            
            if source_type == 'reference_client':
                enhanced_parts.append(f"Référence: {source_content}")
            elif source_type == 'offre_service':
                enhanced_parts.append(f"Service: {source_content}")
            elif source_type == 'gestion_crise':
                enhanced_parts.append(f"Urgent: {source_content}")
            else:
                enhanced_parts.append(source_content)
        
        return "\n".join(enhanced_parts)

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
    try:
        with open(CLIENT_DATA_FILE, 'r', encoding='utf-8') as f:
            client_data = json.load(f)
        logger.info(f"✅ Données client chargées pour {client_data['entreprise']['nom']}")
        return client_data
    except Exception as e:
        logger.error(f"❌ Erreur chargement données client: {e}")
        raise

def initialize_rag_system(client_data: Dict[str, Any]):
    """Initialise le système RAG complet"""
    
    # 1. Initialisation des modèles
    logger.info("Initialisation des modèles Ollama...")
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    llm = Ollama(
        model="tinyllama",
        temperature=0.7,  # Plus créatif pour compenser la petite taille
        num_predict=300,  # Réponses plus courtes = plus rapide
        top_k=20,
        top_p=0.9
    )
    
    # 2. Connexion à la base vectorielle
    vectorstore = Chroma(
        collection_name=CHROMA_COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=CHROMA_DB_DIRECTORY
    )
    
    # 3. Retrieveur avec seuil abaissé (CORRECTION CRITIQUE)
    retriever = vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "k": 3,  # Seulement 3 docs pour tinyllama (moins de contexte)
            "score_threshold": 0.3  # ABAISSÉ de 0.6 à 0.3 pour plus de résultats
        }
    )
    
    # 4. Template de prompt SIMPLIFIÉ pour tinyllama (CORRECTION CRITIQUE)
    template = """Tu es l'assistant de BMS Ventouse, expert en logistique audiovisuelle.

INFORMATIONS ENTREPRISE:
{context}

CLIENT DIT: "{question}"

SITUATION: {scenario_type}

Ta mission: Réponds en 2-3 phrases courtes et professionnelles. Propose une solution concrète. Termine par un appel à l'action (contact, devis, etc.).

Réponse professionnelle:"""
    
    # 5. Initialisation des composants avancés
    context_enhancer = ContextEnhancer(client_data)
    output_parser = AdvancedOutputParser()
    
    # 6. Détection de scénario simplifiée
    def detect_scenario(question: str) -> str:
        question_lower = question.lower()
        
        if any(kw in question_lower for kw in ['urgent', 'demain', 'crise']):
            return "URGENCE détectée"
        elif any(kw in question_lower for kw in ['prix', 'devis', 'budget']):
            return "Demande de DEVIS"
        elif any(kw in question_lower for kw in ['référence', 'expérience']):
            return "Demande de RÉFÉRENCES"
        else:
            return "Question générale"
    
    # 7. Construction du prompt
    prompt = PromptTemplate(
        template=template,
        input_variables=["context", "question", "scenario_type"]
    )
    
    # 8. Chaîne RAG SIMPLIFIÉE (CORRECTION CRITIQUE)
    def process_query(question: str) -> str:
        try:
            # Récupération du contexte
            docs = retriever.get_relevant_documents(question)
            context = context_enhancer.enhance_context(docs)
            scenario = detect_scenario(question)
            
            # Log pour debugging
            logger.info(f"📄 Documents trouvés: {len(docs)}")
            logger.info(f"🎯 Scénario: {scenario}")
            
            # Génération
            prompt_text = prompt.format(
                context=context,
                question=question,
                scenario_type=scenario
            )
            
            # Appel au LLM
            raw_response = llm.invoke(prompt_text)
            
            # Parsing
            parsed_response = output_parser.parse(raw_response)
            
            return parsed_response
            
        except Exception as e:
            logger.error(f"Erreur traitement: {e}")
            return "Merci pour votre message ! Contactez BMS Ventouse pour une réponse personnalisée. 🎬"
    
    return process_query, vectorstore

def main():
    """Fonction principale avec interface utilisateur améliorée"""
    
    try:
        # Chargement des données
        client_data = load_client_data()
        
        # Initialisation du système RAG
        process_query, vectorstore = initialize_rag_system(client_data)
        
        # Vérification du nombre de documents
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
                
                # Génération de la réponse
                response = process_query(avis_client)
                
                # Vérification qualité
                quality_report = quality_checker.check_response_quality(response)
                
                # Affichage des résultats
                print(f"\n✅ RÉPONSE GÉNÉRÉE :")
                print(f"{'─'*50}")
                print(response)
                print(f"{'─'*50}")
                
                # Rapport qualité
                if not quality_report["all_passed"]:
                    logger.warning("⚠️  Réponse sous-optimale détectée")
                    logger.debug(f"Quality checks: {quality_report}")
                
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
