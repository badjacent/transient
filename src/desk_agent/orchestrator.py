"""Desk agent orchestrator that chains refmaster, OMS, pricing, ticker agent, and market context."""

from __future__ import annotations

import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml
from src.desk_agent.config import load_config
from src.refmaster import NormalizerAgent
from src.oms import OMSAgent
from src.pricing import PricingAgent
from src.ticker_agent import ticker_agent
from src.data_tools.fd_api import get_equity_snapshot
logger = logging.getLogger(__name__)

SCENARIO_SCHEMA = {
    "name": str,
    "description": str,
    "trades": list,
    "marks": list,
    "questions": list,
    "metadata": dict,
}

TRADE_SCHEMA = {
    "trade_id": str,
    "ticker": str,
    "quantity": (int, float),
    "price": (int, float),
    "currency": str,
    "counterparty": str,
    "trade_dt": str,
    "settle_dt": str,
    "side": str,
}

MARK_SCHEMA = {
    "ticker": str,
    "internal_mark": (int, float),
    "as_of": str,
    "as_of_date": str,
    "source": str,
    "notes": str,
}

QUESTION_SCHEMA = {
    "question": str,
    "ticker": str,
    "intent_hint": str,
    "context": dict,
}


class DeskAgentOrchestrator:
    """Runs a scenario end-to-end and aggregates results."""

    def __init__(
        self,
        config_path: str | None = None,
        normalizer: NormalizerAgent | None = None,
        oms_agent: OMSAgent | None = None,
        pricing_agent: PricingAgent | None = None,
        ticker_runner=None,
    ) -> None:
        self.config = load_config(config_path)
        log_level = getattr(logging, str(self.config.get("log_level", "INFO")).upper(), logging.INFO)
        Path(self.config["logs_path"]).mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=log_level,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(Path(self.config["logs_path"]) / "desk_agent.log"),
            ],
            force=True,
        )
        self.normalizer = normalizer or NormalizerAgent()
        self.oms_agent = oms_agent or OMSAgent()
        self.pricing_agent = pricing_agent or PricingAgent()
        self.ticker_runner = ticker_runner or ticker_agent.run
        if not callable(self.ticker_runner):
            raise ImportError("Ticker agent runner is not available; ensure ticker_agent dependency is installed.")
        self.ticker_config = {
            "model": self.config.get("ticker_agent_model"),
            "intents_path": self.config.get("ticker_agent_intents"),
        }
        self.retry_cfg = {
            "max": self.config.get("retry_max", 2),
            "backoff_ms": self.config.get("retry_backoff_ms", 500),
            "abort_after_retry": self.config.get("abort_after_retry", False),
        }
        self.log_inputs = bool(int(os.getenv("DESK_AGENT_LOG_INPUTS", "1")))
        self.parallel_ticker = bool(self.config.get("parallel_ticker"))

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

    def validate_all_scenarios(self) -> Dict[str, List[str]]:
        """Validate every scenario file under the configured path."""
        scenarios_dir = Path(self.config["scenarios_path"])
        errors: Dict[str, List[str]] = {}
        if not scenarios_dir.exists():
            raise FileNotFoundError(f"scenarios path not found: {scenarios_dir}")
        for file in scenarios_dir.iterdir():
            if file.suffix.lower() not in {".json", ".yaml", ".yml"}:
                continue
            try:
                scenario = self.load_scenario(file)
                errs = self._validate_scenario(scenario)
                if errs:
                    errors[file.name] = errs
            except Exception as exc:
                errors[file.name] = [str(exc)]
        return errors

    def smoke_all_scenarios(self) -> Dict[str, Any]:
        """Run all scenarios sequentially and return a reliability summary."""
        scenarios_dir = Path(self.config["scenarios_path"])
        if not scenarios_dir.exists():
            raise FileNotFoundError(f"scenarios path not found: {scenarios_dir}")
        summaries: List[Dict[str, Any]] = []
        start = time.perf_counter()
        for file in scenarios_dir.iterdir():
            if file.suffix.lower() not in {".json", ".yaml", ".yml"}:
                continue
            scenario = self.load_scenario(file)
            scenario_name = scenario.get("name", file.name)
            try:
                res = self.run_scenario(scenario)
                status = res.get("summary", {}).get("overall_status", "UNKNOWN")
                summaries.append({"scenario": scenario_name, "status": status, "duration_ms": res.get("execution_metadata", {}).get("execution_time_ms")})
            except Exception as exc:
                summaries.append({"scenario": scenario_name, "status": "ERROR", "error": str(exc)})
        total_ms = (time.perf_counter() - start) * 1000
        failures = [s for s in summaries if s.get("status") == "ERROR"]
        warnings = [s for s in summaries if s.get("status") == "WARNING"]
        return {
            "scenarios_ran": len(summaries),
            "errors": len(failures),
            "warnings": len(warnings),
            "total_ms": total_ms,
            "details": summaries,
        }

    def run_scenario(self, scenario: str | Dict[str, Any]) -> Dict[str, Any]:
        trace: List[Dict[str, Any]] = []
        data = self.load_scenario(scenario)
        scenario_name = data.get("name")
        logger.info("desk_agent scenario_start name=%s", scenario_name)
        validation_errors = self._validate_scenario(data)
        if validation_errors:
            raise ValueError(f"Scenario validation errors: {validation_errors}")
        trades = data.get("trades", [])
        marks = data.get("marks", [])
        questions = data.get("questions", [])

        data_quality = self._step("normalize", self._normalize_trades, trace, trades, marks, questions, scenario_name=scenario_name)
        trade_results = self._step("trade_qa", self._run_trades, trace, trades, scenario_name=scenario_name)
        pricing_results = self._step("pricing", self._run_pricing, trace, marks, scenario_name=scenario_name)
        ticker_results = self._step("ticker", self._run_ticker, trace, questions, scenario_name=scenario_name)
        market_context = self._step("market_context", self._market_context, trace, trades, marks, scenario_name=scenario_name)

        summary = self._summarize(trade_results, pricing_results)
        narrative = self._narrative(summary, trade_results, pricing_results, data_quality)
        report = self._assemble_report(
            data, data_quality, trade_results, pricing_results, market_context, ticker_results, narrative, summary, trace
        )
        logger.info(
            "desk_agent scenario_complete name=%s status=%s total_trades=%s total_marks=%s duration_ms=%.2f",
            scenario_name,
            summary.get("overall_status"),
            summary.get("total_trades"),
            summary.get("total_marks"),
            report["execution_metadata"].get("execution_time_ms"),
        )
        return report

    def _step(self, name: str, fn, trace: List[Dict[str, Any]], *args, scenario_name: str | None = None):
        attempts = 0
        last_exc: Exception | None = None
        start = time.perf_counter()
        while attempts <= self.retry_cfg.get("max", 2):
            attempts += 1
            try:
                result = fn(*args)
                duration_ms = (time.perf_counter() - start) * 1000
                trace.append({"step": name, "status": "OK", "duration_ms": duration_ms, "attempts": attempts})
                if duration_ms > 2000:
                    logger.warning("%s slow_step scenario=%s duration_ms=%.2f", name, scenario_name, duration_ms)
                else:
                    logger.info("%s completed scenario=%s duration_ms=%.2f", name, scenario_name, duration_ms)
                return result
            except Exception as exc:
                last_exc = exc
                duration_ms = (time.perf_counter() - start) * 1000
                trace.append({"step": name, "status": "ERROR", "error": str(exc), "duration_ms": duration_ms, "attempts": attempts})
                logger.error("%s failed attempt=%d: %s", name, attempts, exc)
                if attempts > self.retry_cfg.get("max", 2) and self.retry_cfg.get("abort_after_retry", False):
                    break
                time.sleep(self.retry_cfg.get("backoff_ms", 500) / 1000)
        logger.warning("%s returning empty result after failures: %s", name, last_exc)
        return {"error": str(last_exc) if last_exc else "unknown_error"}

    def _normalize_trades(self, trades: List[Dict[str, Any]], marks: List[Dict[str, Any]], questions: List[Dict[str, Any]]) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        issues: List[Dict[str, Any]] = []
        confidence_scores: Dict[str, float] = {}
        items = []
        items.extend(trades or [])
        items.extend(marks or [])
        items.extend(questions or [])
        for item in items:
            ticker = item.get("ticker") or item.get("question")  # question may encode ticker text
            if not ticker:
                continue
            try:
                matches = self.normalizer.normalize(ticker, top_k=1)
                if matches:
                    match = matches[0]
                    rec = {"input": ticker, "normalized": match.equity.symbol, "confidence": match.confidence, "ambiguous": match.ambiguous}
                    results.append(rec)
                    confidence_scores[match.equity.symbol] = match.confidence
                    if match.ambiguous or match.confidence < 0.9:
                        issues.append({"ticker": ticker, "issue": "ambiguous_or_low_confidence"})
                else:
                    issues.append({"ticker": ticker, "issue": "unknown"})
            except Exception as exc:
                issues.append({"ticker": ticker, "issue": f"error: {exc}"})
            if self.log_inputs:
                logger.info("normalize input=%s result=%s", ticker, results[-1] if results else "none")
        logger.info("normalize completed count=%d issues=%d", len(results), len(issues))
        return {"ticker_normalizations": results, "normalization_issues": issues, "confidence_scores": confidence_scores}

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
        normalized_marks = []
        for mark in marks:
            if "as_of" in mark and "as_of_date" not in mark:
                mark = {**mark, "as_of_date": mark["as_of"]}
            normalized_marks.append(mark)
        return self.pricing_agent.run(normalized_marks)

    def _run_ticker(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        queue: List[str] = []
        for q in questions:
            question = q if isinstance(q, str) else q.get("question")
            if question:
                queue.append(question)
        if self.parallel_ticker and queue:
            with ThreadPoolExecutor(max_workers=min(4, len(queue))) as pool:
                future_map = {pool.submit(self.ticker_runner, q): q for q in queue}
                for fut in as_completed(future_map):
                    question = future_map[fut]
                    try:
                        answer = fut.result()
                        if isinstance(answer, dict) and "question" not in answer:
                            answer = {**answer, "question": question}
                        results.append(answer)
                    except Exception as exc:
                        results.append({"question": question, "error": str(exc), "intent": "error"})
        else:
            for question in queue:
                try:
                    answer = self.ticker_runner(question)
                    if isinstance(answer, dict) and "question" not in answer:
                        answer = {**answer, "question": question}
                    results.append(answer)
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
        sector_perf: Dict[str, Dict[str, Any]] = {}
        market_movements: Dict[str, Any] = {}
        if snapshots:
            sectors: Dict[str, List[float]] = {}
            for snap in snapshots:
                sector = snap.get("sector") or "UNKNOWN"
                sectors.setdefault(sector, []).append(snap.get("return_1d", 1.0))
            for sec, rets in sectors.items():
                sector_perf[sec] = {"avg_return_1d": sum(rets) / len(rets), "count": len(rets)}
            market_movements = {
                "avg_return_1d": sum(s.get("return_1d", 1.0) for s in snapshots) / len(snapshots),
                "avg_return_5d": sum(s.get("return_5d", 1.0) for s in snapshots) / len(snapshots),
            }
        else:
            logger.info("market context unavailable for tickers=%s", tickers)
        return {
            "key_tickers": list(tickers),
            "snapshots": snapshots,
            "market_movements": market_movements,
            "sector_performance": sector_perf,
            "as_of_date": datetime.utcnow().strftime("%Y-%m-%d"),
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
        issue_breakdown: Dict[str, int] = {}
        severity_breakdown: Dict[str, int] = {}
        counterparty_breakdown: Dict[str, int] = {}
        ticker_breakdown: Dict[str, int] = {}
        for tr in trade_results:
            trade = tr.get("trade", {})
            ticker = trade.get("ticker")
            cp = trade.get("counterparty")
            for issue in tr.get("issues", []):
                issue_breakdown[issue.get("type")] = issue_breakdown.get(issue.get("type"), 0) + 1
                severity_breakdown[issue.get("severity")] = severity_breakdown.get(issue.get("severity"), 0) + 1
                if cp:
                    counterparty_breakdown[cp] = counterparty_breakdown.get(cp, 0) + 1
                if ticker:
                    ticker_breakdown[ticker] = ticker_breakdown.get(ticker, 0) + 1
        # Performance budget check
        perf_budget_ms = self.config.get("performance_budget_ms", 30000)
        return {
            "total_trades": total_trades,
            "trades_with_issues": trades_with_issues,
            "total_marks": total_marks,
            "marks_flagged": marks_flagged,
            "percent_trades_with_issues": (trades_with_issues / total_trades * 100) if total_trades else 0.0,
            "percent_marks_flagged": (marks_flagged / total_marks * 100) if total_marks else 0.0,
            "overall_status": overall_status,
            "issue_breakdown": issue_breakdown,
            "severity_breakdown": severity_breakdown,
            "counterparty_breakdown": counterparty_breakdown,
            "ticker_breakdown": ticker_breakdown,
            "performance_budget_ms": perf_budget_ms,
        }

    def _narrative(
        self,
        summary: Dict[str, Any],
        trade_results: List[Dict[str, Any]],
        pricing_results: Dict[str, Any],
        data_quality: Dict[str, Any],
    ) -> str:
        total_trades = summary.get("total_trades", 0)
        trade_errors = summary.get("issue_breakdown", {}).get("settlement_date", 0) + summary.get(
            "issue_breakdown", {}
        ).get("identifier_mismatch", 0)
        marks_flagged = summary.get("marks_flagged", 0)
        perf_ok = summary.get("performance_budget_ms", 30000)
        # Highlight top issues
        top_issue = None
        if summary.get("issue_breakdown"):
            top_issue = max(summary["issue_breakdown"], key=summary["issue_breakdown"].get)
        dq_issues = len(data_quality.get("normalization_issues", []))
        narrative_parts = [
            f"Processed {total_trades} trade(s) and {summary.get('total_marks',0)} mark(s); overall status {summary.get('overall_status')}.",
            f"Issues: trades_with_issues={summary.get('trades_with_issues',0)}, marks_flagged={marks_flagged}, dq_issues={dq_issues}.",
        ]
        if top_issue:
            narrative_parts.append(f"Top issue type: {top_issue}.")
        if summary.get("issue_breakdown"):
            narrative_parts.append(f"Severities: {summary.get('severity_breakdown',{})}.")
        narrative_parts.append(f"Performance budget(ms): {perf_ok}; check execution_metadata for timings.")
        return " ".join(narrative_parts)

    def _validate_scenario(self, scenario: Dict[str, Any]) -> List[str]:
        errors = []
        for field, ftype in SCENARIO_SCHEMA.items():
            if field not in scenario:
                errors.append(f"missing {field}")
            elif ftype and not isinstance(scenario[field], ftype):
                errors.append(f"{field} must be {ftype}")
        errors.extend(
            self._validate_items(
                "trades",
                scenario.get("trades", []),
                required=["ticker", "quantity", "price", "currency", "counterparty", "trade_dt", "settle_dt"],
                schema=TRADE_SCHEMA,
            )
        )
        errors.extend(
            self._validate_items(
                "marks",
                scenario.get("marks", []),
                required=["ticker", "internal_mark"],
                schema=MARK_SCHEMA,
                date_keys=("as_of", "as_of_date"),
            )
        )
        errors.extend(
            self._validate_items("questions", scenario.get("questions", []), required=["question"], schema=QUESTION_SCHEMA)
        )
        return errors

    def _validate_items(
        self,
        kind: str,
        items: List[Dict[str, Any]],
        required: List[str],
        schema: Dict[str, Any],
        date_keys: Tuple[str, ...] | None = None,
    ) -> List[str]:
        errs: List[str] = []
        for idx, item in enumerate(items):
            for field in required:
                if field not in item:
                    errs.append(f"{kind}[{idx}] missing {field}")
            if date_keys and not any(k in item for k in date_keys):
                errs.append(f"{kind}[{idx}] missing one of {date_keys}")
            for field, ftype in schema.items():
                if field in item and ftype and not isinstance(item[field], ftype):
                    errs.append(f"{kind}[{idx}] field {field} must be {ftype}")
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
        timestamp = datetime.utcnow().isoformat()
        trade_issues = []
        for idx, tr in enumerate(trade_results):
            trade_payload = tr.get("trade", {})
            trade_issues.append(
                {
                    "trade_id": trade_payload.get("trade_id") or f"trade_{idx+1}",
                    "status": tr.get("status"),
                    "issues": tr.get("issues", []),
                    "ticker": trade_payload.get("ticker"),
                    "counterparty": trade_payload.get("counterparty"),
                }
            )
        pricing_flags = []
        for mark in pricing_results.get("enriched_marks", []):
            pricing_flags.append(
                {
                    "ticker": mark.get("ticker"),
                    "internal_mark": mark.get("internal_mark"),
                    "market_price": mark.get("market_price"),
                    "deviation": mark.get("deviation_percentage"),
                    "classification": mark.get("classification"),
                    "explanation": mark.get("explanation"),
                }
            )

        return {
            "scenario": {
                "name": data.get("name"),
                "description": data.get("description"),
                "metadata": data.get("metadata", {}),
                "execution_date": timestamp,
            },
            "data_quality": data_quality,
            "trade_issues": trade_issues,
            "pricing_flags": pricing_flags,
            "market_context": market_context,
            "ticker_agent_results": ticker_results,
            "narrative": narrative,
            "summary": summary,
            "execution_metadata": {
                "execution_time_ms": sum(t.get("duration_ms", 0) for t in trace),
                "timestamp": timestamp,
                "agents_executed": ["refmaster", "oms", "pricing", "ticker_agent", "market_context"],
                "trace": trace,
                "config": {
                    "retry_max": self.retry_cfg.get("max"),
                    "retry_backoff_ms": self.retry_cfg.get("backoff_ms"),
                    "abort_after_retry": self.retry_cfg.get("abort_after_retry"),
                },
                "errors": [t for t in trace if t.get("status") == "ERROR"],
            },
        }

    def generate_report(self, result: Dict[str, Any], output_path: str | None = None) -> Dict[str, Any]:
        """Return report dict; optionally write prettified JSON."""
        report = result
        if output_path:
            Path(output_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
