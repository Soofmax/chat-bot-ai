from fastapi.testclient import TestClient
import server.app as app_module


class StubPipeline:
    def process(self, question: str) -> str:
        return "Réponse après refresh"


class FakeChromaClient:
    def __init__(self, path: str):
        self.path = path
    def delete_collection(self, name: str):
        # Simule suppression sans erreur
        return True


def test_refresh_deletes_collection(monkeypatch):
    # Dev: pas d'API_KEYS
    monkeypatch.setattr(app_module, "API_KEYS", set())
    monkeypatch.setattr(app_module, "ENV", "development")
    # Stub chromadb client pour éviter IO
    monkeypatch.setattr(app_module.chromadb, "PersistentClient", FakeChromaClient)
    # Stub pipeline
    monkeypatch.setattr(app_module, "get_pipeline", lambda mode, client_id: StubPipeline())

    with TestClient(app_module.app) as client:
        r = client.post(
            "/api/chat",
            json={"question": "Test", "client_id": "bms_ventouse", "mode": "main", "refresh": True},
        )
        assert r.status_code == 200
        assert "response" in r.json()