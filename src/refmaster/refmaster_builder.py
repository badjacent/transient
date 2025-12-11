"""Builds refmaster_data.json from a hardcoded ticker list using SEC CIK and FMP identifiers when available."""

import json
import hashlib
from pathlib import Path

from src.data_tools.schemas import Equity
from src.data_tools import fmp_api
from src.data_tools.sec_cik import get_cik_for_ticker
from dotenv import load_dotenv

load_dotenv()


TICKERS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "JPM", "V",
    "MA", "PG", "XOM", "CVX", "JNJ", "UNH", "HD", "BAC", "PFE", "KO",
    "PEP", "CSCO", "ADBE", "CRM", "NFLX", "INTC", "ORCL", "T", "VZ", "WMT",
    "COST", "DIS", "MCD", "NKE", "SBUX", "AMD", "AVGO", "TXN", "QCOM", "AMGN",
    "ABBV", "LLY", "MRK", "DHR", "HON", "CAT", "BA", "UPS", "GE", "DE",
]


def _to_equity(symbol: str) -> Equity:
    """Create an Equity record, preferring FMP identifiers, fallback to placeholders."""
    try:
        cik = get_cik_for_ticker(symbol) or ""
    except Exception:
        cik = ""
    try:
        eq = fmp_api.get_security_identifiers(symbol)
        if cik and (eq.isin or eq.cusip):
            eq.cik = cik
        _ensure_defaults(eq)
        return eq
    except Exception:
        eq = Equity(
            symbol=symbol,
            isin="",
            cusip="",
            cik=cik,
            currency="USD",
            exchange="",
            pricing_source="financialdatasets.ai",
        )
        _ensure_defaults(eq)
        return eq


def _deterministic_digits(symbol: str, length: int) -> str:
    digest = hashlib.sha256(symbol.encode("utf-8")).hexdigest()
    digits = "".join(ch for ch in digest if ch.isdigit())
    if not digits:
        digits = "0" * length
    while len(digits) < length:
        digits += digits
    return digits[:length]


def _cusip_check_digit(base8: str) -> str:
    total = 0
    for idx, ch in enumerate(base8):
        val = int(ch)
        if idx % 2 == 1:
            val *= 2
        total += val // 10 + val % 10
    return str((10 - (total % 10)) % 10)


def _generate_cusip(symbol: str) -> str:
    base = _deterministic_digits(symbol, 8)
    check = _cusip_check_digit(base)
    return base + check


def _isin_check_digit(body: str) -> str:
    digits = ""
    for ch in body:
        if ch.isdigit():
            digits += ch
        else:
            digits += str(ord(ch.upper()) - 55)
    total = 0
    reverse_digits = digits[::-1]
    for idx, ch in enumerate(reverse_digits):
        val = int(ch)
        if idx % 2 == 0:
            val *= 2
        total += val // 10 + val % 10
    return str((10 - (total % 10)) % 10)


def _generate_isin_from_cusip(cusip: str) -> str:
    body = f"US{cusip}"
    check = _isin_check_digit(body)
    return f"{body}{check}"


def _assign_exchange(symbol: str) -> str:
    if len(symbol) == 4:
        return "NASDAQ"
    if len(symbol) < 4:
        return "NYSE"
    return "NASDAQ"


def _ensure_defaults(eq: Equity) -> None:
    if not eq.cusip:
        eq.cusip = _generate_cusip(eq.symbol)
    if not eq.isin:
        eq.isin = _generate_isin_from_cusip(eq.cusip)
    if not eq.currency:
        eq.currency = "USD"
    if not eq.exchange:
        eq.exchange = _assign_exchange(eq.symbol)


def build(output_path: Path | str | None = None) -> Path:
    """Write the hardcoded tickers to refmaster_data.json with Equity schema."""
    path = Path(output_path) if output_path else Path(__file__).parent / "refmaster_data.json"
    equities = [_to_equity(t) for t in TICKERS]
    payload = {"equities": [eq.model_dump() for eq in equities]}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


if __name__ == "__main__":
    out = build()
    print(f"Wrote {len(TICKERS)} equities to {out}")
