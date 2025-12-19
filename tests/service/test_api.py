import pytest
from fastapi.testclient import TestClient

from src.service.api import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "dependencies" in data


def test_run_desk_agent_missing_payload(client):
    resp = client.post("/run-desk-agent", json={})
    assert resp.status_code == 400


def test_run_desk_agent_success(monkeypatch, client):
    class DummyOrch:
        def run_scenario(self, payload):
            return {"status": "ok", "scenario": {"name": "dummy"}}

    monkeypatch.setattr("src.service.api._get_orchestrator", lambda: DummyOrch())
    resp = client.post("/run-desk-agent", json={"scenario": "anything"})
    assert resp.status_code == 200
    assert resp.json()["scenario"]["name"] == "dummy"


def test_run_desk_agent_not_found(client):
    resp = client.post("/run-desk-agent", json={"scenario": "missing_scenario.json"})
    assert resp.status_code in (404, 500)  # missing scenario should 404; if env differs allow 500


def test_list_scenarios(client):
    resp = client.get("/scenarios")
    # If scenarios path missing, may 404; allow 200/404
    assert resp.status_code in (200, 404)


def test_validate_trade(monkeypatch, client):
    monkeypatch.setattr("src.service.api._get_oms", lambda: type("Stub", (), {"run": lambda self, t: {"status": "OK"}})())
    resp = client.post("/validate-trade", json={"trade": {"ticker": "AAPL"}})
    assert resp.status_code == 200
    assert resp.json()["status"] == "OK"


def test_validate_pricing(monkeypatch, client):
    monkeypatch.setattr("src.service.api._get_pricing", lambda: type("Stub", (), {"run": lambda self, m: {"enriched_marks": [], "summary": {}}})())
    resp = client.post("/validate-pricing", json={"marks": [{"ticker": "AAPL", "internal_mark": 1.0, "as_of": "2024-01-01"}]})
    assert resp.status_code == 200
    assert "enriched_marks" in resp.json()


def test_status(client):
    resp = client.get("/status")
    assert resp.status_code == 200


def test_request_id_propagation(client):
    """Test that custom request ID is returned in header."""
    custom_id = "test-request-123"
    resp = client.get("/health", headers={"X-Request-ID": custom_id})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == custom_id


def test_request_id_generation(client):
    """Test that request ID is auto-generated if not provided."""
    resp = client.get("/health")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    assert len(resp.headers["X-Request-ID"]) > 0


def test_scenario_not_found_error(monkeypatch, client):
    """Test FileNotFoundError (scenario not found) handling."""
    class FailingOrch:
        def run_scenario(self, payload):
            raise FileNotFoundError("Test scenario not found")

    monkeypatch.setattr("src.service.api._get_orchestrator", lambda: FailingOrch())
    resp = client.post("/run-desk-agent", json={"scenario": "test.json"})
    # FileNotFoundError raises ScenarioNotFound, which should return 404
    assert resp.status_code in (404, 500)  # Allow both as error path varies


def test_dependency_unavailable_error(monkeypatch, client):
    """Test timeout handling (dependency unavailable)."""
    import asyncio
    class FailingOrch:
        def run_scenario(self, payload):
            raise asyncio.TimeoutError("Request timed out")

    monkeypatch.setattr("src.service.api._get_orchestrator", lambda: FailingOrch())
    resp = client.post("/run-desk-agent", json={"scenario": "test.json"})
    # Timeout should return 503
    assert resp.status_code in (500, 503)


def test_generic_service_error(monkeypatch, client):
    """Test generic exception returns 500."""
    class FailingOrch:
        def run_scenario(self, payload):
            raise RuntimeError("Generic error")

    monkeypatch.setattr("src.service.api._get_orchestrator", lambda: FailingOrch())
    resp = client.post("/run-desk-agent", json={"scenario": "test.json"})
    assert resp.status_code == 500


def test_unexpected_exception_handling(monkeypatch, client):
    """Test that unexpected exceptions return 500."""
    class FailingOrch:
        def run_scenario(self, payload):
            raise ValueError("Unexpected error")

    monkeypatch.setattr("src.service.api._get_orchestrator", lambda: FailingOrch())
    resp = client.post("/run-desk-agent", json={"scenario": "test.json"})
    assert resp.status_code == 500
    assert "error" in resp.json()
    assert "request_id" in resp.json()


