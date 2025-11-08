import time
from fastapi.testclient import TestClient
import server.app as app_module


class StubPipeline:
    def __init__(self):
        pass

    def process(self, question: str) -> str:
        return "Réponse professionnelle: Nous pouvons vous aider. Contactez-nous pour un devis."


def test_rate_limit_ip(monkeypatch):
    # Disable auth
    monkeypatch.setattr(app_module, "API_KEYS", set())
    # Configure rate limit: 2 req per 1 sec
    monkeypatch.setattr(app_module, "RATE_LIMIT_WINDOW_SEC", 1)
    monkeypatch.setattr(app_module, "RATE_LIMIT_MAX_REQ", 2)
    monkeypatch.setattr(app_module, "RATE_LIMIT_KEY", "ip")
    # Reset buckets
    app_module.RL_BUCKETS.clear()
    # Stub pipeline to avoid heavy model downloads
    monkeypatch.setattr(app_module, "get_pipeline", lambda mode, client_id: StubPipeline())

    client = TestClient(app_module.app)

    payload = {"question": "Test", "client_id": "bms_ventouse", "mode": "main"}
    r1 = client.post("/api/chat", json=payload)
    r2 = client.post("/api/chat", json=payload)
    r3 = client.post("/api/chat", json=payload)

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r3.status_code == 429

    # Wait for window reset
    time.sleep(1.1)
    r4 = client.post("/api/chat", json=payload)
    assert r4.status_code == 200


def test_rate_limit_apikey(monkeypatch):
    # Enable auth and use API key-based limiting
    monkeypatch.setattr(app_module, "API_KEYS", {"k1"})
    monkeypatch.setattr(app_module, "RATE_LIMIT_WINDOW_SEC", 1)
    monkeypatch.setattr(app_module, "RATE_LIMIT_MAX_REQ", 1)
    monkeypatch.setattr(app_module, "RATE_LIMIT_KEY", "apikey")
    app_module.RL_BUCKETS.clear()
    # Stub pipeline
    monkeypatch.setattr(app_module, "get_pipeline", lambda mode, client_id: StubPipeline())

    client = TestClient(app_module.app)
    headers = {"Authorization": "Bearer k1"}

    payload = {"question": "Test", "client_id": "bms_ventouse", "mode": "main"}
    r1 = client.post("/api/chat", json=payload, headers=headers)
    r2 = client.post("/api/chat", json=payload, headers=headers)

    assert r1.status_code == 200
    assert r2.status_code == 429