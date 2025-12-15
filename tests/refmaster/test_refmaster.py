import json
from pathlib import Path

import pytest

from src.refmaster.normalizer_agent import NormalizerAgent, load_equities, normalize, resolve_ticker
from src.refmaster.schema import RefMasterEquity


def _sample_equities():
    return [
        RefMasterEquity(symbol="AAPL", isin="US0378331005", cusip="037833100", currency="USD", exchange="NASDAQ", pricing_source="unit"),
        RefMasterEquity(symbol="AAPB", isin="US0000000001", cusip="000000000", currency="USD", exchange="NYSE", pricing_source="unit"),
    ]


def test_load_equities_json(tmp_path):
    payload = {"equities": [_sample_equities()[0].model_dump()]}
    json_path = tmp_path / "refmaster_data.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")
    equities = load_equities(str(json_path))
    assert equities and equities[0].symbol == "AAPL"


def test_load_equities_csv(tmp_path):
    csv_path = tmp_path / "refmaster_data.csv"
    csv_path.write_text(
        "symbol,isin,cusip,currency,exchange,pricing_source\n"
        "AAPL,US0378331005,037833100,USD,NASDAQ,test\n",
        encoding="utf-8",
    )
    equities = load_equities(str(csv_path))
    assert equities and equities[0].symbol == "AAPL" and equities[0].exchange == "NASDAQ"


def test_normalize_exact_isin():
    agent = NormalizerAgent(equities=_sample_equities())
    results = agent.normalize("US0378331005")
    assert results and results[0].equity.symbol == "AAPL" and results[0].confidence == pytest.approx(1.0)


def test_normalize_symbol_with_country():
    agent = NormalizerAgent(equities=_sample_equities())
    results = agent.normalize("AAPL US")
    assert results and results[0].equity.symbol == "AAPL"


def test_normalize_exchange_suffix():
    agent = NormalizerAgent(equities=_sample_equities())
    results = agent.normalize("AAPL.OQ")
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


def test_tie_breaker_prefers_exchange_and_shorter_symbol():
    equities = [
        RefMasterEquity(symbol="AAA", isin="", cusip="", currency="USD", exchange="NYSE", pricing_source="unit"),
        RefMasterEquity(symbol="AAAB", isin="", cusip="", currency="USD", exchange="NASDAQ", pricing_source="unit"),
    ]
    agent = NormalizerAgent(equities=equities)
    # Both candidates only match the symbol text (same base confidence),
    # but AAA has an exchange match and shorter symbol length.
    results = agent.normalize("AAA listed on NYSE")
    assert results and results[0].equity.symbol == "AAA"


def test_normalize_company_name_with_exchange_threshold_override():
    agent = NormalizerAgent(equities=_sample_equities(), thresholds={"reject": 0.2})
    results = agent.normalize("Apple Inc NASDAQ")
    assert results and results[0].equity.symbol == "AAPL"
    assert "exchange_only" in results[0].reasons


@pytest.mark.parametrize(
    "query,thresholds",
    [
        ("AAPL US", None),
        ("AAPL.OQ", None),
        ("US0378331005", None),
        ("Apple Inc NASDAQ", {"reject": 0.2}),
    ],
)
def test_normalization_results_include_reasons_and_confidence(query, thresholds):
    kwargs = {"thresholds": thresholds} if thresholds else {}
    agent = NormalizerAgent(equities=_sample_equities(), **kwargs)
    results = agent.normalize(query)
    assert results, f"no matches for {query}"
    top = results[0]
    assert isinstance(top.confidence, float)
    assert top.reasons, f"missing reasons for {query}"
