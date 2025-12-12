"""Pydantic schemas for data tooling outputs."""

from typing import Optional

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
