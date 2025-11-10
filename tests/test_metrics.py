from fastapi.testclient import TestClient
import server.app as app_module


class FakeInstrumentator:
    def instrument(self, app):
        return self

    def expose(self, app):
        # Ajoute une route /metrics simple
        @app.get("/metrics")
        def _metrics():
            return {"status": "metrics"}
        return app


def test_prometheus_metrics_exposed(monkeypatch):
    # Force l'activation et stub l'instrumentation
    monkeypatch.setattr(app_module, "HAS_PROM", True)
    monkeypatch.setattr(app_module, "Instrumentator", FakeInstrumentator)

    with TestClient(app_module.build_app()) as client:
        r = client.get("/metrics")
        assert r.status_code == 200
        assert r.json().get("status") == "metrics"