from src.desk_agent.orchestrator import DeskAgentOrchestrator


class DummyNormalizer:
    def normalize(self, desc, top_k=1):
        return []


class DummyOMS:
    def run(self, trade_json):
        return {"status": "OK", "issues": [], "explanation": "ok", "trade": trade_json}


class DummyPricing:
    def run(self, marks_input):
        return {"enriched_marks": [], "summary": {}}


def test_run_scenario_minimal(monkeypatch):
    # Stub ticker agent and market snapshot to avoid external calls
    monkeypatch.setattr("src.desk_agent.orchestrator.ticker_agent.run", lambda q: {"intent": "generic", "summary": "ok", "metrics": {}})
    monkeypatch.setattr("src.desk_agent.orchestrator.get_equity_snapshot", lambda tkr: type("Snap", (), {"model_dump": lambda self: {"ticker": tkr}})())

    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DummyOMS(),
        pricing_agent=DummyPricing(),
    )
    scenario = {
        "name": "minimal",
        "description": "minimal scenario",
        "trades": [{"ticker": "AAPL", "quantity": 1, "price": 1, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-01-01", "settle_dt": "2024-01-02"}],
        "marks": [{"ticker": "AAPL", "internal_mark": 1.0, "as_of_date": "2024-01-01"}],
        "questions": [{"question": "How is AAPL?"}],
    }
    report = orch.run_scenario(scenario)
    assert report["scenario"]["name"] == "minimal"
    assert "summary" in report
    assert isinstance(report["trade_issues"], list)
    assert isinstance(report["pricing_flags"], list)
