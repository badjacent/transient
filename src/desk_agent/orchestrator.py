"""Desk agent orchestrator that chains refmaster, OMS, pricing, ticker agent, and market context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

import yaml
from src.desk_agent.config import load_config
from src.refmaster import NormalizerAgent
from src.oms import OMSAgent
from src.pricing import PricingAgent
from src.ticker_agent import ticker_agent
from src.data_tools.fd_api import get_equity_snapshot


class DeskAgentOrchestrator:
    """Runs a scenario end-to-end and aggregates results."""

    def __init__(
        self,
        config_path: str | None = None,
        normalizer: NormalizerAgent | None = None,
        oms_agent: OMSAgent | None = None,
        pricing_agent: PricingAgent | None = None,
    ) -> None:
        self.config = load_config(config_path)
        self.normalizer = normalizer or NormalizerAgent()
        self.oms_agent = oms_agent or OMSAgent()
        self.pricing_agent = pricing_agent or PricingAgent()

    def load_scenario(self, name_or_path: str | Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(name_or_path, dict):
            return name_or_path
        scenarios_dir = Path(self.config["scenarios_path"])
        path = Path(name_or_path)
        if not path.exists():
            path = scenarios_dir / name_or_path
        if not path.exists():
            raise FileNotFoundError(f"Scenario not found: {name_or_path}")
        if path.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(path.read_text()) or {}
        return json.loads(path.read_text())

    def run_scenario(self, scenario: str | Dict[str, Any]) -> Dict[str, Any]:
        data = self.load_scenario(scenario)
        trades = data.get("trades", [])
        marks = data.get("marks", [])
        questions = data.get("questions", [])

        data_quality = self._normalize_trades(trades + marks + questions)
        trade_results = self._run_trades(trades)
        pricing_results = self._run_pricing(marks)
        ticker_results = self._run_ticker(questions)
        market_context = self._market_context(trades, marks)

        summary = self._summarize(trade_results, pricing_results)
        narrative = self._narrative(summary)

        return {
            "scenario": {"name": data.get("name"), "description": data.get("description")},
            "data_quality": data_quality,
            "trade_issues": trade_results,
            "pricing_flags": pricing_results.get("enriched_marks", []),
            "market_context": market_context,
            "ticker_agent_results": ticker_results,
            "narrative": narrative,
            "summary": summary,
        }

    def _normalize_trades(self, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        results = []
        issues = []
        for item in items:
            ticker = item.get("ticker")
            if not ticker:
                continue
            try:
                matches = self.normalizer.normalize(ticker, top_k=1)
                if matches:
                    match = matches[0]
                    results.append({"input": ticker, "normalized": match.equity.symbol, "confidence": match.confidence})
                    if match.ambiguous or match.confidence < 0.9:
                        issues.append({"ticker": ticker, "issue": "ambiguous_or_low_confidence"})
                else:
                    issues.append({"ticker": ticker, "issue": "unknown"})
            except Exception as exc:
                issues.append({"ticker": ticker, "issue": f"error: {exc}"})
        return {"ticker_normalizations": results, "normalization_issues": issues}

    def _run_trades(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for trade in trades:
            res = self.oms_agent.run(trade)
            res["trade"] = trade
            results.append(res)
        return results

    def _run_pricing(self, marks: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not marks:
            return {"enriched_marks": [], "summary": {}}
        try:
            return self.pricing_agent.run(marks)
        except Exception as exc:
            return {"enriched_marks": [], "summary": {}, "error": str(exc)}

    def _run_ticker(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for q in questions:
            question = q if isinstance(q, str) else q.get("question")
            if not question:
                continue
            try:
                results.append(ticker_agent.run(question))
            except Exception as exc:
                results.append({"question": question, "error": str(exc)})
        return results

    def _market_context(self, trades: List[Dict[str, Any]], marks: List[Dict[str, Any]]) -> Dict[str, Any]:
        tickers = {t.get("ticker") for t in trades if t.get("ticker")} | {m.get("ticker") for m in marks if m.get("ticker")}
        snapshots = []
        for tkr in tickers:
            try:
                snap = get_equity_snapshot(tkr)
                snapshots.append(snap.model_dump())
            except Exception:
                continue
        return {"key_tickers": list(tickers), "snapshots": snapshots}

    def _summarize(self, trade_results: List[Dict[str, Any]], pricing_results: Dict[str, Any]) -> Dict[str, Any]:
        total_trades = len(trade_results)
        trades_with_issues = sum(1 for r in trade_results if r.get("status") != "OK")
        enriched = pricing_results.get("enriched_marks", [])
        total_marks = len(enriched)
        marks_flagged = sum(1 for m in enriched if m.get("classification") != "OK")
        overall_status = "OK"
        if trades_with_issues or marks_flagged:
            overall_status = "WARNING"
        if any(r.get("status") == "ERROR" for r in trade_results) or any(
            m.get("classification") in {"OUT_OF_TOLERANCE", "NO_MARKET_DATA"} for m in enriched
        ):
            overall_status = "ERROR"
        return {
            "total_trades": total_trades,
            "trades_with_issues": trades_with_issues,
            "total_marks": total_marks,
            "marks_flagged": marks_flagged,
            "overall_status": overall_status,
        }

    def _narrative(self, summary: Dict[str, Any]) -> str:
        return (
            f"Processed {summary.get('total_trades',0)} trades with {summary.get('trades_with_issues',0)} issues; "
            f"processed {summary.get('total_marks',0)} marks with {summary.get('marks_flagged',0)} flagged; "
            f"overall status {summary.get('overall_status')}."
        )
