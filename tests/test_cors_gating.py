import pytest
from fastapi.testclient import TestClient
import server.app as app_module


def test_cors_wildcard_disallowed_in_production(monkeypatch):
    # Production with wildcard origins should fail startup
    monkeypatch.setattr(app_module, "ENV", "production")
    monkeypatch.setattr(app_module, "API_KEYS", {"k1"})
    monkeypatch.setattr(app_module, "ALLOWED_ORIGINS", "*")

    with pytest.raises(RuntimeError):
        TestClient(app_module.app)


def test_cors_allowed_origin_headers(monkeypatch):
    # Non-production: allow specific origin and check headers
    monkeypatch.setattr(app_module, "ENV", "development")
    monkeypatch.setattr(app_module, "ALLOWED_ORIGINS", "http://example.com")
    client = TestClient(app_module.app)
    r = client.options("/api/chat", headers={"Origin": "http://example.com"})
    # CORS middleware should be active; status may be 200 or 404 depending route,
    # but headers should include Access-Control-Allow-Origin for allowed origin.
    assert r.headers.get("access-control-allow-origin") == "http://example.com"