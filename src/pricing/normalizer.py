"""Market normalization utilities for pricing marks."""

from __future__ import annotations

from datetime import date, datetime
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from src.data_tools.fd_api import get_price_snapshot
from src.refmaster import NormalizerAgent, normalize as ref_normalize
from src.pricing.config import load_tolerances
from src.pricing.schema import EnrichedMark, Mark

logger = logging.getLogger(__name__)


class MarketNormalizer:
    """Compare internal marks to market prices with configurable thresholds."""

    def __init__(self, tolerances: Optional[Dict[str, Any]] = None, refmaster: NormalizerAgent | None = None):
        self.tolerances = load_tolerances()
        if tolerances:
            self.tolerances.update(tolerances)
        self._cache: Dict[tuple[str, str], Dict[str, Any]] = {}
        self.refmaster = refmaster
        self.max_workers = int(self.tolerances.get("max_workers", 1))

    def fetch_market_price(self, ticker: str, as_of_date: str) -> Dict[str, Any]:
        """Fetch market price; return dict with price/date or error."""
        cache_key = (ticker.upper(), as_of_date)
        if cache_key in self._cache:
            return self._cache[cache_key]
        try:
            dt = date.fromisoformat(as_of_date)
        except Exception as exc:
            return {"error": f"invalid_date: {exc}"}
        retries = int(self.tolerances.get("retry_count", 0))
        backoff_ms = int(self.tolerances.get("retry_backoff_ms", 0))
        attempt = 0
        while True:
            try:
                snap = get_price_snapshot(ticker, dt)
                result = {"price": snap.price, "date": snap.date}
                self._cache[cache_key] = result
                return result
            except Exception as exc:
                if attempt >= retries:
                    return {"error": str(exc)}
                attempt += 1
                time.sleep(backoff_ms / 1000.0 if backoff_ms else 0)

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
        logger.info(
            "compare mark=%s market=%s deviation_pct=%s classification=%s",
            internal_mark,
            market_price,
            f"{deviation_pct:.4f}" if deviation_pct is not None else None,
            cls,
        )
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

        total = len(records)
        logger.info("enrich_marks starting count=%d", total)
        if self.max_workers > 1:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                for enriched in executor.map(self._enrich_one, records):
                    marks.append(enriched)
        else:
            for record in records:
                marks.append(self._enrich_one(record))
        logger.info("enrich_marks completed count=%d", total)
        return marks

    def _enrich_one(self, record: Dict[str, Any]) -> EnrichedMark:
        mark = Mark(**record)
        # Optional refmaster validation
        if self.refmaster:
            try:
                rm = self.refmaster.normalize(mark.ticker, top_k=1)
            except Exception as exc:
                rm = []
                logger.warning("refmaster normalize failed for %s: %s", mark.ticker, exc)
            if not rm:
                return EnrichedMark(
                    **mark.model_dump(),
                    market_price=None,
                    deviation_absolute=None,
                    deviation_percentage=None,
                    classification="NO_MARKET_DATA",
                    market_data_date=None,
                    error="unknown_ticker",
                )
        result = self.fetch_market_price(mark.ticker, mark.as_of_date)
        market_price = result.get("price")
        enriched_fields = self.compare_mark_to_market(mark.internal_mark, market_price)
        enriched_fields["market_data_date"] = result.get("date")
        if self._is_stale(mark.as_of_date) and enriched_fields["classification"] != "NO_MARKET_DATA":
            enriched_fields["classification"] = "STALE_MARK"
        if result.get("error"):
            enriched_fields["error"] = result["error"]
            enriched_fields["classification"] = "NO_MARKET_DATA"
        return EnrichedMark(**mark.model_dump(), **enriched_fields)
