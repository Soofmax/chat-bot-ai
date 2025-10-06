import json
import chromadb
import os
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain.docstore.document import Document
from typing import List, Dict, Any
import logging

# --- Configuration ---
CLIENT_ID = "bms_ventouse"
CLIENT_DATA_FILE = f"./clients/{CLIENT_ID}/data.json"
CHROMA_COLLECTION_NAME = CLIENT_ID
CHROMA_DB_DIRECTORY = "./chroma_db"

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataPreprocessor:
    """Classe dédiée au prétraitement des données pour améliorer la qualité des embeddings"""
    
    @staticmethod
    def chunk_text(text: str, max_length: int = 500) -> List[str]:
        """Découpe les textes longs en chunks pour de meilleurs embeddings"""
        words = text.split()
        chunks = []
        current_chunk = []
        
        for word in words:
            if len(' '.join(current_chunk + [word])) <= max_length:
                current_chunk.append(word)
            else:
                chunks.append(' '.join(current_chunk))
                current_chunk = [word]
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks

def load_and_prepare_documents(filepath: str) -> List[Document]:
    """Charge le fichier JSON et le transforme en une liste de 'Documents' pour LangChain."""
    
    logger.info(f"Chargement et parsing du fichier de données : {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Erreur lors du chargement du fichier JSON : {e}")
        raise

    documents = []
    preprocessor = DataPreprocessor()

    # 1. Informations entreprise (enrichies)
    info_sections = [
        f"Entreprise: {data['entreprise']['nom']}",
        f"Slogan: {data['entreprise']['slogan']}",
        f"Mission: {data['entreprise']['mission']}",
        f"Valeurs: {', '.join(data['entreprise']['valeurs'])}",
        f"Positionnement: {data['entreprise']['positioning']}",
        f"Public cible: {data['client_info']['target_audience']}",
        f"Zone d'intervention: {data['client_info']['intervention_zone']}",
        f"Disponibilité: {data['client_info']['business_hours']}"
    ]
    info_text = " | ".join(info_sections)
    
    # Découpage en chunks si nécessaire
    info_chunks = preprocessor.chunk_text(info_text)
    for i, chunk in enumerate(info_chunks):
        documents.append(Document(
            page_content=chunk, 
            metadata={"source": "entreprise_info", "chunk": i, "type": "informations_generales"}
        ))

    # 2. Personnalité IA (détaillée)
    personality_text = (
        f"Personnalité de l'assistant: {data['ai_personality']['profile']} | "
        f"Ton: {data['ai_personality']['tone']} | "
        f"Style de communication: {data['ai_personality']['communication_style']} | "
        f"Mots-clés importants: {', '.join(data['ai_personality']['vocabulaire_metier']['mots_puissants'])} | "
        f"Termes techniques: {', '.join(data['ai_personality']['vocabulaire_metier']['terms_techniques'])}"
    )
    personality_chunks = preprocessor.chunk_text(personality_text)
    for i, chunk in enumerate(personality_chunks):
        documents.append(Document(
            page_content=chunk,
            metadata={"source": "ai_personality", "chunk": i, "type": "comportement_ia"}
        ))

    # 3. Services (un document par service avec détails)
    for service in data['services_detailles']:
        service_details = service.get('details', [])
        service_text = (
            f"Service: {service['name']} | "
            f"Description: {service['description']} | "
            f"Détails: {'; '.join(service_details)}"
        )
        documents.append(Document(
            page_content=service_text,
            metadata={
                "source": "service", 
                "service_name": service['name'],
                "type": "offre_service"
            }
        ))

    # 4. Réponses stratégiques (scénarios métier)
    if 'reponses_strategiques' in data['ai_personality']:
        for scenario_name, scenario_response in data['ai_personality']['reponses_strategiques'].items():
            if isinstance(scenario_response, dict):
                for sub_scenario, response in scenario_response.items():
                    scenario_text = f"Scénario: {scenario_name}_{sub_scenario} | Réponse type: {response}"
                    documents.append(Document(
                        page_content=scenario_text,
                        metadata={
                            "source": "reponses_strategiques",
                            "scenario": f"{scenario_name}_{sub_scenario}",
                            "type": "reponse_automatisee"
                        }
                    ))
            elif isinstance(scenario_response, list):
                for i, response in enumerate(scenario_response):
                    scenario_text = f"Scénario: {scenario_name} | Réponse type {i+1}: {response}"
                    documents.append(Document(
                        page_content=scenario_text,
                        metadata={
                            "source": "reponses_strategiques",
                            "scenario": scenario_name,
                            "type": "reponse_automatisee"
                        }
                    ))

    # 5. Références prestigieuses
    for ref in data['references_prestigieuses']:
        ref_text = (
            f"Référence client: {ref['projet']} | "
            f"Client: {ref['client']} | "
            f"Type: {ref['type']} | "
            f"Spécificité: {ref.get('specificite', 'Non spécifié')}"
        )
        documents.append(Document(
            page_content=ref_text,
            metadata={
                "source": "references",
                "client": ref['client'],
                "type_projet": ref['type'],
                "type": "reference_client"
            }
        ))

    # 6. Scénarios critiques et recommandations (VERSION CORRIGÉE)
    if 'scenarios_critiques' in data:
        for scenario_name, scenario_info in data['scenarios_critiques'].items():
            # Gestion sécurisée des clés optionnelles
            declencheurs = scenario_info.get('declencheur', [])
            reponse = scenario_info.get('reponse', 'Non spécifié')
            action = scenario_info.get('action', 'Non spécifié')
            cta_prioritaire = scenario_info.get('cta_prioritaire', 'Non spécifié')
            
            scenario_text = (
                f"Scénario critique: {scenario_name} | "
                f"Déclencheurs: {', '.join(declencheurs)} | "
                f"Réponse: {reponse} | "
                f"Action: {action} | "
                f"CTA: {cta_prioritaire}"
            )
            documents.append(Document(
                page_content=scenario_text,
                metadata={
                    "source": "scenarios_critiques",
                    "scenario_type": scenario_name,
                    "type": "gestion_crise"
                }
            ))

    # 7. Preuves sociales et témoignages
    if 'preuves_sociales' in data:
        for i, temoignage in enumerate(data['preuves_sociales']['temoignages_metier']):
            documents.append(Document(
                page_content=f"Témoignage client {i+1}: {temoignage}",
                metadata={"source": "preuves_sociales", "type": "temoignage"}
            ))

    logger.info(f"✅ {len(documents)} documents préparés pour l'indexation avec métadonnées enrichies")
    return documents

