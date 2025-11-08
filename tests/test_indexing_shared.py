import json
from pathlib import Path

from shared.indexing import load_and_prepare_documents


def test_load_and_prepare_documents(tmp_path):
    # Build a minimal client data file combining expected fields
    data = {
        "entreprise": {
            "nom": "BrandX",
            "slogan": "Excellence au quotidien",
            "ville": "Paris",
            "secteur": "Audiovisuel",
            "description": "Prestations de ventousage et régie.",
        },
        "ai_personality": {
            "ton": "professionnel",
            "style": "direct",
            "vocabulaire_metier": {
                "mots_puissants": ["urgence", "devis"],
                "terms_techniques": ["régie", "stationnement"],
            },
            "reponses_strategiques": {
                "Urgence": {"action": "Intervention rapide"},
                "Devis": ["Proposer devis standard", "Proposer devis sur mesure"],
            },
        },
        "services_detailles": [
            {"name": "Ventousage", "description": "Ventousage véhicules.", "details": ["Zone rouge", "Permis temporaires"]},
        ],
        "references_prestigieuses": [
            {"client": "Netflix", "projet": "Série X", "type": "Plateau", "specificite": "Nuit"},
        ],
        "scenarios_critiques": {
            "Crise stationnement": {
                "declencheur": ["fourrière", "verbalisation"],
                "reponse": "Coordination mairie",
                "action": "Régie on-site",
                "cta_prioritaire": "Appel immédiat",
            }
        },
        "preuves_sociales": {
            "temoignages_metier": ["Excellent service", "Equipe réactive"],
        },
    }
    p = tmp_path / "client.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    docs = load_and_prepare_documents(str(p))
    assert isinstance(docs, list)
    assert len(docs) > 5

    # Ensure some metadata types exist
    types = {d.metadata.get("type") for d in docs}
    assert {"entreprise_info", "ai_personality", "service", "reponse_strategique", "reference", "scenario", "temoignage"} & types