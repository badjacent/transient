import pytest
from datetime import date

from src.pricing.normalizer import MarketNormalizer
from src.pricing.schema import Mark


def test_compare_mark_classification():
    norm = MarketNormalizer(tolerances={"ok_threshold": 0.02, "review_threshold": 0.05})
    # 103 vs 100 = 3% deviation, should be REVIEW_NEEDED (> 2%, < 5%)
    res = norm.compare_mark_to_market(103, 100, "AAPL")
    assert res["classification"] == "REVIEW_NEEDED"
    # 110 vs 100 = 10% deviation, should be OUT_OF_TOLERANCE (> 5%)
    res2 = norm.compare_mark_to_market(110, 100, "AAPL")
    assert res2["classification"] == "OUT_OF_TOLERANCE"
    # 101 vs 100 = 1% deviation, should be OK (< 2%)
    res3 = norm.compare_mark_to_market(101, 100, "AAPL")
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
    # Use recent date to avoid STALE_MARK classification
    # Use 106.0 vs 100.0 = 6% deviation, which is > 5% threshold for OUT_OF_TOLERANCE
    marks = [{"ticker": "AAPL", "internal_mark": 106.0, "as_of_date": "2025-12-18"}]
    enriched = norm.enrich_marks(marks)
    assert enriched[0].classification == "OUT_OF_TOLERANCE"
    assert enriched[0].market_price == 100.0
