import re

from shared.generation import AdvancedOutputParser


def test_parser_removes_prompt_leak_and_dedup():
    parser = AdvancedOutputParser("BrandX")
    text = """# 🎬 MISSION
Contenu du prompt inutilisable
**Réponse :** Merci pour votre message. Merci pour votre message. Contact direct recommandé.
"""
    out = parser.parse(text)
    assert "MISSION" not in out
    assert "Réponse" not in out
    # Deduplication: "Merci pour votre message." should appear only once
    assert out.count("Merci pour votre message") == 1
    assert len(out) >= 25


def test_parser_short_fallback():
    parser = AdvancedOutputParser("BrandX")
    text = "Ok."
    out = parser.parse(text)
    assert "BrandX" in out  # brand in fallback
    assert len(out) >= 25