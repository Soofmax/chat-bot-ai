from shared.generation import detect_scenario, ResponseQualityChecker


def test_detect_scenario():
    assert detect_scenario("Urgent tournage demain") == "Urgence"
    assert detect_scenario("Pouvez-vous faire un devis ?") == "Devis"
    assert detect_scenario("Avez-vous des références ou un portfolio ?") == "Références"
    assert detect_scenario("Bonjour") == "Question générale"


def test_quality_checker():
    qc = ResponseQualityChecker("BrandX")
    resp = "Merci pour votre message. Contactez-nous pour un devis personnalisé BrandX."
    report = qc.check(resp)
    assert report["all_passed"]
    assert report["has_cta"]
    assert report["sufficient_length"]
    assert report["no_prompt_leak"]