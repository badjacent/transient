import json
from pathlib import Path

from src.pricing.pricing_agent import PricingAgent


def test_pricing_agent_run_with_list(monkeypatch):
    agent = PricingAgent()
    monkeypatch.setattr(agent.normalizer, "enrich_marks", lambda records: [])
    result = agent.run([{"ticker": "AAPL", "internal_mark": 100.0, "as_of_date": "2024-06-05"}])
    assert "enriched_marks" in result
    assert result["summary"]["total_marks"] == 0 or result["summary"]["total_marks"] == len(result["enriched_marks"])


def test_pricing_agent_run_csv(tmp_path, monkeypatch):
    csv_path = tmp_path / "marks.csv"
    csv_path.write_text("ticker,internal_mark,as_of_date\nAAPL,100,2024-06-05\n", encoding="utf-8")
    agent = PricingAgent()
    monkeypatch.setattr(agent.normalizer, "enrich_marks", lambda records: [])
    result = agent.run(str(csv_path))
    assert "enriched_marks" in result


def test_pricing_agent_run_scenario_file(monkeypatch):
    agent = PricingAgent()

    # Stub out enrich_marks to avoid external calls while asserting load succeeds
    def _stub_enrich(records):
        return []

    monkeypatch.setattr(agent.normalizer, "enrich_marks", _stub_enrich)
    # Should process existing src/pricing/marks.csv without errors
    result = agent.run("src/pricing/marks.csv")
    assert "enriched_marks" in result
    assert "summary" in result


def test_generate_report(tmp_path):
    from src.pricing.pricing_agent import generate_report

    payload = {
        "enriched_marks": [
            {
                "ticker": "AAPL",
                "as_of_date": "2024-06-05",
                "classification": "OK",
                "internal_mark": 100,
                "market_price": 100,
                "deviation_percentage": 0,
            }
        ],
        "summary": {"counts": {"OK": 1}, "total_marks": 1, "average_deviation": 0, "max_deviation": 0, "top_tickers": []},
    }
    md = generate_report(payload, output_path=tmp_path / "report.md")
    assert "Pricing Report" in md
    assert (tmp_path / "report.md").exists()


# ===== Comprehensive Test Suite =====


def test_classification_ok(monkeypatch):
    """Test OK classification (deviation within ok_threshold)."""
    agent = PricingAgent()
    monkeypatch.setattr(agent.normalizer, "fetch_market_price",
                       lambda t, d: {"price": 100.0, "date": d})
    result = agent.run([{"ticker": "AAPL", "internal_mark": 101.0, "as_of_date": "2025-12-17"}])
    assert result["enriched_marks"][0]["classification"] == "OK"
    assert "within acceptable tolerance" in result["enriched_marks"][0]["explanation"]


def test_classification_review_needed(monkeypatch):
    """Test REVIEW_NEEDED (ok_threshold < deviation <= review_threshold)."""
    agent = PricingAgent()
    monkeypatch.setattr(agent.normalizer, "fetch_market_price",
                       lambda t, d: {"price": 100.0, "date": d})
    result = agent.run([{"ticker": "AAPL", "internal_mark": 103.5, "as_of_date": "2025-12-17"}])
    assert result["enriched_marks"][0]["classification"] == "REVIEW_NEEDED"
    assert "moderate variance" in result["enriched_marks"][0]["explanation"].lower()


def test_classification_out_of_tolerance(monkeypatch):
    """Test OUT_OF_TOLERANCE (deviation > review_threshold)."""
    agent = PricingAgent()
    monkeypatch.setattr(agent.normalizer, "fetch_market_price",
                       lambda t, d: {"price": 100.0, "date": d})
    result = agent.run([{"ticker": "AAPL", "internal_mark": 108.0, "as_of_date": "2025-12-17"}])
    assert result["enriched_marks"][0]["classification"] == "OUT_OF_TOLERANCE"
    assert "possible causes" in result["enriched_marks"][0]["explanation"].lower()


def test_classification_stale_mark(monkeypatch):
    """Test STALE_MARK (as_of_date exceeds stale_days)."""
    from datetime import datetime, timedelta
    stale_date = (datetime.utcnow().date() - timedelta(days=10)).isoformat()
    agent = PricingAgent()
    monkeypatch.setattr(agent.normalizer, "fetch_market_price",
                       lambda t, d: {"price": 100.0, "date": d})
    result = agent.run([{"ticker": "AAPL", "internal_mark": 100.5, "as_of_date": stale_date}])
    assert result["enriched_marks"][0]["classification"] == "STALE_MARK"
    assert "exceeds" in result["enriched_marks"][0]["explanation"]


