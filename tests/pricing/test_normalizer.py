import pytest
from datetime import date

from src.pricing.normalizer import MarketNormalizer
from src.pricing.schema import Mark


def test_compare_mark_classification():
    norm = MarketNormalizer(tolerances={"ok_threshold": 0.02, "review_threshold": 0.05})
    res = norm.compare_mark_to_market(102, 100)
    assert res["classification"] == "REVIEW_NEEDED"
    res2 = norm.compare_mark_to_market(110, 100)
    assert res2["classification"] == "OUT_OF_TOLERANCE"
    res3 = norm.compare_mark_to_market(101, 100)
    assert res3["classification"] == "OK"


def test_enrich_marks_missing_market(monkeypatch):
    norm = MarketNormalizer()
    monkeypatch.setattr(norm, "fetch_market_price", lambda t, d: {"error": "no data"})
    marks = [{"ticker": "AAPL", "internal_mark": 100.0, "as_of_date": "2024-06-05"}]
    enriched = norm.enrich_marks(marks)
    assert enriched[0].classification == "NO_MARKET_DATA"
    assert enriched[0].error


def test_enrich_marks_with_price(monkeypatch):
    norm = MarketNormalizer(tolerances={"ok_threshold": 0.02, "review_threshold": 0.05})
    monkeypatch.setattr(norm, "fetch_market_price", lambda t, d: {"price": 100.0, "date": d})
    marks = [{"ticker": "AAPL", "internal_mark": 105.0, "as_of_date": "2024-06-05"}]
    enriched = norm.enrich_marks(marks)
    assert enriched[0].classification == "OUT_OF_TOLERANCE"
    assert enriched[0].market_price == 100.0
