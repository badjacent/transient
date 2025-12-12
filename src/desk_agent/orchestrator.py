"""Desk agent orchestrator that chains refmaster, OMS, pricing, ticker agent, and market context."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
import os

import yaml
from src.desk_agent.config import load_config
from src.refmaster import NormalizerAgent
from src.oms import OMSAgent
from src.pricing import PricingAgent
from src.ticker_agent import ticker_agent
from src.data_tools.fd_api import get_equity_snapshot
from src.data_tools.schemas import PriceSnapshot

logger = logging.getLogger(__name__)


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
        self.retry_cfg = {
            "max": self.config.get("retry_max", 2),
            "backoff_ms": self.config.get("retry_backoff_ms", 500),
            "abort_after_retry": self.config.get("abort_after_retry", True),
        }
        self.log_inputs = bool(int(os.getenv("DESK_AGENT_LOG_INPUTS", "1")))

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
        trace: List[Dict[str, Any]] = []
        data = self.load_scenario(scenario)
        validation_errors = self._validate_scenario(data)
        if validation_errors:
            raise ValueError(f"Scenario validation errors: {validation_errors}")
        trades = data.get("trades", [])
        marks = data.get("marks", [])
        questions = data.get("questions", [])

        data_quality = self._step("normalize", self._normalize_trades, trace, trades + marks + questions)
        trade_results = self._step("trade_qa", self._run_trades, trace, trades)
        pricing_results = self._step("pricing", self._run_pricing, trace, marks)
        ticker_results = self._step("ticker", self._run_ticker, trace, questions)
        market_context = self._step("market_context", self._market_context, trace, trades, marks)

        summary = self._summarize(trade_results, pricing_results)
        narrative = self._narrative(summary)
        return self._assemble_report(
            data, data_quality, trade_results, pricing_results, market_context, ticker_results, narrative, summary, trace
        )

    def _step(self, name: str, fn, trace: List[Dict[str, Any]], *args):
        start = time.perf_counter()
        try:
            result = fn(*args)
            trace.append({"step": name, "status": "OK", "duration_ms": (time.perf_counter() - start) * 1000})
            return result
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            trace.append({"step": name, "status": "ERROR", "error": str(exc), "duration_ms": duration_ms})
            if self.retry_cfg.get("abort_after_retry", True):
                raise
            return {}

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
                    results.append(
                        {"input": ticker, "normalized": match.equity.symbol, "confidence": match.confidence}
                    )
                    if match.ambiguous or match.confidence < 0.9:
                        issues.append({"ticker": ticker, "issue": "ambiguous_or_low_confidence"})
                else:
                    issues.append({"ticker": ticker, "issue": "unknown"})
            except Exception as exc:
                issues.append({"ticker": ticker, "issue": f"error: {exc}"})
            if self.log_inputs:
                logger.info("normalize input=%s result=%s", ticker, results[-1] if results else "none")
        logger.info("normalize completed count=%d issues=%d", len(results), len(issues))
        return {"ticker_normalizations": results, "normalization_issues": issues}

    def _run_trades(self, trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        if not trades:
            logger.info("no trades provided; skipping OMS")
            return results
        for trade in trades:
            try:
                res = self.oms_agent.run(trade)
            except Exception as exc:
                res = {"status": "ERROR", "issues": [{"type": "trade_validation", "severity": "ERROR", "message": str(exc), "field": "*"}], "explanation": str(exc)}
            res["trade"] = trade
            results.append(res)
        return results

    def _run_pricing(self, marks: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not marks:
            logger.info("no marks provided; skipping pricing")
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
                results.append({"question": question, "error": str(exc), "intent": "error"})
        return results

    def _market_context(self, trades: List[Dict[str, Any]], marks: List[Dict[str, Any]]) -> Dict[str, Any]:
        tickers = {t.get("ticker") for t in trades if t.get("ticker")} | {m.get("ticker") for m in marks if m.get("ticker")}
        snapshots = []
        for tkr in tickers:
            try:
                snap = get_equity_snapshot(tkr)
                snapshots.append(snap.model_dump())
            except Exception as exc:
                logger.warning("market context snapshot failed for %s: %s", tkr, exc)
        return {
            "key_tickers": list(tickers),
            "snapshots": snapshots,
            "market_movements": {},
            "sector_performance": {},
        }

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

    def _validate_scenario(self, scenario: Dict[str, Any]) -> List[str]:
        errors = []
        required_top = ["name", "description", "trades", "marks", "questions"]
        for key in required_top:
            if key not in scenario:
                errors.append(f"missing {key}")
        errors.extend(
            self._validate_items(
                "trades",
                scenario.get("trades", []),
                required=["ticker", "quantity", "price", "currency", "counterparty", "trade_dt", "settle_dt"],
            )
        )
        errors.extend(
            self._validate_items("marks", scenario.get("marks", []), required=["ticker", "internal_mark", "as_of_date"])
        )
        errors.extend(self._validate_items("questions", scenario.get("questions", []), required=["question"]))
        return errors

    def _validate_items(self, kind: str, items: List[Dict[str, Any]], required: List[str]) -> List[str]:
        errs: List[str] = []
        for idx, item in enumerate(items):
            for field in required:
                if field not in item:
                    errs.append(f"{kind}[{idx}] missing {field}")
        return errs

    def _assemble_report(
        self,
        data,
        data_quality,
        trade_results,
        pricing_results,
        market_context,
        ticker_results,
        narrative,
        summary,
        trace,
    ) -> Dict[str, Any]:
        return {
            "scenario": {**{k: data.get(k) for k in ("name", "description")}, "metadata": data.get("metadata", {})},
            "data_quality": data_quality,
            "trade_issues": trade_results,
            "pricing_flags": pricing_results.get("enriched_marks", []),
            "market_context": market_context,
            "ticker_agent_results": ticker_results,
            "narrative": narrative,
            "summary": summary,
            "execution_metadata": {"trace": trace},
        }

    def generate_report(self, result: Dict[str, Any], output_path: str | None = None) -> Dict[str, Any]:
        """Return report dict; optionally write prettified JSON."""
        report = result
        if output_path:
            Path(output_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
