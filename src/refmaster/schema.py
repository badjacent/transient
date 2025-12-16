"""Schemas for reference master entities and normalization results."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class RefMasterEquity(BaseModel):
    """Static identifiers/metadata for an equity security."""

    symbol: str
    isin: str
    cusip: str
    currency: str
    exchange: str
    pricing_source: str
    cik: str = ""
    name: Optional[str] = None
    country: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None

    @field_validator("symbol", "currency", "exchange", mode="before")
    @classmethod
    def _upper_trim(cls, v: str) -> str:
        return v.strip().upper() if isinstance(v, str) else v


class NormalizationResult(BaseModel):
    """Ranked normalization outcome."""

    equity: RefMasterEquity
    confidence: float = Field(ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)
    ambiguous: bool = False
