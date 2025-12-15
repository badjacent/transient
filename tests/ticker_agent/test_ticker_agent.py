import pytest

from src.ticker_agent import ticker_agent
from src.data_tools.schemas import (
    BalanceSheet,
    CashFlowStatement,
    EquitySnapshot,
    IncomeStatement,
)


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


@pytest.fixture
def sample_nvda_snapshot():
    return EquitySnapshot(
        ticker="NVDA",
        price=450.0,
        return_1d=1.01,
        return_5d=1.04,
        market_cap=2_000_000_000_000,
        sector="Tech",
        industry="Semiconductors",
        date="2025-02-01",
        source="financialdatasets.ai",
    )


def test_run_fundamentals(monkeypatch, sample_snapshot):
    monkeypatch.setattr(ticker_agent, "_cached_snapshot", lambda ticker: sample_snapshot)
    result = ticker_agent.run("What is the market cap for TEST?")
    assert result["intent"] == "financials_revenue_summary"
    assert "market cap" in result["summary"].lower()
    assert "market_cap" in result["metrics"]
    assert result["metrics"]["ticker"] == "TEST"


def test_run_performance(monkeypatch, sample_snapshot):
    monkeypatch.setattr(ticker_agent, "_cached_snapshot", lambda ticker: sample_snapshot)
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
    monkeypatch.setattr(ticker_agent, "_cached_snapshot", _raise)
    result = ticker_agent.run("market cap for TEST?")
    assert result["error"] == "data_unavailable"
    assert "boom" in result["summary"]


def test_run_income_statement_intent(monkeypatch, sample_snapshot):
    statements = (
        IncomeStatement(ticker="TEST", period="annual", fiscal_year=2024, total_revenue=1500.0, currency="USD"),
        IncomeStatement(ticker="TEST", period="annual", fiscal_year=2023, total_revenue=1200.0, currency="USD"),
    )

    monkeypatch.setattr(ticker_agent, "_cached_snapshot", lambda ticker: sample_snapshot)
    monkeypatch.setattr(ticker_agent, "_cached_income_statements", lambda ticker: statements)

    result = ticker_agent.run("Summarize the last 4 years of revenue for TEST.")

    assert result["intent"] == "income_statement_summary"
    assert "income_statements" in result["metrics"]
    assert len(result["metrics"]["income_statements"]) == 2
    assert "revenue history" in result["summary"].lower()


def test_run_income_statement_question_for_nvda(monkeypatch, sample_nvda_snapshot):
    statements = (
        IncomeStatement(ticker="NVDA", period="annual", fiscal_year=2024, total_revenue=60000.0, currency="USD"),
        IncomeStatement(ticker="NVDA", period="annual", fiscal_year=2023, total_revenue=50000.0, currency="USD"),
        IncomeStatement(ticker="NVDA", period="annual", fiscal_year=2022, total_revenue=47000.0, currency="USD"),
        IncomeStatement(ticker="NVDA", period="annual", fiscal_year=2021, total_revenue=40000.0, currency="USD"),
    )

    def mock_snapshot(ticker):
        assert ticker == "NVDA"
        return sample_nvda_snapshot

    def mock_income_statements(ticker):
        assert ticker == "NVDA"
        return statements

    monkeypatch.setattr(ticker_agent, "_cached_snapshot", mock_snapshot)
    monkeypatch.setattr(ticker_agent, "_cached_income_statements", mock_income_statements)

    result = ticker_agent.run("Summarize the last 4 years of revenue for NVDA.")

    assert result["intent"] == "income_statement_summary"
    assert result["metrics"]["ticker"] == "NVDA"
    assert len(result["metrics"]["income_statements"]) == 4
    assert "2024" in result["summary"]


def test_run_fundamentals_risk_summary(monkeypatch, sample_snapshot):
    income_statements = [
        IncomeStatement(
            ticker="TEST",
            period="annual",
            fiscal_year=2024,
            total_revenue=1500.0,
            operating_income=300.0,
            net_income=200.0,
            currency="USD",
        ),
        IncomeStatement(
            ticker="TEST",
            period="annual",
            fiscal_year=2023,
            total_revenue=1200.0,
            operating_income=240.0,
            net_income=150.0,
            currency="USD",
        ),
    ]
    balance_sheets = [
        BalanceSheet(
            ticker="TEST",
            period="annual",
            fiscal_year=2024,
            current_ratio=1.6,
            debt_to_equity=0.4,
            cash_and_cash_equivalents=500.0,
        ),
        BalanceSheet(
            ticker="TEST",
            period="annual",
            fiscal_year=2023,
            current_ratio=1.2,
            debt_to_equity=0.6,
        ),
    ]
    cash_flows = [
        CashFlowStatement(
            ticker="TEST",
            period="annual",
            fiscal_year=2024,
            free_cash_flow=250.0,
            currency="USD",
        ),
        CashFlowStatement(
            ticker="TEST",
            period="annual",
            fiscal_year=2023,
            free_cash_flow=200.0,
            currency="USD",
        ),
    ]

    monkeypatch.setattr(ticker_agent, "_cached_snapshot", lambda ticker: sample_snapshot)
    monkeypatch.setattr(ticker_agent, "_cached_income_statements", lambda ticker: tuple(income_statements))
    monkeypatch.setattr(ticker_agent, "_cached_balance_sheets", lambda ticker: tuple(balance_sheets))
    monkeypatch.setattr(ticker_agent, "_cached_cash_flow_statements", lambda ticker: tuple(cash_flows))

    result = ticker_agent.run("Provide a fundamentals risk trend for TEST.")

    assert result["intent"] == "fundamentals_risk_summary"
    metrics = result["metrics"]
    assert metrics["income_statements"]
    assert metrics["balance_sheets"]
    assert metrics["cash_flow_statements"]
    assert "Fundamentals & Risk Analysis" in result["summary"]
    assert "Risk Assessment" in result["summary"]


def test_run_dividend_intent(monkeypatch, sample_snapshot):
    monkeypatch.setattr(ticker_agent, "_cached_snapshot", lambda ticker: sample_snapshot)
    result = ticker_agent.run("What is the dividend policy for TEST?")
    assert result["intent"] == "dividend_overview"
    assert "dividend details unavailable" in result["summary"]
    assert "dividend_yield" in result["metrics"]


def test_run_volatility_intent(monkeypatch, sample_snapshot):
    monkeypatch.setattr(ticker_agent, "_cached_snapshot", lambda ticker: sample_snapshot)
    result = ticker_agent.run("Compare vol for TEST vs peers.")
    assert result["intent"] == "volatility_comparison_convertible"
    assert "return_5d" in result["metrics"]
    assert "5D return" in result["summary"] or "5d" in result["summary"].lower()


def test_run_news_intent(monkeypatch, sample_snapshot):
    monkeypatch.setattr(ticker_agent, "_cached_snapshot", lambda ticker: sample_snapshot)
    result = ticker_agent.run("Any news headlines on TEST sentiment?")
    assert result["intent"] == "news_sentiment_stub"
    assert "news sentiment" in result["summary"].lower()
    assert result["metrics"]["sentiment"] is None
