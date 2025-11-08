#!/usr/bin/env python3
import json
import re
from pathlib import Path

SAFE_ID = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")

DEFAULT_PROMPT = (
    "Tu es l'assistant de {brand_name}.\n\n"
    "CONTEXTE:\n{context}\n\n"
    "CLIENT DIT: \"{question}\"\n\n"
    "SITUATION: {scenario}\n\n"
    "Mission: Réponds en 2-3 phrases claires, professionnelles et orientées solution. "
    "Termine par un appel à l'action (contact, devis, etc.).\nRéponse:"
)

def ask(prompt: str, default: str = "") -> str:
    s = input(f"{prompt} [{'Entrée' if default == '' else default}]: ").strip()
    return s if s else default

def ask_list(prompt: str, default: str = "") -> list[str]:
    s = ask(prompt + " (séparé par des virgules)", default)
    return [x.strip() for x in s.split(",") if x.strip()]

def ask_yes_no(prompt: str, default_yes: bool = True) -> bool:
    default = "o" if default_yes else "n"
    s = input(f"{prompt} [o/n, défaut {default}]: ").strip().lower()
    if s in {"o", "oui", "y", "yes"}:
        return True
    if s in {"n", "non", "no"}:
        return False
    return default_yes

def ensure_safe_client_id(client_id: str) -> str:
    if not SAFE_ID.match(client_id):
        raise ValueError("client_id invalide: lettres/chiffres/_/-, max 64 caractères")
    return client_id

def main():
    print("=== Assistant de création de client (wizard) ===")

    # Choix du mode
    mode_alt = ask_yes_no("Créer dans rag_alt/clients (alt) ? (sinon clients/)", False)
    base_dir = Path("./rag_alt/clients" if mode_alt else "./clients")

    # Identifiant et marque
    while True:
        try:
            client_id = ensure_safe_client_id(ask("Identifiant client (slug)", "nouveau_client"))
            break
        except ValueError as e:
            print(f"Erreur: {e}")

    brand_name = ask("Nom de la marque/entreprise", "Ma Marque")
    slogan = ask("Slogan", "Votre partenaire fiable et réactif")
    mission = ask("Mission", "Offrir des services de qualité avec réactivité et transparence")
    valeurs = ask_list("Valeurs", "Professionnalisme, Réactivité, Fiabilité")
    positioning = ask("Positionnement", "Leader local sur les services techniques audiovisuels")

    # Contacts et infos
    email = ask("Email de contact", "contact@example.com")
    phone = ask("Téléphone", "+33 1 23 45 67 89")
    zones = ask_list("Zones d'intervention", "Paris, Île-de-France")
    horaires = ask("Horaires", "Lun-Ven 9h-18h")

    # Services
    services = []
    print("\nAjout de services (laisser le nom vide pour terminer)")
    while True:
        nom = ask("Service - nom", "")
        if not nom:
            break
        description = ask("Service - description", "Description courte")
        details = ask_list("Service - détails", "Transport, Installation, Coordination")
        services.append({"nom": nom, "description": description, "details": details})

    if not services:
        # Valeurs par défaut si aucun service saisi
        services = [
            {"nom": "Logistique plateau", "description": "Gestion complète du plateau", "details": ["Transport", "Installation", "Coordination"]},
            {"nom": "Autorisation tournage", "description": "Démarches et relations mairie", "details": []},
        ]

    # Personnalité IA
    profile = ask("Personnalité IA - profil", "assistant client professionnel")
    tone = ask("Personnalité IA - ton", "professionnel, chaleureux")
    comm_style = ask("Personnalité IA - style de communication", "direct et orienté solution")
    mots_puissants = ask_list("Vocabulaire - mots puissants", "réactif, expert, clé en main, accompagnement")
    terms_techniques = ask_list("Vocabulaire - termes techniques", "sécurité plateau, repérage, permis de tournage")

    # Références et scénarios
    references = ask_list("Références prestigieuses", "Netflix, Canal+, Arte")
    print("\nScénarios critiques (laisser vide pour les valeurs par défaut)")
    scen_urgence = ask("Scénario - urgence", "Demande urgente avec tournage imminent")
    scen_devis = ask("Scénario - devis", "Demande de chiffrage détaillé")
    scen_refs = ask("Scénario - références", "Besoin d'exemples de projets similaires")

    # Preuves sociales
    temoignages = ask_list("Témoignages métier", "Service impeccable, équipe réactive., Accompagnement de qualité du début à la fin.")

    # Prompt template
    use_custom_prompt = ask_yes_no("Définir un prompt personnalisé ?", False)
    if use_custom_prompt:
        print("\nLe prompt doit contenir les variables {brand_name}, {context}, {question}, {scenario}.")
        prompt_template = ask("Prompt personnalisé", DEFAULT_PROMPT)
    else:
        prompt_template = DEFAULT_PROMPT

    data = {
        "entreprise": {
            "nom": brand_name,
            "slogan": slogan,
            "mission": mission,
            "valeurs": valeurs,
            "positioning": positioning,
        },
        "client_info": {
            "cibles": ["Production TV", "Cinéma", "Publicité"],
            "contacts": {"email": email, "phone": phone},
            "zone_intervention": zones,
            "horaires": horaires,
        },
        "services_detailles": services,
        "ai_personality": {
            "profile": profile,
            "tone": tone,
            "communication_style": comm_style,
            "vocabulaire_metier": {
                "mots_puissants": mots_puissants,
                "terms_techniques": terms_techniques,
            },
        },
        "references_prestigieuses": references,
        "scenarios_critiques": {
            "urgence": scen_urgence,
            "devis": scen_devis,
            "references": scen_refs,
        },
        "preuves_sociales": {
            "temoignages_metier": temoignages,
        },
        "prompt_template": prompt_template,
    }

    out_dir = base_dir / client_id
    out_file = out_dir / "data.json"
    out_dir.mkdir(parents=True, exist_ok=True)

    with out_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("\n=== Client créé avec succès ===")
    print(f"Fichier: {out_file}")

if __name__ == "__main__":
    main()