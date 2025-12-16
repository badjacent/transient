"""Schemas for OMS trade validation."""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Trade(BaseModel):
    """Equity trade record."""

    ticker: str
    quantity: float
    price: float
    currency: str
    counterparty: str
    trade_dt: str = Field(..., description="YYYY-MM-DD")
    settle_dt: str = Field(..., description="YYYY-MM-DD")

    @field_validator("ticker", "currency", mode="before")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.strip().upper() if isinstance(v, str) else v

    @field_validator("quantity", "price")
    @classmethod
    def _positive(cls, v: float) -> float:
        if v is None or v <= 0:
            raise ValueError("must be positive")
        return v

    @field_validator("currency")
    @classmethod
    def _currency_format(cls, v: str) -> str:
        if not v or len(v) != 3:
            raise ValueError("currency must be 3-letter ISO")
        return v

    @staticmethod
    def _parse_date(val: str) -> date:
        try:
            return date.fromisoformat(val)
        except Exception as exc:
            raise ValueError(f"invalid date {val}") from exc

    @field_validator("trade_dt", "settle_dt")
    @classmethod
    def _validate_dates(cls, v: str) -> str:
        cls._parse_date(v)
        return v

    def settle_not_before_trade(self) -> bool:
        return self._parse_date(self.settle_dt) >= self._parse_date(self.trade_dt)
