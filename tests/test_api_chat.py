from fastapi.testclient import TestClient

import server.app as app_module


class StubPipeline:
    def __init__(self):
        pass

    def process(self, question: str) -> str:
        return "Réponse professionnelle: Nous pouvons vous aider. Contactez-nous pour un devis."


def test_api_chat_basic(monkeypatch):
    # Bypass auth by clearing API_KEYS
    monkeypatch.setattr(app_module, "API_KEYS", set())

    # Stub get_pipeline to avoid heavy model downloads
    def stub_get_pipeline(mode: str, client_id: str):
        return StubPipeline()

    monkeypatch.setattr(app_module, "get_pipeline", stub_get_pipeline)

    client = TestClient(app_module.app)

    payload = {"question": "Besoin devis", "client_id": "bms_ventouse", "mode": "main"}
    r = client.post("/api/chat", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["client_id"] == "bms_ventouse"
    assert "response" in data
    assert "Contactez" in data["response"]