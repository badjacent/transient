"""Market normalization utilities for pricing marks."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.data_tools.fd_api import get_price_snapshot
from src.pricing.config import load_tolerances
from src.pricing.schema import EnrichedMark, Mark


class MarketNormalizer:
    """Compare internal marks to market prices with configurable thresholds."""

    def __init__(self, tolerances: Optional[Dict[str, Any]] = None):
        self.tolerances = load_tolerances()
        if tolerances:
            self.tolerances.update(tolerances)

    def fetch_market_price(self, ticker: str, as_of_date: str) -> Dict[str, Any]:
        """Fetch market price; return dict with price/date or error."""
        try:
            dt = date.fromisoformat(as_of_date)
        except Exception as exc:
            return {"error": f"invalid_date: {exc}"}
        try:
            snap = get_price_snapshot(ticker, dt)
            return {"price": snap.price, "date": snap.date}
        except Exception as exc:
            return {"error": str(exc)}

    def compare_mark_to_market(self, internal_mark: float, market_price: Optional[float]) -> Dict[str, Any]:
        """Compute deviation and classification given tolerances."""
        if market_price is None:
            return {
                "market_price": None,
                "deviation_absolute": None,
                "deviation_percentage": None,
                "classification": "NO_MARKET_DATA",
            }
        deviation_abs = internal_mark - market_price
        deviation_pct = abs(deviation_abs) / market_price if market_price else None
        cls = "OK"
        ok_th = self.tolerances["ok_threshold"]
        review_th = self.tolerances["review_threshold"]
        if deviation_pct is None:
            cls = "NO_MARKET_DATA"
        elif deviation_pct > review_th:
            cls = "OUT_OF_TOLERANCE"
        elif deviation_pct > ok_th:
            cls = "REVIEW_NEEDED"
        return {
            "market_price": market_price,
            "deviation_absolute": deviation_abs,
            "deviation_percentage": deviation_pct,
            "classification": cls,
        }

    def _is_stale(self, as_of_date: str) -> bool:
        try:
            dt = date.fromisoformat(as_of_date)
        except Exception:
            return False
        age_days = (datetime.utcnow().date() - dt).days
        return age_days > self.tolerances["stale_days"]

    def enrich_marks(self, marks_input) -> List[EnrichedMark]:
        """Enrich a list/DataFrame of marks with market data and classifications."""
        marks: List[Mark] = []
        if hasattr(marks_input, "to_dict"):  # pandas DataFrame
            records = marks_input.to_dict(orient="records")
        elif isinstance(marks_input, list):
            records = marks_input
        else:
            raise ValueError("marks_input must be a list of dicts or DataFrame")

        for record in records:
            mark = Mark(**record)
            result = self.fetch_market_price(mark.ticker, mark.as_of_date)
            market_price = result.get("price")
            enriched_fields = self.compare_mark_to_market(mark.internal_mark, market_price)
            enriched_fields["market_data_date"] = result.get("date")
            if self._is_stale(mark.as_of_date) and enriched_fields["classification"] != "NO_MARKET_DATA":
                enriched_fields["classification"] = "STALE_MARK"
            if result.get("error"):
                enriched_fields["error"] = result["error"]
                enriched_fields["classification"] = "NO_MARKET_DATA"
            enriched = EnrichedMark(**mark.model_dump(), **enriched_fields)
            marks.append(enriched)
        return marks