def initialize_vector_store(documents: List[Document], collection_name: str, persist_directory: str) -> Chroma:
    """Initialise et retourne le vector store Chroma"""
    
    logger.info("Création des embeddings avec Ollama...")
    
    embeddings = OllamaEmbeddings(model="tinyllama")
    
    # Nettoyage de l'ancienne collection
    client = chromadb.PersistentClient(path=persist_directory)
    try:
        client.delete_collection(name=collection_name)
        logger.info(f"Ancienne collection '{collection_name}' supprimée")
    except (ValueError, Exception) as e:
        logger.info(f"Collection '{collection_name}' non trouvée, création nouvelle collection")
    
    # Création du vector store
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=persist_directory,
        collection_metadata={"hnsw:space": "cosine"}  # Optimisation pour la similarité
    )
    
    return vectorstore

def verify_embedding_quality(vectorstore: Chroma, test_queries: List[str] = None):
    """Vérifie la qualité des embeddings avec des requêtes tests"""
    
    if test_queries is None:
        test_queries = [
            "ventousage stationnement",
            "urgence tournage",
            "devis logistique",
            "références Netflix",
            "zone technique plateau"
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
        
        # 2. Initialisation du vector store
        vectorstore = initialize_vector_store(
            documents_to_index, 
            CHROMA_COLLECTION_NAME, 
            CHROMA_DB_DIRECTORY
        )
        
        # 3. Vérification de qualité
        verify_embedding_quality(vectorstore)
        
        logger.info(f"✅ Base de connaissances vectorielle '{CHROMA_COLLECTION_NAME}' créée avec succès")
        logger.info(f"📁 Répertoire: {CHROMA_DB_DIRECTORY}")
        logger.info(f"📄 Documents indexés: {len(documents_to_index)}")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création de la base vectorielle: {e}")
        raise
