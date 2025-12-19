import json
from pathlib import Path

import pytest

from src.data_tools.schemas import Trade as DataTrade
from src.oms.oms_agent import OMSAgent
from src.refmaster.schema import RefMasterEquity, NormalizationResult


class DummySnap:
    def __init__(self, price: float) -> None:
        self.price = price
        self.ticker = "TEST"
        self.date = "2024-06-05"
        self.source = "test"


class NormalizerStub:
    def __init__(self, resolver) -> None:
        self._resolver = resolver

    def normalize(self, ticker: str, top_k: int = 3):
        return self._resolver(ticker)


def equity(symbol: str) -> RefMasterEquity:
    return RefMasterEquity(symbol=symbol, isin=f"US{symbol:0<9}0"[:12], cusip=f"{symbol:0<9}", currency="USD", exchange="NYSE", pricing_source="TEST")


def test_status_rules_collect_all(monkeypatch):
    agent = OMSAgent(normalizer=NormalizerStub(lambda t: []))
    monkeypatch.setattr("src.oms.oms_agent.get_price_snapshot", lambda t, d: DummySnap(120))
    res = agent.run({"ticker": "BAD", "quantity": 100, "price": 200, "currency": "USD", "counterparty": "UNKNOWN", "trade_dt": "2024-06-05", "settle_dt": "2024-06-04"})
    error_types = {i["type"] for i in res["issues"] if i["severity"] == "ERROR"}
    warning_types = {i["type"] for i in res["issues"] if i["severity"] == "WARNING"}
    assert res["status"] == "ERROR"
    assert "identifier_mismatch" in error_types
    assert "settlement_date" in error_types
    assert "price_tolerance" in warning_types or "counterparty" in warning_types


def test_schema_validation_surfaces(monkeypatch):
    agent = OMSAgent()
    monkeypatch.setattr("src.oms.oms_agent.get_price_snapshot", lambda t, d: DummySnap(100))
    res = agent.run({"ticker": "AAPL", "quantity": -1, "price": 0, "currency": "US", "counterparty": "MS", "trade_dt": "bad-date", "settle_dt": "2024-06-07"})
    assert res["status"] == "ERROR"
    assert any(i["type"] == "schema_validation" for i in res["issues"])


def test_data_tools_trade_compatibility(monkeypatch):
    agent = OMSAgent(normalizer=NormalizerStub(lambda t: [NormalizationResult(equity=equity(t), confidence=0.99, reasons=[])]))
    monkeypatch.setattr("src.oms.oms_agent.get_price_snapshot", lambda t, d: DummySnap(190))
    trade = DataTrade(ticker="AAPL", quantity=100, price=190, currency="USD", counterparty="MS", trade_dt="2024-06-05", settle_dt="2024-06-07")
    res = agent.run(trade)
    assert res["status"] == "OK"
    assert not res["issues"]


@pytest.mark.parametrize("scenario_file", [Path("tests/oms/scenarios.json")])
def test_scenarios(monkeypatch, scenario_file):
    scenarios = json.loads(scenario_file.read_text())
    assert len(scenarios) >= 10, "production-pressure suite should cover many trades"

    def resolver_for(mode: str):
        def _normalize(ticker: str, top_k: int = 3):
            if mode == "invalid":
                return []
            if mode == "ambiguous":
                return [
                    NormalizationResult(
                        equity=equity(ticker),
                        confidence=0.91,
                        reasons=["symbol_exact"],
                        ambiguous=True,
                    )
                ]
            if mode == "low_confidence":
                return [
                    NormalizationResult(
                        equity=equity(ticker),
                        confidence=0.5,
                        reasons=["symbol_in_text"],
                        ambiguous=False,
                    )
                ]
            return [
                NormalizationResult(
                    equity=equity(ticker),
                    confidence=0.99,
                    reasons=["symbol_exact"],
                    ambiguous=False,
                )
            ]

        return _normalize

    for scenario in scenarios:
        trade = scenario["trade"]
        normalizer_mode = scenario.get("normalizer_mode", "ok")
        market_price = scenario.get("market_price", trade.get("price", 100.0))
        if scenario.get("market_data_unavailable"):
            monkeypatch.setattr(
                "src.oms.oms_agent.get_price_snapshot",
                lambda t, d: (_ for _ in ()).throw(RuntimeError("API down")),
            )
        else:
            monkeypatch.setattr(
                "src.oms.oms_agent.get_price_snapshot",
                lambda t, d, p=market_price: DummySnap(p),
            )
        agent = OMSAgent(
            normalizer=NormalizerStub(resolver_for(normalizer_mode)),
            ref_currency_map={"AAPL": "USD", "MSFT": "USD", "SAP": "EUR"},
        )
        res = agent.run(trade)
        expected_status = scenario["expected_status"]
        expected_issues = scenario["expected_issues"]
        assert (
            res["status"] == expected_status
        ), f"{scenario['name']} expected {expected_status} got {res['status']} ({res['issues']})"
        for expected in expected_issues:
            matches = [
                i
                for i in res["issues"]
                if i["type"] == expected["type"] and i["severity"] == expected["severity"]
            ]
            assert matches, f"{scenario['name']} missing expected issue {expected}"
