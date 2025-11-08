from fastapi.testclient import TestClient
import server.app as app_module


def test_security_headers_present(monkeypatch):
    monkeypatch.setattr(app_module, "ENV", "development")
    client = TestClient(app_module.app)
    r = client.get("/healthz")
    hdrs = r.headers
    assert hdrs.get("Strict-Transport-Security") is not None
    assert hdrs.get("X-Content-Type-Options") == "nosniff"
    assert hdrs.get("X-Frame-Options") == "DENY"
    assert hdrs.get("Referrer-Policy") == "no-referrer"
    assert "Content-Security-Policy" in hdrs