def test_classification_no_market_data(monkeypatch):
    """Test NO_MARKET_DATA (fetch fails)."""
    agent = PricingAgent()
    monkeypatch.setattr(agent.normalizer, "fetch_market_price",
                       lambda t, d: {"error": "ticker_not_found"})
    result = agent.run([{"ticker": "BADTICK", "internal_mark": 100.0, "as_of_date": "2025-12-17"}])
    assert result["enriched_marks"][0]["classification"] == "NO_MARKET_DATA"
    assert "unable to fetch" in result["enriched_marks"][0]["explanation"].lower()


def test_per_instrument_override(monkeypatch):
    """Test that per-instrument tolerance overrides are applied."""
    from src.pricing.normalizer import MarketNormalizer

    tolerances = {
        "ok_threshold": 0.02,
        "review_threshold": 0.05,
        "stale_days": 5,
        "instrument_overrides": {
            "TSLA": {"ok_threshold": 0.05, "review_threshold": 0.10}
        }
    }
    norm = MarketNormalizer(tolerances=tolerances)

    # TSLA with 4% deviation → should be OK (due to override)
    result = norm.compare_mark_to_market(104.0, 100.0, "TSLA")
    assert result["classification"] == "OK"

    # AAPL with 4% deviation → should be REVIEW_NEEDED (global threshold)
    result = norm.compare_mark_to_market(104.0, 100.0, "AAPL")
    assert result["classification"] == "REVIEW_NEEDED"


def test_summary_statistics(monkeypatch):
    """Test that summary includes all required statistics."""
    agent = PricingAgent()
    monkeypatch.setattr(agent.normalizer, "fetch_market_price",
                       lambda t, d: {"price": 100.0, "date": d})

    marks = [
        {"ticker": "AAPL", "internal_mark": 101.0, "as_of_date": "2025-12-17"},  # OK
        {"ticker": "MSFT", "internal_mark": 103.0, "as_of_date": "2025-12-17"},  # REVIEW
        {"ticker": "GOOGL", "internal_mark": 108.0, "as_of_date": "2025-12-17"}, # OUT_OF_TOL
    ]

    result = agent.run(marks)
    summary = result["summary"]

    assert "flagged_count" in summary
    assert "critical_count" in summary
    assert "data_quality_issues" in summary
    assert summary["flagged_count"] == 2  # REVIEW + OUT_OF_TOLERANCE
    assert summary["critical_count"] == 1  # OUT_OF_TOLERANCE only


def test_performance_budget(monkeypatch):
    """Test that processing completes within budget."""
    agent = PricingAgent()
    monkeypatch.setattr(agent.normalizer, "fetch_market_price",
                       lambda t, d: {"price": 100.0, "date": d})

    marks = [
        {"ticker": f"TICK{i}", "internal_mark": 100.0, "as_of_date": "2025-12-17"}
        for i in range(50)
    ]

    result = agent.run(marks)
    assert result["summary"]["within_budget"] is True
    assert result["summary"]["duration_ms"] < 30000


def test_explanation_text_quality():
    """Test that explanations include actionable guidance."""
    from src.pricing.pricing_agent import PricingAgent
    from src.pricing.schema import EnrichedMark

    agent = PricingAgent()

    # Create mock enriched mark
    mark = EnrichedMark(
        ticker="AAPL",
        internal_mark=110.0,
        as_of_date="2025-12-17",
        market_price=100.0,
        deviation_absolute=10.0,
        deviation_percentage=0.10,
        classification="OUT_OF_TOLERANCE"
    )
    explanation = agent._explain(mark)
    assert "possible causes" in explanation.lower()
    assert "action:" in explanation.lower()
    assert len(explanation) > 100  # Ensure detailed explanation


def test_tolerance_loading_with_overrides():
    """Test that per-instrument overrides are loaded correctly."""
    from src.pricing.config import load_tolerances

    config = load_tolerances("config/tolerances.yaml")
    assert "instrument_overrides" in config
    assert "TSLA" in config["instrument_overrides"]
    assert config["instrument_overrides"]["TSLA"]["ok_threshold"] == 0.05
    assert config["instrument_overrides"]["TSLA"]["review_threshold"] == 0.10


def test_metadata_attachment(monkeypatch):
    """Test that metadata fields are attached to enriched marks."""
    agent = PricingAgent()
    monkeypatch.setattr(agent.normalizer, "fetch_market_price",
                       lambda t, d: {"price": 100.0, "date": d})

    result = agent.run([{"ticker": "AAPL", "internal_mark": 101.0, "as_of_date": "2025-12-17"}])
    mark = result["enriched_marks"][0]

    assert "market_data_source" in mark
    assert mark["market_data_source"] == "financialdatasets.ai"
    assert "fetch_timestamp" in mark
    assert "tolerance_override_applied" in mark
    assert isinstance(mark["tolerance_override_applied"], bool)
