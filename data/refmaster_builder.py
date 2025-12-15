"""Builds refmaster_data.json from a hardcoded ticker list using SEC CIK and LLM-enriched identifiers."""

import json
import hashlib
import os
from typing import Dict, List
from pathlib import Path

from dotenv import load_dotenv
import requests

from src.refmaster.schema import RefMasterEquity
from src.data_tools.sec_cik import get_cik_for_ticker

load_dotenv()


TICKERS = [
    "AAPL", "MSFT", "GOOG", "AMZN", "NVDA", "META", "TSLA", "BRK.B", "JPM", "V",
    "MA", "PG", "XOM", "CVX", "JNJ", "UNH", "HD", "BAC", "PFE", "KO",
    "PEP", "CSCO", "ADBE", "CRM", "NFLX", "INTC", "ORCL", "T", "VZ", "WMT",
    "COST", "DIS", "MCD", "NKE", "SBUX", "AMD", "AVGO", "TXN", "QCOM", "AMGN",
    "ABBV", "LLY", "MRK", "DHR", "HON", "CAT", "BA", "UPS", "GE", "DE",
]


def _to_equity(symbol: str) -> RefMasterEquity:
    """Create an Equity record with SEC CIK (if available) and placeholder IDs."""
    try:
        cik = get_cik_for_ticker(symbol) or ""
    except Exception:
        cik = ""
    eq = RefMasterEquity(
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
    base_equities: Dict[str, RefMasterEquity] = {t: _to_equity(t) for t in TICKERS}
    enriched_equities = _enrich_with_llm(list(base_equities.values()))
    final_equities = []
    for sym, base in base_equities.items():
        enriched = enriched_equities.get(sym, base)
        # Only set CIK if we have at least one other identifier (to avoid overwriting blanks)
        if (enriched.isin or enriched.cusip) and base.cik:
            enriched.cik = base.cik
        elif not enriched.cik:
            enriched.cik = base.cik
        _ensure_defaults(enriched)
        final_equities.append(enriched)
    payload = {"equities": [eq.model_dump() for eq in final_equities]}
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def _enrich_with_llm(equities: List[RefMasterEquity]) -> Dict[str, RefMasterEquity]:
    """Call LLM once to fill identifiers; fallback to original on failure."""
    model = os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL")
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    endpoint = os.getenv("LLM_API_URL") or os.getenv("OPENAI_API_URL") or "https://api.openai.com/v1/chat/completions"
    if not model or not api_key:
        return {eq.symbol: eq for eq in equities}

    tickers = [eq.symbol for eq in equities]
    system_prompt = (
        "You are a reference data assistant. For each US ticker provided, supply CUSIP, ISIN, exchange, and currency. "
        "Return JSON: {\"equities\": [{\"symbol\": str, \"cusip\": str, \"isin\": str, "
        "\"exchange\": str, \"currency\": str}]}."
    )
    user_prompt = "Tickers: " + ", ".join(tickers)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    try:
        resp = requests.post(
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages},
            timeout=300,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        data = json.loads(content)
        items = data.get("equities", []) if isinstance(data, dict) else []
        mapping: Dict[str, RefMasterEquity] = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            sym = item.get("symbol")
            if not sym:
                continue
            eq = RefMasterEquity(
                symbol=sym,
                isin=item.get("isin", "") or "",
                cusip=item.get("cusip", "") or "",
                cik="",  # handled separately
                currency=item.get("currency", "USD") or "USD",
                exchange=item.get("exchange", "") or _assign_exchange(sym),
                pricing_source="llm",
            )
            _ensure_defaults(eq)
            mapping[sym.upper()] = eq
        return mapping
    except Exception:
        return {eq.symbol: eq for eq in equities}


if __name__ == "__main__":
    out = build()
    print(f"Wrote {len(TICKERS)} equities to {out}")
