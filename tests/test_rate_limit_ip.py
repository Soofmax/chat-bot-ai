from fastapi.testclient import TestClient
import server.app as app_module


class StubPipeline:
    def process(self, question: str) -> str:
        return "OK"


def test_rate_limit_ip_fallback(monkeypatch):
    # Dev: limiter en mémoire
    monkeypatch.setattr(app_module, "ENV", "development")
    monkeypatch.setattr(app_module, "API_KEYS", set())
    monkeypatch.setattr(app_module, "REDIS_URL", "")
    # Réduire fenêtre et limite
    monkeypatch.setattr(app_module, "RATE_LIMIT_WINDOW_SEC", 60)
    monkeypatch.setattr(app_module, "RATE_LIMIT_MAX_REQ", 1)
    # Stub pipeline
    monkeypatch.setattr(app_module, "get_pipeline", lambda mode, client_id: StubPipeline())

    with TestClient(app_module.app) as client:
        payload = {"question": "Test", "client_id": "bms_ventouse", "mode": "main"}
        r1 = client.post("/api/chat", json=payload)
        assert r1.status_code == 200
        r2 = client.post("/api/chat", json=payload)
        assert r2.status_code == 429