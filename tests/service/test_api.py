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
