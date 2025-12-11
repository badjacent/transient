"""FinancialModelingPrep.com client for reference data lookups (CUSIP/ISIN)."""

from __future__ import annotations

import os
from typing import Dict, Optional

import requests
from dotenv import load_dotenv

from src.data_tools.schemas import Equity

load_dotenv()

BASE_URL = "https://financialmodelingprep.com/api/v3"


def _get_api_key() -> str:
    """Fetch FMP API key from environment."""
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        raise ValueError(
            "FMP_API_KEY not found in environment variables. Set it in your .env file."
        )
    return api_key


def _request_json(path: str, params: Optional[Dict] = None) -> Dict:
    """Perform a GET request and return JSON, raising for non-200."""
    api_key = _get_api_key()
    url = f"{BASE_URL}/{path.lstrip('/')}"
    query = params.copy() if params else {}
    query["apikey"] = api_key
    resp = requests.get(url, params=query, timeout=10)
    if resp.status_code != 200:
        raise requests.RequestException(
            f"FMP request failed with status {resp.status_code}: {resp.text}"
        )
    return resp.json()


def get_security_identifiers(ticker: str) -> Equity:
    """
    Map a ticker to identifiers using FMP profile endpoint.

    Args:
        ticker: Symbol to look up (e.g., AAPL).

    Returns:
        Equity model populated with symbol, cusip, isin, and placeholders for other fields.
    """
    if not ticker or not isinstance(ticker, str):
        raise ValueError("Ticker must be a non-empty string.")
    symbol = ticker.strip().upper()
    data = _request_json(f"profile/{symbol}")

    # FMP returns a list of profiles; take the first valid entry.
    profile = None
    if isinstance(data, list) and data:
        profile = data[0]
    elif isinstance(data, dict):
        profile = data

    if not profile or not isinstance(profile, dict):
        raise ValueError(f"No profile data returned for ticker {symbol}.")

    cusip = profile.get("cusip", "") or ""
    isin = profile.get("isin", "") or ""
    cik = profile.get("cik", "") or ""
    currency = profile.get("currency", "") or ""
    exchange = profile.get("exchangeShortName", "") or profile.get("exchange", "") or ""

    return Equity(
        symbol=symbol,
        cusip=cusip,
        isin=isin,
        cik=cik,
        currency=currency or "USD",
        exchange=exchange,
        pricing_source="financialmodelingprep.com",
    )
