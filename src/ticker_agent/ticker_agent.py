"""Simple ticker agent that routes questions to desk data tools."""

from __future__ import annotations

import os
import re
import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv

from src.data_tools.fd_api import (
    get_balance_sheets,
    get_cash_flow_statements,
    get_equity_snapshot,
    get_income_statements,
)
from src.data_tools.schemas import (
    BalanceSheet,
    CashFlowStatement,
    EquitySnapshot,
    IncomeStatement,
)
from src.ticker_agent import classifier
from src.ticker_agent.prompts import SYSTEM_PROMPT, TOOLS_PROMPT

load_dotenv()


logger = logging.getLogger(__name__)


def _get_llm_model() -> Optional[str]:
    """Return LLM model name from env or None if not configured."""
    return os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL")


def _extract_ticker(question: str) -> Optional[str]:
    """Heuristic ticker extraction with support for suffixes (AAPL US, AAPL.OQ)."""
    if not question:
        return None
    text = question.strip().upper()
    
    # Comprehensive stopwords including common financial/date terms
    stopwords = {
        "AND", "THE", "LAST", "THIS", "PLEASE", "SHOW", "GIVE", "SUMMARIZE", "SUMMARISE",
        "PAST", "OVER", "FOR", "FROM", "ABOUT", "WITH", "INTO", "THAT", "WHAT", "WHEN",
        "WHERE", "WHICH", "WHO", "WHY", "HOW", "WILL", "WOULD", "SHOULD", "COULD",
        "YEARS", "YEAR", "MONTHS", "MONTH", "DAYS", "DAY", "WEEKS", "WEEK", "QUARTERS",
        "QUARTER", "REVENUE", "REVENUES", "INCOME", "EARNINGS", "PROFIT", "LOSS",
        "PRICE", "PRICES", "STOCK", "STOCKS", "SHARES", "SHARE", "MARKET", "MARKETS",
        "DATA", "INFO", "INFORMATION", "SUMMARY", "SUMMARIES", "HISTORY", "HISTORIES",
        "PERFORMANCE", "RETURN", "RETURNS", "DIVIDEND", "DIVIDENDS", "YIELD", "YIELDS",
        "EPS", "PE", "RATIO", "RATIOS", "VALUE", "VALUES", "CAP", "SECTOR", "INDUSTRY"
    }
    
    pattern = re.compile(r"^[A-Z]{1,5}(\.[A-Z]{1,3})?$")
    
    # First, try to find ticker after common prepositions (for, of, about)
    # This handles cases like "revenue for NVDA" or "last 4 years of revenue for NVDA"
    preposition_pattern = re.compile(r"\b(?:FOR|OF|ABOUT|ON|IN)\s+([A-Z]{1,5}(?:\.[A-Z]{1,3})?)\b", re.IGNORECASE)
    matches = preposition_pattern.findall(text)
    for match in matches:
        ticker = match.split(".")[0]
        if ticker not in stopwords and len(ticker) >= 1:
            return ticker
    
    # Fallback: look for ticker-like patterns, but skip stopwords
    parts = re.split(r"\s+", text)
    for token in parts:
        cleaned = token.strip(".,:;!?()")
        if not cleaned or cleaned in stopwords:
            continue
        if pattern.match(cleaned):
            ticker = cleaned.split(".")[0]
            # Additional check: skip if it's a common word
            if ticker not in stopwords:
                return ticker
    
    # Last resort: find any ticker-like pattern, but still filter stopwords
    all_matches = re.findall(r"\b([A-Z]{1,5}(?:\.[A-Z]{1,3})?)\b", text)
    for match in all_matches:
        ticker = match.split(".")[0]
        if ticker not in stopwords:
            return ticker
    
    return None


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
        except Exception as exc:
            logger.warning("LLM classification failed; falling back to heuristics: %s", exc)
            # Fall back to heuristics on LLM failure
            pass
    q = (question or "").lower()
    ticker = _extract_ticker(question or "")
    income_keywords = ["income statement", "eps", "net income", "gross profit", "operating income"]
    revenue_history_keywords = ["last 4", "last four", "past 4", "four years", "income statement", "statement"]
    if any(word in q for word in ["income statement", "net income", "gross profit", "eps"]) or (
        "revenue" in q and any(term in q for term in ["year", "years", "history", "statement"])
    ):
        return "income_statement_summary", {"ticker": ticker}
    if any(k in q for k in ["dividend", "yield", "ex-div", "payout"]):
        return "dividend_overview", {"ticker": ticker}
    if any(k in q for k in ["performance", "return", "ytd", "1m", "3m", "month", "quarter"]):
        return "price_performance_summary", {"ticker": ticker}
    if any(k in q for k in ["vol", "risk"]) and "fundamental" not in q and "trend" not in q:
        return "volatility_comparison_convertible", {"ticker": ticker}
    if any(k in q for k in ["fundamental", "risk trend", "financial health", "risk factor"]) or (
        "risk" in q and any(term in q for term in ["trend", "factor", "indicator", "analysis"])
    ):
        return "fundamentals_risk_summary", {"ticker": ticker}
    if any(k in q for k in ["news", "headline", "sentiment"]):
        return "news_sentiment_stub", {"ticker": ticker}
    if any(k in q for k in ["revenue", "fundamentals", "market cap", "sector"]):
        return "financials_revenue_summary", {"ticker": ticker}
    return "generic_unhandled", {"ticker": ticker}


