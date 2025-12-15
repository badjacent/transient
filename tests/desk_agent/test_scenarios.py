import json
from pathlib import Path

from src.desk_agent.orchestrator import DeskAgentOrchestrator


class NormalizerStub:
    def normalize(self, desc, top_k=1):
        class Res:
            def __init__(self, sym):
                self.equity = type("Eq", (), {"symbol": sym})
                self.confidence = 0.99
                self.ambiguous = False
        return [Res(desc)]


class OMSStub:
    def run(self, trade_json):
        return {"status": "OK", "issues": [], "explanation": "ok", "trade": trade_json}


class PricingStub:
    def run(self, marks):
        enriched = []
        for m in marks:
            enriched.append(
                {
                    **m,
                    "market_price": m.get("internal_mark"),
                    "classification": "OK",
                    "deviation_percentage": 0.0,
                    "explanation": "OK",
                }
            )
        return {"enriched_marks": enriched, "summary": {"counts": {"OK": len(enriched)}}}


def test_validate_all_scenarios(monkeypatch):
    monkeypatch.setattr(
        "src.desk_agent.orchestrator.get_equity_snapshot",
        lambda tkr: type("Snap", (), {"model_dump": lambda self: {"ticker": tkr, "return_1d": 1.0, "return_5d": 1.0, "sector": "TECH", "market_cap": 1.0}})(),
    )
    orch = DeskAgentOrchestrator(
        normalizer=NormalizerStub(),
        oms_agent=OMSStub(),
        pricing_agent=PricingStub(),
        ticker_runner=lambda q: {"question": q, "intent": "generic", "summary": "ok", "metrics": {}},
    )
    errors = orch.validate_all_scenarios()
    assert errors == {}


def test_run_all_scenarios(monkeypatch):
    monkeypatch.setattr(
        "src.desk_agent.orchestrator.get_equity_snapshot",
        lambda tkr: type("Snap", (), {"model_dump": lambda self: {"ticker": tkr, "return_1d": 1.0, "return_5d": 1.0, "sector": "TECH", "market_cap": 1.0}})(),
    )
    orch = DeskAgentOrchestrator(
        normalizer=NormalizerStub(),
        oms_agent=OMSStub(),
        pricing_agent=PricingStub(),
        ticker_runner=lambda q: {"question": q, "intent": "generic", "summary": "ok", "metrics": {}},
    )
    scenarios_dir = Path("scenarios")
    for path in scenarios_dir.glob("*.json"):
        scenario = json.loads(path.read_text())
        report = orch.run_scenario(scenario)
        assert "summary" in report
        assert "trade_issues" in report
        assert "pricing_flags" in report
        assert report["scenario"]["name"] == scenario["name"]
