from fastapi.testclient import TestClient
import server.app as app_module


class StubPipeline:
    def process(self, question: str) -> str:
        return "OK"


def test_rbac_client_scope(monkeypatch):
    # Production, auth OK but client_id not allowed for this key -> 403
    monkeypatch.setattr(app_module, "ENV", "production")
    monkeypatch.setattr(app_module, "API_KEYS", {"k1"})
    monkeypatch.setattr(app_module, "ALLOWED_ORIGINS", "http://example.com")
    monkeypatch.setattr(app_module, "API_KEYS_MAP", {"k1": {"allowed_client"}})
    # Provide dummy REDIS_URL to satisfy production gating
    monkeypatch.setattr(app_module, "REDIS_URL", "redis://dummy:6379")
    monkeypatch.setattr(app_module, "get_pipeline", lambda mode, client_id: StubPipeline())

    client = TestClient(app_module.app)
    payload = {"question": "Test", "client_id": "blocked_client", "mode": "main"}

    r = client.post("/api/chat", json=payload, headers={"Authorization": "Bearer k1"})
    assert r.status_code == 403

    # Allowed client succeeds
    payload["client_id"] = "allowed_client"
    r2 = client.post("/api/chat", json=payload, headers={"Authorization": "Bearer k1"})
    assert r2.status_code == 200