def _build_metrics(
    intent: str,
    snap: EquitySnapshot,
    income_history: Optional[List[IncomeStatement]] = None,
    balance_sheets: Optional[List[BalanceSheet]] = None,
    cash_flows: Optional[List[CashFlowStatement]] = None,
) -> Dict[str, Any]:
    base = {
        "ticker": snap.ticker,
        "as_of": snap.date,
        "price": snap.price,
    }
    if intent == "price_performance_summary":
        base.update({"return_1d": snap.return_1d, "return_5d": snap.return_5d})
    elif intent == "financials_revenue_summary":
        base.update({"market_cap": snap.market_cap, "sector": snap.sector, "industry": snap.industry})
    elif intent == "income_statement_summary":
        entries: List[Dict[str, Any]] = []
        if income_history:
            for stmt in income_history:
                entries.append(
                    {
                        "fiscal_year": stmt.fiscal_year,
                        "period": stmt.period,
                        "total_revenue": stmt.total_revenue,
                        "operating_income": stmt.operating_income,
                        "net_income": stmt.net_income,
                        "diluted_eps": stmt.diluted_eps,
                        "currency": stmt.currency,
                    }
                )
        base.update({"income_statements": entries})
    elif intent == "dividend_overview":
        # Placeholder since dividends not available from current tool
        base.update({"dividend_yield": None, "next_ex_date": None})
    elif intent == "volatility_comparison_convertible":
        base.update({"return_5d": snap.return_5d})
    elif intent == "news_sentiment_stub":
        base.update({"sentiment": None, "headline_sample": None})
    elif intent == "fundamentals_risk_summary":
        # Income statement metrics
        income_entries: List[Dict[str, Any]] = []
        if income_history:
            for stmt in income_history:
                income_entries.append(
                    {
                        "fiscal_year": stmt.fiscal_year,
                        "period": stmt.period,
                        "total_revenue": stmt.total_revenue,
                        "operating_income": stmt.operating_income,
                        "net_income": stmt.net_income,
                        "diluted_eps": stmt.diluted_eps,
                        "currency": stmt.currency,
                    }
                )
        
        # Balance sheet metrics
        balance_entries: List[Dict[str, Any]] = []
        if balance_sheets:
            for bs in balance_sheets:
                balance_entries.append(
                    {
                        "fiscal_year": bs.fiscal_year,
                        "period": bs.period,
                        "current_ratio": bs.current_ratio,
                        "debt_to_equity": bs.debt_to_equity,
                        "working_capital": bs.working_capital,
                        "cash_and_cash_equivalents": bs.cash_and_cash_equivalents,
                        "total_debt": bs.total_debt,
                        "total_equity": bs.total_equity,
                        "currency": bs.currency,
                    }
                )
        
        # Cash flow metrics
        cash_flow_entries: List[Dict[str, Any]] = []
        if cash_flows:
            for cf in cash_flows:
                cash_flow_entries.append(
                    {
                        "fiscal_year": cf.fiscal_year,
                        "period": cf.period,
                        "operating_cash_flow": cf.operating_cash_flow,
                        "free_cash_flow": cf.free_cash_flow,
                        "capital_expenditures": cf.capital_expenditures,
                        "currency": cf.currency,
                    }
                )
        
        base.update({
            "market_cap": snap.market_cap,
            "sector": snap.sector,
            "industry": snap.industry,
            "income_statements": income_entries,
            "balance_sheets": balance_entries,
            "cash_flow_statements": cash_flow_entries,
        })
    return base


