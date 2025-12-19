"""Schemas for pricing marks and enriched results."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, validator


class Mark(BaseModel):
    """Internal end-of-day pricing mark."""

    ticker: str
    internal_mark: float
    as_of_date: str = Field(..., description="YYYY-MM-DD")
    notes: Optional[str] = None
    source: Optional[str] = None
    position_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    instrument_type: Optional[str] = None
    currency: Optional[str] = None

    @validator("ticker", pre=True, always=True)
    def _upper(cls, v: str) -> str:
        return v.strip().upper() if isinstance(v, str) else v

    @validator("as_of_date")
    def _validate_date(cls, v: str) -> str:
        try:
            date.fromisoformat(v)
        except Exception as exc:
            raise ValueError(f"Invalid as_of_date format (YYYY-MM-DD expected): {v}") from exc
        return v


class EnrichedMark(Mark):
    """Mark augmented with market comparison."""

    market_price: Optional[float] = None
    deviation_absolute: Optional[float] = None
    deviation_percentage: Optional[float] = None
    classification: str
    market_data_date: Optional[str] = None
    market_data_source: Optional[str] = None
    fetch_timestamp: Optional[str] = None
    tolerance_override_applied: Optional[bool] = None
    error: Optional[str] = None
    explanation: Optional[str] = None


class PricingSummary(BaseModel):
    """Aggregate summary for a set of marks."""

    counts: dict
    total_marks: int
    average_deviation: Optional[float] = None
    max_deviation: Optional[float] = None
    top_tickers: list[str] = Field(default_factory=list)