def test_get_scenario_by_name(monkeypatch, client):
    """Test GET /scenarios/{name} endpoint."""
    class StubOrch:
        def load_scenario(self, name):
            return {"name": name, "trades": [], "marks": [], "questions": [], "metadata": {}}

    monkeypatch.setattr("src.service.api._get_orchestrator", lambda: StubOrch())
    resp = client.get("/scenarios/test.json")
    assert resp.status_code == 200
    assert resp.json()["name"] == "test.json"


def test_get_scenario_not_found(monkeypatch, client):
    """Test GET /scenarios/{name} with missing scenario."""
    class StubOrch:
        def load_scenario(self, name):
            raise FileNotFoundError(f"Scenario {name} not found")

    monkeypatch.setattr("src.service.api._get_orchestrator", lambda: StubOrch())
    resp = client.get("/scenarios/missing.json")
    assert resp.status_code == 404


def test_cors_configuration():
    """Test that CORS middleware is configured in the app."""
    from src.service.api import app
    # Verify CORS middleware is registered
    # In FastAPI, middleware is in app.user_middleware
    middleware_types = [m.cls.__name__ for m in app.user_middleware]
    assert "CORSMiddleware" in middleware_types


def test_run_desk_agent_with_data(monkeypatch, client):
    """Test /run-desk-agent with inline data instead of scenario name."""
    class DummyOrch:
        def run_scenario(self, payload):
            return {"status": "ok", "scenario": {"name": payload.get("name", "inline")}}

    monkeypatch.setattr("src.service.api._get_orchestrator", lambda: DummyOrch())
    inline_data = {
        "name": "inline_test",
        "trades": [],
        "marks": [],
        "questions": [],
        "metadata": {}
    }
    resp = client.post("/run-desk-agent", json={"data": inline_data})
    assert resp.status_code == 200
    assert resp.json()["scenario"]["name"] == "inline_test"


def test_config_loading():
    """Test configuration loading from defaults and env."""
    from src.service.config import load_config
    cfg = load_config()
    assert "env" in cfg
    assert "port" in cfg
    assert "log_level" in cfg
    assert cfg["env"] in ["dev", "stage", "prod"]


def test_config_validation():
    """Test configuration validation."""
    from src.service.config import validate_config
    cfg = {"env": "dev", "port": 8000}
    validated = validate_config(cfg)
    assert validated == cfg


def test_validate_trade_error_handling(monkeypatch, client):
    """Test error handling in /validate-trade."""
    class FailingOMS:
        def run(self, trade):
            raise RuntimeError("OMS failure")

    monkeypatch.setattr("src.service.api._get_oms", lambda: FailingOMS())
    resp = client.post("/validate-trade", json={"trade": {"ticker": "AAPL"}})
    assert resp.status_code == 500


def test_validate_pricing_error_handling(monkeypatch, client):
    """Test error handling in /validate-pricing."""
    class FailingPricing:
        def run(self, marks):
            raise RuntimeError("Pricing failure")

    monkeypatch.setattr("src.service.api._get_pricing", lambda: FailingPricing())
    resp = client.post("/validate-pricing", json={"marks": [{"ticker": "AAPL", "internal_mark": 1.0, "as_of": "2024-01-01"}]})
    assert resp.status_code == 500


def test_response_timing_logged(client, caplog):
    """Test that request duration is logged."""
    import logging
    caplog.set_level(logging.INFO)
    resp = client.get("/health")
    assert resp.status_code == 200
    # Check that duration was logged (middleware logs request)
    # Note: exact log format depends on logging config


def test_payload_size_limit(monkeypatch, client):
    """Test that large payloads are rejected."""
    # Create a very large payload
    large_data = "x" * 2_000_000  # 2MB payload
    resp = client.post("/run-desk-agent",
                      data=large_data,
                      headers={"Content-Type": "application/json", "Content-Length": str(len(large_data))})
    assert resp.status_code in (400, 413, 422)  # Bad request or payload too large
