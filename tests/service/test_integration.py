import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.service.api import app


@pytest.fixture
def client():
    return TestClient(app)


def _stub_orchestrator(monkeypatch, report, fail_missing: bool = False):
    class StubOrch:
        def run_scenario(self, scenario):
            if fail_missing and "missing" in str(scenario):
                raise FileNotFoundError(scenario)
            return report

        def load_scenario(self, name):
            if "missing" in str(name):
                raise FileNotFoundError(name)
            path = Path(name)
            if path.exists():
                return json.loads(path.read_text())
            return {"name": "inline", "description": "demo", "trades": [], "marks": [], "questions": [], "metadata": {}}

    monkeypatch.setattr("src.service.api._get_orchestrator", lambda: StubOrch())


def test_run_desk_agent_integration(monkeypatch, client, tmp_path):
    scenario_path = tmp_path / "demo.json"
    scenario_path.write_text(json.dumps({"name": "demo", "description": "test", "trades": [], "marks": [], "questions": [], "metadata": {}}))
    report = {"summary": {"overall_status": "OK"}, "scenario": {"name": "demo"}}
    _stub_orchestrator(monkeypatch, report)
    resp = client.post("/run-desk-agent", json={"scenario": str(scenario_path)})
    assert resp.status_code == 200
    assert resp.json()["scenario"]["name"] == "demo"


def test_run_desk_agent_handles_missing(monkeypatch, client):
    _stub_orchestrator(monkeypatch, {"scenario": {"name": "demo"}}, fail_missing=True)
    resp = client.post("/run-desk-agent", json={"scenario": "missing.json"})
    assert resp.status_code in (404, 500)


def test_validate_trade_performance(monkeypatch, client):
    class StubOMS:
        def run(self, trade):
            return {"status": "OK"}

    monkeypatch.setattr("src.service.api._get_oms", lambda: StubOMS())
    payload = {"trade": {"ticker": "AAPL", "quantity": 1, "price": 1, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-01-01", "settle_dt": "2024-01-02"}}
    resp = client.post("/validate-trade", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "OK"


def test_validate_pricing_performance(monkeypatch, client):
    class StubPricing:
        def run(self, marks):
            return {"enriched_marks": marks, "summary": {"counts": {"OK": len(marks)}}}

    monkeypatch.setattr("src.service.api._get_pricing", lambda: StubPricing())
    marks = [{"ticker": "AAPL", "internal_mark": 1.0, "as_of": "2024-01-01"}]
    resp = client.post("/validate-pricing", json={"marks": marks})
    assert resp.status_code == 200
    body = resp.json()
    assert body["summary"]["counts"]["OK"] == 1
