import pytest

from src.desk_agent import ticker_agent
from src.data_tools.schemas import EquitySnapshot


@pytest.fixture
def sample_snapshot():
    return EquitySnapshot(
        ticker="TEST",
        price=100.0,
        return_1d=1.02,
        return_5d=1.05,
        market_cap=1_000_000_000,
        sector="Tech",
        industry="Software",
        date="2025-01-10",
        source="financialdatasets.ai",
    )


def test_run_fundamentals(monkeypatch, sample_snapshot):
    monkeypatch.setattr(ticker_agent, "get_equity_snapshot", lambda ticker: sample_snapshot)
    result = ticker_agent.run("What is the market cap for TEST?")
    assert result["intent"] == "financials_revenue_summary"
    assert "market cap" in result["summary"].lower()
    assert "market_cap" in result["metrics"]
    assert result["metrics"]["ticker"] == "TEST"


def test_run_performance(monkeypatch, sample_snapshot):
    monkeypatch.setattr(ticker_agent, "get_equity_snapshot", lambda ticker: sample_snapshot)
    result = ticker_agent.run("How has TEST performed YTD?")
    assert result["intent"] == "price_performance_summary"
    assert "1d" in result["summary"].lower()
    assert "return_1d" in result["metrics"]


def test_run_error_invalid_ticker():
    result = ticker_agent.run("anything")
    assert result["error"] == "invalid_ticker"


def test_run_error_data_unavailable(monkeypatch):
    def _raise(_):
        raise RuntimeError("boom")
    monkeypatch.setattr(ticker_agent, "get_equity_snapshot", _raise)
    result = ticker_agent.run("market cap for TEST?")
    assert result["error"] == "data_unavailable"
    assert "boom" in result["summary"]
