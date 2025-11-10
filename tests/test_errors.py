from fastapi.testclient import TestClient
import server.app as app_module


def test_file_not_found_error(monkeypatch):
    # Dev: sans auth
    monkeypatch.setattr(app_module, "API_KEYS", set())
    monkeypatch.setattr(app_module, "ENV", "development")
    # get_pipeline -> FileNotFoundError pour couvrir la branche d'erreur
    def raise_fn(mode: str, client_id: str):
        raise FileNotFoundError("missing")
    monkeypatch.setattr(app_module, "get_pipeline", raise_fn)

    with TestClient(app_module.app) as client:
        r = client.post("/api/chat", json={"question": "Test", "client_id": "missing", "mode": "main"})
        assert r.status_code == 200
        body = r.json()
        assert "error" in body and "introuvable" in body.get("error","")