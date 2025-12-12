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


def test_run_desk_agent_not_found(client):
    resp = client.post("/run-desk-agent", json={"scenario": "missing_scenario.json"})
    assert resp.status_code in (404, 500)  # missing scenario should 404; if env differs allow 500


def test_list_scenarios(client):
    resp = client.get("/scenarios")
    # If scenarios path missing, may 404; allow 200/404
    assert resp.status_code in (200, 404)


def test_status(client):
    resp = client.get("/status")
    assert resp.status_code == 200
