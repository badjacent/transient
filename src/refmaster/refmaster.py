"""Reference master loader."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Tuple

from src.data_tools.schemas import Equity


class RefMaster:
    """Loads and holds a list of equities from refmaster_data.json."""

    def __init__(self, data_path: str | Path | None = None) -> None:
        path = Path(data_path) if data_path else Path(__file__).parent / "refmaster_data.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        equities = data.get("equities", [])
        self.equities: List[Equity] = [Equity(**eq) for eq in equities if isinstance(eq, dict)]

    def symbols(self) -> List[str]:
        return [eq.symbol for eq in self.equities]


class NormalizerAgent:
    """Normalizes various input formats to standardized equity identifiers."""

    def __init__(self, refmaster: RefMaster | None = None) -> None:
        """Initialize with a RefMaster instance."""
        self.refmaster = refmaster or RefMaster()

    def normalize(self, description_or_id: str) -> List[Tuple[Equity, float]]:
        """
        Normalize an input string to ranked equity matches with confidence scores.
        
        Handles input variations like:
        - "AAPL US" - ticker with country code
        - "AAPL.OQ" - ticker with exchange suffix
        - "Apple Inc NASDAQ" - company name with exchange (partial match on exchange)
        - "US0378331005" - ISIN
        - "037833100" - CUSIP
        - "0000320193" - CIK
        
        Args:
            description_or_id: Input string that may contain ticker, ISIN, CUSIP, CIK, etc.
            
        Returns:
            List of tuples (Equity, confidence_score) sorted by confidence (highest first).
            Confidence scores range from 0.0 to 1.0, where 1.0 is an exact match.
        """
        input_str = description_or_id.strip().upper()
        matches: List[Tuple[Equity, float]] = []
        
        # Extract potential identifiers from input
        extracted = self._extract_identifiers(input_str)
        
        # Score each equity against the input
        for equity in self.refmaster.equities:
            score = self._calculate_match_score(equity, input_str, extracted)
            if score > 0.0:
                matches.append((equity, score))
        
        # Sort by confidence score (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        return matches

    def _extract_identifiers(self, input_str: str) -> dict:
        """Extract potential identifiers from input string."""
        extracted = {
            "symbol": None,
            "isin": None,
            "cusip": None,
            "cik": None,
            "exchange": None,
            "country": None,
        }
        
        # ISIN pattern: US followed by 9 alphanumeric, then check digit (12 chars total)
        isin_match = re.search(r"\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b", input_str)
        if isin_match:
            extracted["isin"] = isin_match.group(1)
        
        # CUSIP pattern: 9 alphanumeric characters
        cusip_match = re.search(r"\b([A-Z0-9]{9})\b", input_str)
        if cusip_match and not extracted["isin"]:
            # Could be CUSIP if it's 9 chars and not part of an ISIN
            potential_cusip = cusip_match.group(1)
            if len(potential_cusip) == 9:
                extracted["cusip"] = potential_cusip
        
        # CIK pattern: 10 digits (often with leading zeros)
        cik_match = re.search(r"\b(0{0,6}[0-9]{4,10})\b", input_str)
        if cik_match:
            cik_str = cik_match.group(1)
            # Normalize CIK to 10 digits with leading zeros
            if cik_str.isdigit():
                extracted["cik"] = cik_str.zfill(10)
        
        # Extract symbol (ticker) - typically 1-5 uppercase letters/numbers, possibly with dot
        # Handle formats like "AAPL", "AAPL.OQ", "BRK.B", "AAPL US"
        symbol_match = re.search(r"\b([A-Z]{1,5}(?:\.[A-Z])?)\b", input_str)
        if symbol_match:
            symbol = symbol_match.group(1)
            # Remove exchange suffix if present (e.g., .OQ, .N, .A)
            if "." in symbol:
                symbol = symbol.split(".")[0]
            extracted["symbol"] = symbol
        
        # Extract exchange mentions (NASDAQ, NYSE, etc.)
        exchange_keywords = ["NASDAQ", "NYSE", "AMEX", "OTC"]
        for exchange in exchange_keywords:
            if exchange in input_str:
                extracted["exchange"] = exchange
        
        # Extract country codes (US, etc.)
        if " US" in input_str or input_str.endswith(" US"):
            extracted["country"] = "US"
        
        return extracted

    def _calculate_match_score(
        self, equity: Equity, input_str: str, extracted: dict
    ) -> float:
        """Calculate confidence score for a match between equity and input."""
        max_score = 0.0
        
        # Exact ISIN match (highest confidence)
        if extracted["isin"] and equity.isin:
            if equity.isin.upper() == extracted["isin"]:
                return 1.0
        
        # Exact CUSIP match (very high confidence)
        if extracted["cusip"] and equity.cusip:
            if equity.cusip.upper() == extracted["cusip"]:
                return 0.95
        
        # Exact CIK match (very high confidence)
        if extracted["cik"] and equity.cik:
            normalized_cik = equity.cik.zfill(10) if equity.cik.isdigit() else equity.cik
            if normalized_cik == extracted["cik"]:
                return 0.95
        
        # Exact symbol match (high confidence)
        if extracted["symbol"] and equity.symbol:
            if equity.symbol.upper() == extracted["symbol"]:
                max_score = max(max_score, 0.9)
                # Bonus if exchange also matches
                if extracted["exchange"] and equity.exchange:
                    if extracted["exchange"].upper() in equity.exchange.upper():
                        max_score = max(max_score, 0.95)
        
        # Partial symbol match (symbol appears in input)
        if equity.symbol:
            symbol_upper = equity.symbol.upper()
            if symbol_upper in input_str:
                # Check if it's a word boundary match (better) vs substring (worse)
                if re.search(rf"\b{symbol_upper}\b", input_str):
                    max_score = max(max_score, 0.85)
                else:
                    max_score = max(max_score, 0.6)
        
        # Exchange match only (low confidence, but better than nothing)
        if extracted["exchange"] and equity.exchange:
            if extracted["exchange"].upper() in equity.exchange.upper():
                max_score = max(max_score, 0.3)
        
        # Fuzzy ISIN match (partial)
        if extracted["isin"] and equity.isin:
            # Check if CUSIP part matches (ISIN = US + CUSIP + check digit)
            if equity.isin.startswith("US") and len(equity.isin) >= 11:
                equity_cusip_part = equity.isin[2:11]  # Skip "US" and last digit
                if extracted["isin"].startswith("US") and len(extracted["isin"]) >= 11:
                    input_cusip_part = extracted["isin"][2:11]
                    if equity_cusip_part == input_cusip_part:
                        max_score = max(max_score, 0.8)
        
        return max_score
