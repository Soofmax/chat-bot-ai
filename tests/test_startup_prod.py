import pytest
from fastapi.testclient import TestClient
import server.app as app_module


def test_startup_requires_keys_and_cors(monkeypatch):
    # Production: API_KEYS manquant -> RuntimeError
    monkeypatch.setattr(app_module, "ENV", "production")
    monkeypatch.setattr(app_module, "API_KEYS", set())
    monkeypatch.setattr(app_module, "ALLOWED_ORIGINS", "http://example.com")

    with pytest.raises(RuntimeError):
        with TestClient(app_module.build_app()) as _:
            pass