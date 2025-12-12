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
