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
    monkeypatch.setattr("src.desk_agent.orchestrator.ticker_agent.run", lambda q: {"intent": "generic", "summary": "ok", "metrics": {}, "question": q})
    monkeypatch.setattr("src.desk_agent.orchestrator.get_equity_snapshot", lambda tkr: type("Snap", (), {"model_dump": lambda self: {"ticker": tkr, "return_1d": 1.0, "return_5d": 1.0, "sector": "TECH", "market_cap": 1.0}})())

    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DummyOMS(),
        pricing_agent=DummyPricing(),
    )
    scenario = {
        "name": "minimal",
        "description": "minimal scenario",
        "trades": [{"trade_id": "T1", "ticker": "AAPL", "quantity": 1, "price": 1, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-01-01", "settle_dt": "2024-01-02"}],
        "marks": [{"ticker": "AAPL", "internal_mark": 1.0, "as_of": "2024-01-01"}],
        "questions": [{"question": "How is AAPL?"}],
        "metadata": {},
    }
    report = orch.run_scenario(scenario)
    assert report["scenario"]["name"] == "minimal"
    assert "summary" in report
    assert isinstance(report["trade_issues"], list)
    assert isinstance(report["pricing_flags"], list)
    assert report["market_context"]["market_movements"]["avg_return_1d"] == 1.0


def test_scenario_validation_errors():
    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DummyOMS(),
        pricing_agent=DummyPricing(),
    )
    scenario = {"description": "missing name", "trades": [], "marks": [], "questions": [], "metadata": {}}
    errs = orch._validate_scenario(scenario)
    assert errs


def test_report_structure_with_failed_step(monkeypatch):
    class FailingPricing(DummyPricing):
        def run(self, marks_input):
            raise RuntimeError("pricing boom")

    monkeypatch.setattr("src.desk_agent.orchestrator.ticker_agent.run", lambda q: {"intent": "generic", "summary": "ok", "metrics": {}, "question": q})
    monkeypatch.setattr("src.desk_agent.orchestrator.get_equity_snapshot", lambda tkr: type("Snap", (), {"model_dump": lambda self: {"ticker": tkr, "return_1d": 1.0, "return_5d": 1.0, "sector": "TECH", "market_cap": 1.0}})())
    orch = DeskAgentOrchestrator(
        normalizer=DummyNormalizer(),
        oms_agent=DummyOMS(),
        pricing_agent=FailingPricing(),
    )
    scenario = {
        "name": "pricing_fail",
        "description": "pricing step fails but report returns",
        "trades": [{"trade_id": "T1", "ticker": "AAPL", "quantity": 1, "price": 1, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-01-01", "settle_dt": "2024-01-02"}],
        "marks": [{"ticker": "AAPL", "internal_mark": 1.0, "as_of": "2024-01-01"}],
        "questions": [],
        "metadata": {},
    }
    report = orch.run_scenario(scenario)
    assert report["scenario"]["name"] == "pricing_fail"
    assert "errors" in report["execution_metadata"]
    assert report["execution_metadata"]["errors"], "expected errors captured in execution_metadata"
