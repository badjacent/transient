"""SEC ticker-to-CIK mapping helper."""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from typing import Dict, Optional

import requests

SEC_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
DEFAULT_USER_AGENT = "transient-ai/0.1 (mailto:example@example.com)"


@lru_cache(maxsize=1)
def fetch_cik_map() -> Dict[str, str]:
    """
    Fetch the SEC ticker->CIK mapping.

    Returns:
        Dict of uppercased ticker -> zero-padded 10-digit CIK.
    """
    ua = os.getenv("SEC_USER_AGENT") or os.getenv("USER_AGENT") or DEFAULT_USER_AGENT
    headers = {"User-Agent": ua}
    resp = requests.get(SEC_TICKER_URL, headers=headers, timeout=15)
    if resp.status_code == 403:
        raise requests.HTTPError(
            "SEC request forbidden (403). Set SEC_USER_AGENT with contact info per SEC guidelines."
        )
    resp.raise_for_status()
    data = resp.json()

    mapping: Dict[str, str] = {}
    if isinstance(data, dict):
        # Format: {"0": {"ticker": "A", "cik_str": 861459, ...}, ...}
        for entry in data.values():
            if not isinstance(entry, dict):
                continue
            ticker = entry.get("ticker")
            cik_str = entry.get("cik_str")
            if ticker and cik_str is not None:
                cik_str = str(cik_str)
                cik = cik_str.zfill(10)
                mapping[ticker.upper()] = cik
    return mapping


def get_cik_for_ticker(ticker: str) -> Optional[str]:
    """Return the zero-padded CIK for a ticker, if available."""
    if not ticker or not isinstance(ticker, str):
        return None
    symbol = ticker.strip().upper()
    # Reject obvious non-tickers (numbers, etc.)
    if not re.match(r"^[A-Z.\-]{1,10}$", symbol):
        return None
    mapping = fetch_cik_map()
    return mapping.get(symbol)
