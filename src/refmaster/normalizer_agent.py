"""Deterministic reference master normalizer (no LLM)."""

from __future__ import annotations

import csv
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Iterable, List, Optional

from src.refmaster.schema import Equity, NormalizationResult


@lru_cache(maxsize=1)
def load_equities(data_path: Optional[str] = None) -> List[Equity]:
    """Load equities from CSV or JSON; falls back to refmaster_data.json in this package."""
    base_path = Path(data_path) if data_path else Path(__file__).parent / "refmaster_data.json"
    if base_path.exists() and base_path.suffix.lower() == ".csv":
        with base_path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = [Equity(**row) for row in reader if row]
        return rows
    if base_path.exists() and base_path.suffix.lower() == ".json":
        data = json.loads(base_path.read_text(encoding="utf-8"))
        equities = data.get("equities", data) if isinstance(data, dict) else data
        return [Equity(**eq) for eq in equities if isinstance(eq, dict)]
    raise FileNotFoundError(f"Could not load refmaster data from {base_path}")


class NormalizerAgent:
    """Normalize free-form identifiers to canonical equities."""

    def __init__(
        self,
        equities: Optional[Iterable[Equity]] = None,
        thresholds: Optional[dict] = None,
    ) -> None:
        self.equities = list(equities) if equities is not None else load_equities()
        self.thresholds = {
            "exact": 1.0,
            "high": 0.9,
            "ambiguous_low": 0.6,
            "ambiguous_high": 0.85,
            "reject": 0.4,
        }
        if thresholds:
            self.thresholds.update(thresholds)

    def normalize(self, description_or_id: str, top_k: int = 5) -> List[NormalizationResult]:
        """Return ranked matches with confidence and reasons."""
        if not description_or_id:
            return []
        input_str = description_or_id.strip()
        extracted = self._extract_identifiers(input_str)
        scored: List[NormalizationResult] = []
        for eq in self.equities:
            conf, reasons = self._score(eq, extracted, input_str)
            if conf > 0:
                scored.append(
                    NormalizationResult(
                        equity=eq,
                        confidence=conf,
                        reasons=reasons,
                        ambiguous=False,
                    )
                )
        scored.sort(key=lambda r: r.confidence, reverse=True)
        if not scored or scored[0].confidence < self.thresholds["reject"]:
            return []
        # Ambiguity detection
        if len(scored) > 1 and scored[0].confidence <= self.thresholds["ambiguous_high"]:
            if scored[1].confidence >= self.thresholds["ambiguous_low"]:
                for res in scored:
                    if res.confidence >= self.thresholds["ambiguous_low"]:
                        res.ambiguous = True
        return scored[:top_k]

    def _score(self, eq: Equity, extracted: dict, input_str: str) -> tuple[float, List[str]]:
        reasons: List[str] = []
        score = 0.0

        # Exact identifiers
        if extracted["isin"] and eq.isin and eq.isin.upper() == extracted["isin"]:
            return self.thresholds["exact"], ["isin_exact"]
        if extracted["cusip"] and eq.cusip and eq.cusip.upper() == extracted["cusip"]:
            return self.thresholds["high"], ["cusip_exact"]
        if extracted["cik"] and eq.cik and eq.cik.upper() == extracted["cik"]:
            return self.thresholds["high"], ["cik_exact"]

        # Symbol matches
        if extracted["symbol"] and eq.symbol and eq.symbol.upper() == extracted["symbol"]:
            score = max(score, 0.9)
            reasons.append("symbol_exact")
            if extracted["exchange"] and eq.exchange and extracted["exchange"] in eq.exchange.upper():
                score = max(score, 0.95)
                reasons.append("exchange_match")
            if extracted["country"] and eq.country and extracted["country"] == eq.country.upper():
                score = max(score, 0.92)
                reasons.append("country_match")

        # Partial symbol/name matches
        if eq.symbol and eq.symbol.upper() in input_str.upper():
            score = max(score, 0.7)
            reasons.append("symbol_in_text")
        if extracted["exchange"] and eq.exchange and extracted["exchange"] in eq.exchange.upper():
            score = max(score, 0.3)
            reasons.append("exchange_only")

        return score, reasons

    def _extract_identifiers(self, input_str: str) -> dict:
        out = {"symbol": None, "isin": None, "cusip": None, "cik": None, "exchange": None, "country": None}
        text = input_str.upper()
        isin_match = re.search(r"\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b", text)
        if isin_match:
            out["isin"] = isin_match.group(1)
        cusip_match = re.search(r"\b([A-Z0-9]{9})\b", text)
        if cusip_match and not out["isin"]:
            out["cusip"] = cusip_match.group(1)
        cik_match = re.search(r"\b(0{0,6}[0-9]{4,10})\b", text)
        if cik_match:
            out["cik"] = cik_match.group(1).zfill(10)
        symbol_match = re.search(r"\b([A-Z]{1,5}(?:\.[A-Z])?)\b", text)
        if symbol_match:
            symbol = symbol_match.group(1)
            if "." in symbol:
                symbol = symbol.split(".")[0]
            out["symbol"] = symbol
        exchange_keywords = ["NASDAQ", "NYSE", "AMEX", "OTC"]
        for ex in exchange_keywords:
            if ex in text:
                out["exchange"] = ex
                break
        if " US" in text or text.endswith(" US"):
            out["country"] = "US"
        return out


def normalize(description_or_id: str, top_k: int = 5) -> List[NormalizationResult]:
    """Convenience function using default agent/cache."""
    agent = NormalizerAgent()
    return agent.normalize(description_or_id, top_k=top_k)


def resolve_ticker(symbol: str) -> Optional[Equity]:
    """Return a canonical equity for an exact symbol match."""
    agent = NormalizerAgent()
    symbol = (symbol or "").upper()
    for eq in agent.equities:
        if eq.symbol.upper() == symbol:
            return eq
    return None
