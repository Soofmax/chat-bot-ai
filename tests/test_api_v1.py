from fastapi.testclient import TestClient
import server.app as app_module


class StubPipeline:
    def process(self, question: str) -> str:
        return "Réponse professionnelle v1"


def test_api_v1_chat(monkeypatch):
    # Dev: pas d'API_KEYS
    monkeypatch.setattr(app_module, "API_KEYS", set())
    monkeypatch.setattr(app_module, "ENV", "development")
    # Stub pipeline
    monkeypatch.setattr(app_module, "get_pipeline", lambda mode, client_id: StubPipeline())

    with TestClient(app_module.app) as client:
        r = client.post("/v1/chat", json={"question": "Test", "client_id": "bms_ventouse", "mode": "main"})
        assert r.status_code == 200
        assert "response" in r.json()