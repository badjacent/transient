"""Pydantic schemas for data tooling outputs."""

from typing import Dict, Optional

from pydantic import BaseModel, Field


class PriceSnapshot(BaseModel):
    """Daily pricing snapshot with simple return multipliers."""

    ticker: str
    price: float
    return_1d: float = Field(..., description="Return vs previous trading day as a multiplier.")
    return_5d: float = Field(..., description="Return vs five trading days ago as a multiplier.")
    date: str
    source: str = Field(default="financialdatasets.ai")


class CompanyFacts(BaseModel):
    """Current, non-dated fundamentals for a company."""

    ticker: str
    market_cap: float
    sector: str
    industry: Optional[str] = None
    source: str = Field(default="financialdatasets.ai")


class EquitySnapshot(BaseModel):
    """Combined snapshot of recent price action and high-level fundamentals."""

    ticker: str
    price: float
    return_1d: float = Field(default=1.0, description="Return vs previous trading day as a multiplier.")
    return_5d: float = Field(default=1.0, description="Return vs five trading days ago as a multiplier.")
    market_cap: float
    sector: str
    industry: Optional[str] = None
    date: str
    source: str = Field(default="financialdatasets.ai")


class QAPair(BaseModel):
    """Question/answer tuple generated from filings."""

    question: str
    answer: str
    context: Optional[str] = None


class Equity(BaseModel):
    """Static identifiers/metadata for an equity security."""

    symbol: str
    isin: str
    cusip: str
    cik: str = ""
    currency: str
    exchange: str
    pricing_source: str


class Trade(BaseModel):
    """Trade record for equities, options, and simple credit (bond/CDS)."""

    ticker: str
    quantity: float
    price: float
    currency: str
    counterparty: str
    trade_dt: str = Field(..., description="Trade date in YYYY-MM-DD format")
    settle_dt: str = Field(..., description="Settlement date in YYYY-MM-DD format")


class IncomeStatement(BaseModel):
    """Normalized income statement slice."""

    ticker: str
    period: str
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None
    total_revenue: Optional[float] = None
    cost_of_revenue: Optional[float] = None
    gross_profit: Optional[float] = None
    operating_income: Optional[float] = None
    net_income: Optional[float] = None
    diluted_eps: Optional[float] = None
    currency: Optional[str] = None
    source: str = Field(default="financialdatasets.ai")
    raw: Optional[Dict] = None


class BalanceSheet(BaseModel):
    """Normalized balance sheet slice for assessing financial health and risk."""

    ticker: str
    period: str
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None
    # Assets
    total_assets: Optional[float] = None
    current_assets: Optional[float] = None
    cash_and_cash_equivalents: Optional[float] = None
    # Liabilities
    total_liabilities: Optional[float] = None
    current_liabilities: Optional[float] = None
    total_debt: Optional[float] = None
    long_term_debt: Optional[float] = None
    short_term_debt: Optional[float] = None
    # Equity
    total_equity: Optional[float] = None
    shareholders_equity: Optional[float] = None
    # Calculated risk metrics (can be computed from above)
    current_ratio: Optional[float] = Field(None, description="Current assets / Current liabilities")
    debt_to_equity: Optional[float] = Field(None, description="Total debt / Total equity")
    working_capital: Optional[float] = Field(None, description="Current assets - Current liabilities")
    currency: Optional[str] = None
    source: str = Field(default="financialdatasets.ai")
    raw: Optional[Dict] = None


class CashFlowStatement(BaseModel):
    """Normalized cash flow statement slice for assessing liquidity and cash generation."""

    ticker: str
    period: str
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None
    # Operating activities
    operating_cash_flow: Optional[float] = None
    # Investing activities
    capital_expenditures: Optional[float] = None
    investing_cash_flow: Optional[float] = None
    # Financing activities
    financing_cash_flow: Optional[float] = None
    # Net change
    net_change_in_cash: Optional[float] = None
    free_cash_flow: Optional[float] = Field(None, description="Operating cash flow - Capital expenditures")
    currency: Optional[str] = None
    source: str = Field(default="financialdatasets.ai")
    raw: Optional[Dict] = None
