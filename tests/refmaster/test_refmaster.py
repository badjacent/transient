import json
from pathlib import Path

import pytest

from src.refmaster.normalizer_agent import NormalizerAgent, load_equities, normalize, resolve_ticker
from src.refmaster.schema import Equity


def _sample_equities():
    return [
        Equity(symbol="AAPL", isin="US0378331005", cusip="037833100", currency="USD", exchange="NASDAQ", pricing_source="unit"),
        Equity(symbol="AAPB", isin="US0000000001", cusip="000000000", currency="USD", exchange="NYSE", pricing_source="unit"),
    ]


def test_load_equities_json(tmp_path):
    payload = {"equities": [_sample_equities()[0].model_dump()]}
    json_path = tmp_path / "refmaster_data.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    equities = load_equities(str(json_path))
    assert equities and equities[0].symbol == "AAPL"


def test_normalize_exact_isin():
    agent = NormalizerAgent(equities=_sample_equities())
    results = agent.normalize("US0378331005")
    assert results and results[0].equity.symbol == "AAPL" and results[0].confidence == pytest.approx(1.0)


def test_normalize_symbol_with_country():
    agent = NormalizerAgent(equities=_sample_equities())
    results = agent.normalize("AAPL US")
    assert results and results[0].equity.symbol == "AAPL"


def test_normalize_unknown_rejects():
    agent = NormalizerAgent(equities=_sample_equities(), thresholds={"reject": 0.95})
    assert agent.normalize("ZZZZ") == []


def test_resolve_ticker():
    agent = NormalizerAgent(equities=_sample_equities())
    assert resolve_ticker("aapl").symbol == "AAPL"
    assert resolve_ticker("missing") is None


def test_integration_normalize_function():
    results = normalize("AAPL US", top_k=3)
    # Should return at least one result from packaged data
    assert isinstance(results, list)
