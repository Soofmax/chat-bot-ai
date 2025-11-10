from fastapi.testclient import TestClient
import server.app as app_module


class StubPipeline:
    def process(self, question: str) -> str:
        return "Réponse OK"


def test_auth_required_in_production(monkeypatch):
    # Production gating
    monkeypatch.setattr(app_module, "ENV", "production")
    monkeypatch.setattr(app_module, "API_KEYS", {"k1"})
    monkeypatch.setattr(app_module, "ALLOWED_ORIGINS", "http://example.com")
    # Provide a dummy REDIS_URL to satisfy production gating (SlowAPI not used if HAS_SLOWAPI is False)
    monkeypatch.setattr(app_module, "REDIS_URL", "redis://dummy:6379")
    # Stub pipeline to avoid heavy model loading
    monkeypatch.setattr(app_module, "get_pipeline", lambda mode, client_id: StubPipeline())

    client = TestClient(app_module.app)
    payload = {"question": "Test", "client_id": "bms_ventouse", "mode": "main"}

    # Missing Authorization -> 401
    r1 = client.post("/api/chat", json=payload)
    assert r1.status_code == 401

    # Valid Authorization -> 200
    r2 = client.post("/api/chat", json=payload, headers={"Authorization": "Bearer k1"})
    assert r2.status_code == 200
    assert isinstance(r2.json().get("response"), str)