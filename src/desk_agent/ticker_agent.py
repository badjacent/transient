"""Simple ticker agent that routes questions to desk data tools."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional, Tuple

from dotenv import load_dotenv

from src.data_tools.fd_api import get_equity_snapshot
from src.data_tools.schemas import EquitySnapshot
from src.desk_agent import classifier
from src.desk_agent.prompts import SYSTEM_PROMPT, TOOLS_PROMPT

load_dotenv()


def _get_llm_model() -> Optional[str]:
    """Return LLM model name from env or None if not configured."""
    return os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL")


def _extract_ticker(question: str) -> Optional[str]:
    """Heuristic ticker extraction: first 1-5 letter uppercase token."""
    if not question:
        return None
    match = re.search(r"\b([A-Z]{1,5})\b", question)
    return match.group(1) if match else None


def _classify_intent(question: str) -> Tuple[str, Dict[str, Any]]:
    """Classify using LLM when available; otherwise fall back to heuristics."""
    model = _get_llm_model()
    if model:
        try:
            intent, confidence, slots = classifier.classify_question(
                question,
                model=model,
            )
            ticker = slots.get("ticker") if isinstance(slots, dict) else None
            return intent, {"slots": slots, "confidence": confidence, "ticker": ticker}
        except Exception:
            # Fall back to heuristics on LLM failure
            pass
    q = (question or "").lower()
    ticker = _extract_ticker(question or "")
    if any(k in q for k in ["dividend", "yield", "ex-div", "payout"]):
        return "dividend_overview", {"ticker": ticker}
    if any(k in q for k in ["performance", "return", "ytd", "1m", "3m", "month", "quarter"]):
        return "price_performance_summary", {"ticker": ticker}
    if any(k in q for k in ["vol", "risk"]):
        return "volatility_comparison_convertible", {"ticker": ticker}
    if any(k in q for k in ["revenue", "fundamentals", "market cap", "sector"]):
        return "financials_revenue_summary", {"ticker": ticker}
    return "generic_unhandled", {"ticker": ticker}


def _build_metrics(intent: str, snap: EquitySnapshot) -> Dict[str, Any]:
    base = {
        "ticker": snap.ticker,
        "as_of": snap.date,
        "price": snap.price,
    }
    if intent == "price_performance_summary":
        base.update({"return_1d": snap.return_1d, "return_5d": snap.return_5d})
    elif intent == "financials_revenue_summary":
        base.update({"market_cap": snap.market_cap, "sector": snap.sector, "industry": snap.industry})
    elif intent == "dividend_overview":
        # Placeholder since dividends not available from current tool
        base.update({"dividend_yield": None, "next_ex_date": None})
    elif intent == "volatility_comparison_convertible":
        base.update({"return_5d": snap.return_5d})
    return base


def _summary(intent: str, snap: EquitySnapshot, metrics: Dict[str, Any]) -> str:
    if intent == "price_performance_summary":
        return (
            f"{snap.ticker} trades at ${snap.price:.2f}. "
            f"1D: {snap.return_1d:.2f}x, 5D: {snap.return_5d:.2f}x."
        )
    if intent == "financials_revenue_summary":
        return (
            f"{snap.ticker} price ${snap.price:.2f}, sector {snap.sector}, "
            f"market cap ${snap.market_cap:,.0f}."
        )
    if intent == "dividend_overview":
        return f"{snap.ticker} dividend details unavailable from current data source."
    if intent == "volatility_comparison_convertible":
        return (
            f"{snap.ticker} recent 5D return multiplier {snap.return_5d:.2f}; "
            "use as proxy until convertible vol data is available."
        )
    return f"{snap.ticker} snapshot at ${snap.price:.2f}."


def _error_response(reason: str, detail: str = "") -> Dict[str, Any]:
    return {
        "intent": "generic_unhandled",
        "summary": f"Unable to answer: {reason}. {detail}".strip(),
        "metrics": {},
        "error": reason,
    }


def run(question: str) -> Dict[str, Any]:
    """Answer a question about a ticker using desk data tools."""
    intent, meta = _classify_intent(question)
    resolved_ticker = meta.get("ticker") or _extract_ticker(question or "")
    if not resolved_ticker:
        return _error_response("invalid_ticker", "Provide a ticker in the question.")
    try:
        snap = get_equity_snapshot(resolved_ticker)
    except Exception as exc:
        return _error_response("data_unavailable", str(exc))
    
    metrics = _build_metrics(intent, snap)
    summary = _summary(intent, snap, metrics)
    return {
        "intent": intent,
        "summary": summary,
        "metrics": metrics,
        "source": snap.source,
        "system_prompt": SYSTEM_PROMPT,
        "tools_prompt": TOOLS_PROMPT,
    }
