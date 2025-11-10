import pytest
from fastapi.testclient import TestClient
import server.app as app_module


def test_cors_wildcard_disallowed_in_production(monkeypatch):
    # Production with wildcard origins should fail startup
    monkeypatch.setattr(app_module, "ENV", "production")
    monkeypatch.setattr(app_module, "API_KEYS", {"k1"})
    monkeypatch.setattr(app_module, "ALLOWED_ORIGINS", "*")

    with pytest.raises(RuntimeError):
        with TestClient(app_module.build_app()) as _:
            pass


def test_cors_allowed_origin_headers(monkeypatch):
    # Non-production: allow specific origin and check headers
    monkeypatch.setattr(app_module, "ENV", "development")
    monkeypatch.setattr(app_module, "ALLOWED_ORIGINS", "http://example.com")
    with TestClient(app_module.build_app()) as client:
        r = client.options(
            "/api/chat",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type",
            },
        )
        # CORS middleware should echo the allowed origin
        assert r.headers.get("access-control-allow-origin") == "http://example.com"