def _summary(
    intent: str,
    snap: EquitySnapshot,
    metrics: Dict[str, Any],
    income_history: Optional[List[IncomeStatement]] = None,
    balance_sheets: Optional[List[BalanceSheet]] = None,
    cash_flows: Optional[List[CashFlowStatement]] = None,
) -> str:
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
    if intent == "income_statement_summary":
        if income_history:
            latest = income_history[0]
            oldest = income_history[-1]
            latest_rev = latest.total_revenue
            oldest_rev = oldest.total_revenue
            change_text = ""
            if latest_rev is not None and oldest_rev is not None and latest_rev != oldest_rev:
                delta = latest_rev - oldest_rev
                change_text = f" Change over span: {delta:,.0f}."
            
            # Handle fiscal_year being None - use period or fiscal_period as fallback
            year_text = ""
            if latest.fiscal_year is not None:
                year_text = f"fiscal year {latest.fiscal_year}"
            elif latest.fiscal_period:
                year_text = f"period {latest.fiscal_period}"
            elif latest.period:
                year_text = f"{latest.period} period"
            
            if year_text:
                return (
                    f"{snap.ticker} revenue history spans {len(income_history)} periods. "
                    f"Most recent {year_text} revenue was "
                    f"{latest_rev:,.0f} {latest.currency or ''}.{change_text}".strip()
                )
            else:
                return (
                    f"{snap.ticker} revenue history spans {len(income_history)} periods. "
                    f"Most recent revenue was "
                    f"{latest_rev:,.0f} {latest.currency or ''}.{change_text}".strip()
                )
        return f"{snap.ticker} income statement data unavailable from current source."
    if intent == "dividend_overview":
        return f"{snap.ticker} dividend details unavailable from current data source."
    if intent == "volatility_comparison_convertible":
        return (
            f"{snap.ticker} recent 5D return multiplier {snap.return_5d:.2f}; "
            "use as proxy until convertible vol data is available."
        )
    if intent == "news_sentiment_stub":
        return f"{snap.ticker} news sentiment not available from current source; consider enabling LLM/news feed."
    if intent == "fundamentals_risk_summary":
        parts = []
        
        # Header
        parts.append(f"{snap.ticker} Fundamentals & Risk Analysis (${snap.price:.2f}, {snap.sector}):")
        
        # FUNDAMENTALS SECTION
        fundamentals_parts = []
        
        # Revenue trends
        if income_history and len(income_history) >= 2:
            latest_income = income_history[0]
            oldest_income = income_history[-1]
            if latest_income.total_revenue and oldest_income.total_revenue:
                rev_growth = ((latest_income.total_revenue - oldest_income.total_revenue) / oldest_income.total_revenue) * 100
                trend_direction = "accelerating" if rev_growth > 20 else "growing" if rev_growth > 0 else "declining"
                fundamentals_parts.append(
                    f"Revenue {trend_direction}: {latest_income.total_revenue:,.0f} {latest_income.currency or ''} "
                    f"({rev_growth:+.1f}% over {len(income_history)} periods)"
                )
        
        # Profitability trends
        if income_history and len(income_history) >= 2:
            latest_income = income_history[0]
            oldest_income = income_history[-1]
            if latest_income.net_income is not None and oldest_income.net_income is not None:
                ni_growth = ((latest_income.net_income - oldest_income.net_income) / abs(oldest_income.net_income)) * 100 if oldest_income.net_income != 0 else None
                if ni_growth is not None:
                    fundamentals_parts.append(
                        f"Net income: {latest_income.net_income:,.0f} {latest_income.currency or ''} "
                        f"({ni_growth:+.1f}% change)"
                    )
                else:
                    fundamentals_parts.append(f"Net income: {latest_income.net_income:,.0f} {latest_income.currency or ''}")
        elif income_history and income_history[0].net_income is not None:
            latest_income = income_history[0]
            fundamentals_parts.append(f"Net income: {latest_income.net_income:,.0f} {latest_income.currency or ''}")
        
        # Operating margin trend
        if income_history and len(income_history) >= 2:
            latest = income_history[0]
            oldest = income_history[-1]
            if latest.total_revenue and latest.operating_income and oldest.total_revenue and oldest.operating_income:
                latest_margin = (latest.operating_income / latest.total_revenue) * 100
                oldest_margin = (oldest.operating_income / oldest.total_revenue) * 100
                margin_change = latest_margin - oldest_margin
                fundamentals_parts.append(
                    f"Operating margin: {latest_margin:.1f}% "
                    f"({margin_change:+.1f}pp change)"
                )
        
        if fundamentals_parts:
            parts.append("Fundamentals: " + "; ".join(fundamentals_parts) + ".")
        
        # RISK TRENDS SECTION
        risk_parts = []
        risk_factors = []
        
        # Liquidity risk and trends
        if balance_sheets and len(balance_sheets) >= 1:
            latest_bs = balance_sheets[0]
            if latest_bs.current_ratio is not None:
                ratio = latest_bs.current_ratio
                liquidity_status = "strong" if ratio > 1.5 else "adequate" if ratio > 1.0 else "weak"
                risk_parts.append(f"Liquidity: Current ratio {ratio:.2f} ({liquidity_status})")
                
                # Check trend if we have historical data
                if len(balance_sheets) >= 2:
                    oldest_bs = balance_sheets[-1]
                    if oldest_bs.current_ratio is not None:
                        ratio_change = ratio - oldest_bs.current_ratio
                        trend = "improving" if ratio_change > 0.1 else "deteriorating" if ratio_change < -0.1 else "stable"
                        risk_parts[-1] += f" ({trend} trend)"
                
                if ratio < 1.0:
                    risk_factors.append("liquidity risk")
                
                if latest_bs.cash_and_cash_equivalents:
                    risk_parts.append(f"Cash: {latest_bs.cash_and_cash_equivalents:,.0f} {latest_bs.currency or ''}")
        
        # Leverage risk and trends
        if balance_sheets and len(balance_sheets) >= 1:
            latest_bs = balance_sheets[0]
            if latest_bs.debt_to_equity is not None:
                de_ratio = latest_bs.debt_to_equity
                leverage_status = "high" if de_ratio > 1.0 else "moderate" if de_ratio > 0.5 else "low"
                risk_parts.append(f"Leverage: Debt-to-equity {de_ratio:.2f} ({leverage_status})")
                
                # Check trend if we have historical data
                if len(balance_sheets) >= 2:
                    oldest_bs = balance_sheets[-1]
                    if oldest_bs.debt_to_equity is not None:
                        de_change = de_ratio - oldest_bs.debt_to_equity
                        trend = "increasing" if de_change > 0.1 else "decreasing" if de_change < -0.1 else "stable"
                        risk_parts[-1] += f" ({trend} trend)"
                
                if de_ratio > 1.0:
                    risk_factors.append("high leverage")
        
        # Cash flow risk and trends
        if cash_flows and len(cash_flows) >= 1:
            latest_cf = cash_flows[0]
            if latest_cf.free_cash_flow is not None:
                fcf = latest_cf.free_cash_flow
                fcf_status = "positive" if fcf > 0 else "negative"
                risk_parts.append(f"Free cash flow: {fcf:,.0f} {latest_cf.currency or ''} ({fcf_status})")
                
                # Check trend if we have historical data
                if len(cash_flows) >= 2:
                    oldest_cf = cash_flows[-1]
                    if oldest_cf.free_cash_flow is not None:
                        fcf_change = fcf - oldest_cf.free_cash_flow
                        trend = "improving" if fcf_change > 0 else "deteriorating" if fcf_change < 0 else "stable"
                        risk_parts[-1] += f" ({trend} trend)"
                
                if fcf < 0:
                    risk_factors.append("negative free cash flow")
        
        # Risk summary
        if risk_parts:
            parts.append("Risk Assessment: " + "; ".join(risk_parts) + ".")
        else:
            parts.append("Risk Assessment: Limited risk data available (balance sheet and cash flow data may be unavailable).")
        
        if risk_factors:
            parts.append(f"⚠️ Key Risk Factors: {', '.join(risk_factors)}.")
        elif balance_sheets or cash_flows:
            parts.append("No major risk factors identified from available data.")
        
        return " ".join(parts)
    return f"{snap.ticker} snapshot at ${snap.price:.2f}."


