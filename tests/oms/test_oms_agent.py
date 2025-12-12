import json

import pytest

from src.oms.oms_agent import OMSAgent
from src.oms.schema import Trade


def test_parse_and_missing_fields():
    agent = OMSAgent()
    res = agent.run({"ticker": "", "quantity": 100, "price": 10, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-06-05", "settle_dt": "2024-06-07"})
    assert any(i["type"] == "missing_field" for i in res["issues"])


def test_identifier_error(monkeypatch):
    agent = OMSAgent()
    monkeypatch.setattr(agent.normalizer, "normalize", lambda t, top_k=3: [])
    res = agent.run({"ticker": "ZZZZ", "quantity": 100, "price": 10, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-06-05", "settle_dt": "2024-06-07"})
    assert res["status"] == "ERROR"
    assert any(i["type"] == "identifier_mismatch" for i in res["issues"])


def test_price_tolerance(monkeypatch):
    agent = OMSAgent(thresholds={"warning": 0.02, "error": 0.05})

    class DummySnap:
        def __init__(self, price):
            self.price = price
            self.ticker = "AAPL"
            self.date = "2024-06-05"
            self.source = "test"

    monkeypatch.setattr("src.oms.oms_agent.get_price_snapshot", lambda t, d: DummySnap(100))
    res = agent.run({"ticker": "AAPL", "quantity": 100, "price": 120, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-06-05", "settle_dt": "2024-06-07"})
    assert any(i["type"] == "price_tolerance" for i in res["issues"])


def test_counterparty_warning():
    agent = OMSAgent(valid_counterparties={"OK"})
    res = agent.run({"ticker": "AAPL", "quantity": 100, "price": 100, "currency": "USD", "counterparty": "BAD", "trade_dt": "2024-06-05", "settle_dt": "2024-06-07"})
    assert any(i["type"] == "counterparty" for i in res["issues"])


def test_settlement_before_trade():
    agent = OMSAgent()
    res = agent.run({"ticker": "AAPL", "quantity": 100, "price": 100, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-06-05", "settle_dt": "2024-06-04"})
    assert any(i["type"] == "settlement_date" for i in res["issues"])


def test_json_input():
    agent = OMSAgent()
    payload = json.dumps({"ticker": "AAPL", "quantity": 100, "price": 100, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-06-05", "settle_dt": "2024-06-07"})
    res = agent.run(payload)
    assert res["status"] in {"OK", "WARNING", "ERROR"}
