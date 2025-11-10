from fastapi.testclient import TestClient
import server.app as app_module


def test_request_id_header_present(monkeypatch):
    # Build a fresh app
    monkeypatch.setattr(app_module, "ENV", "development")
    with TestClient(app_module.build_app()) as client:
        r = client.get("/healthz")
        assert r.status_code == 200
        assert r.headers.get("X-Request-ID")