def _error_response(reason: str, detail: str = "") -> Dict[str, Any]:
    """Return error response with required summary and metrics fields."""
    return {
        "intent": "generic_unhandled",
        "summary": f"Unable to answer: {reason}. {detail}".strip(),
        "metrics": {},  # Always include metrics (may be empty dict)
        "error": reason,
    }


@lru_cache(maxsize=64)
def _cached_snapshot(ticker: str) -> EquitySnapshot:
    return get_equity_snapshot(ticker)


@lru_cache(maxsize=64)
def _cached_income_statements(ticker: str) -> Tuple[IncomeStatement, ...]:
    return tuple(get_income_statements(ticker))


@lru_cache(maxsize=64)
def _cached_balance_sheets(ticker: str) -> Tuple[BalanceSheet, ...]:
    return tuple(get_balance_sheets(ticker))


@lru_cache(maxsize=64)
def _cached_cash_flow_statements(ticker: str) -> Tuple[CashFlowStatement, ...]:
    return tuple(get_cash_flow_statements(ticker))


def run(question: str) -> Dict[str, Any]:
    """
    Answer a question about a ticker using desk data tools.
    
    Returns:
        Dict with required fields:
        - "summary" (str): Human-readable summary of the answer
        - "metrics" (dict): Structured metrics data (always present, may be empty)
        - "intent" (str): Detected intent classification
        - "source" (str): Data source identifier
        - "system_prompt" (str): System prompt used
        - "tools_prompt" (str): Tools prompt describing available data sources
    """
    intent, meta = _classify_intent(question)
    resolved_ticker = meta.get("ticker") or _extract_ticker(question or "")
    if not resolved_ticker:
        return _error_response("invalid_ticker", "Provide a ticker in the question.")
    try:
        snap = _cached_snapshot(resolved_ticker)
    except Exception as exc:
        return _error_response("data_unavailable", str(exc))

    income_history: Optional[List[IncomeStatement]] = None
    balance_sheets: Optional[List[BalanceSheet]] = None
    cash_flows: Optional[List[CashFlowStatement]] = None
    
    data_warnings: List[str] = []

    if intent == "income_statement_summary":
        try:
            income_history = list(_cached_income_statements(resolved_ticker))
            if not income_history:
                raise ValueError("Income statements unavailable")
        except Exception as exc:
            return _error_response("data_unavailable", f"Income statements unavailable: {exc}")
    elif intent == "fundamentals_risk_summary":
        # Fetch all three statement types for comprehensive analysis
        try:
            income_history = list(_cached_income_statements(resolved_ticker))
        except Exception as exc:
            # Don't fail completely if one statement type fails
            data_warnings.append(f"Income statements unavailable: {exc}")

        try:
            balance_sheets = list(_cached_balance_sheets(resolved_ticker))
        except Exception as exc:
            data_warnings.append(f"Balance sheets unavailable: {exc}")

        try:
            cash_flows = list(_cached_cash_flow_statements(resolved_ticker))
        except Exception as exc:
            data_warnings.append(f"Cash flow statements unavailable: {exc}")

        # At least one statement type should be available
        if not income_history and not balance_sheets and not cash_flows:
            return _error_response(
                "data_unavailable",
                "Unable to fetch financial statements for fundamentals analysis."
            )
    
    metrics = _build_metrics(
        intent, snap,
        income_history=income_history,
        balance_sheets=balance_sheets,
        cash_flows=cash_flows,
    )
    summary = _summary(
        intent, snap, metrics,
        income_history=income_history,
        balance_sheets=balance_sheets,
        cash_flows=cash_flows,
    )

    if data_warnings:
        metrics.setdefault("data_warnings", data_warnings)
        summary = f"{summary} Data gaps: {'; '.join(data_warnings)}."

    # Ensure both summary and metrics are always present (requirement)
    assert isinstance(metrics, dict), "metrics must be a dict"
    assert isinstance(summary, str), "summary must be a string"
    
    return {
        "intent": intent,
        "summary": summary,
        "metrics": metrics,
        "source": snap.source,
        "system_prompt": SYSTEM_PROMPT,
        "tools_prompt": TOOLS_PROMPT,
    }


def run_many(questions: List[str]) -> List[Dict[str, Any]]:
    """Batch process questions, reusing cached snapshots where possible."""
    results: List[Dict[str, Any]] = []
    for q in questions:
        results.append(run(q))
    return results
