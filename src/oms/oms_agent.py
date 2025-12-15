"""Trade QA agent for OMS."""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import ValidationError

from src.data_tools.fd_api import get_price_snapshot
from src.oms.schema import Trade
from src.refmaster import NormalizerAgent
from src.refmaster.schema import NormalizationResult


DEFAULT_THRESHOLDS = {"warning": 0.02, "error": 0.05}
DEFAULT_COUNTERPARTIES = {"MS", "GS", "JPM", "BAML", "BARC", "CITI"}
logger = logging.getLogger(__name__)


def _issue(issue_type: str, severity: str, message: str, field: str) -> Dict[str, Any]:
    return {"type": issue_type, "severity": severity, "message": message, "field": field}


class OMSAgent:
    """Validates trades with reference data and market checks."""

    def __init__(
        self,
        normalizer: Optional[NormalizerAgent] = None,
        thresholds: Optional[Dict[str, float]] = None,
        valid_counterparties: Optional[set[str]] = None,
        ref_currency_map: Optional[Dict[str, str]] = None,
        settlement_days: Optional[int] = None,
    ) -> None:
        self.normalizer = normalizer or NormalizerAgent()
        env_thresholds = {
            "warning": float(os.getenv("OMS_PRICE_WARNING_THRESHOLD", DEFAULT_THRESHOLDS["warning"])),
            "error": float(os.getenv("OMS_PRICE_ERROR_THRESHOLD", DEFAULT_THRESHOLDS["error"])),
        }
        self.thresholds = {**DEFAULT_THRESHOLDS, **env_thresholds, **(thresholds or {})}
        env_counterparties = os.getenv("OMS_COUNTERPARTIES")
        env_set = {c.strip().upper() for c in env_counterparties.split(",")} if env_counterparties else None
        self.valid_counterparties = valid_counterparties or env_set or DEFAULT_COUNTERPARTIES
        self.ref_currency_map = ref_currency_map or {}
        self.settlement_days = settlement_days or int(os.getenv("OMS_SETTLEMENT_DAYS", 2))
        self.audit_log_path = os.getenv("OMS_AUDIT_LOG")
        self.performance_budget_ms = int(os.getenv("OMS_PERF_BUDGET_MS", 30000))

    def run(self, trade_json: Any) -> Dict[str, Any]:
        trade_dict, parse_issues = self._coerce_trade_dict(trade_json)
        issues: List[Dict[str, Any]] = []
        issues.extend(self._check_required(trade_dict))
        issues.extend(parse_issues)
        timing: Dict[str, float] = {}
        start_time = time.perf_counter()

        trade: Optional[Trade] = None
        try:
            trade_start = time.perf_counter()
            trade = self._parse_trade(trade_dict)
            timing["schema_validation_ms"] = (time.perf_counter() - trade_start) * 1000
        except ValidationError as exc:
            issues.extend(self._validation_issues(exc))
        except Exception as exc:  # Catch data_tools or json parsing errors
            issues.append(_issue("schema_validation", "ERROR", f"Invalid trade input: {exc}", "trade"))

        if trade:
            checks = [
                ("identifier", self._check_identifier),
                ("currency", self._check_currency),
                ("price", self._check_price),
                ("counterparty", self._check_counterparty),
                ("settlement", self._check_settlement),
            ]
            for name, fn in checks:
                step_start = time.perf_counter()
                issues.extend(fn(trade))
                timing[f"{name}_ms"] = (time.perf_counter() - step_start) * 1000

        status = self._status(issues)
        explanation = self._explain(status, issues)
        severity_counts = _count_by(issues, "severity")
        type_counts = _count_by(issues, "type")
        logger.info(
            "oms_agent status=%s issues=%d ticker=%s", status, len(issues), trade_dict.get("ticker")
        )
        timing["total_ms"] = (time.perf_counter() - start_time) * 1000
        result = {
            "status": status,
            "issues": issues,
            "explanation": explanation,
            "metrics": {**timing, "severity_counts": severity_counts, "issue_counts": type_counts},
        }
        self._audit(trade_dict, result)
        return result

    def _audit(self, trade_dict: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Write validation audit log as JSONL when OMS_AUDIT_LOG is set."""
        if not self.audit_log_path:
            return
        try:
            path = Path(self.audit_log_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "ts_ms": int(time.time() * 1000),
                "trade": trade_dict,
                "result": {k: v for k, v in result.items() if k != "explanation"},
            }
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception as exc:
            logger.warning("audit log write failed: %s", exc)

    def run_batch(self, trades: List[Any]) -> Dict[str, Any]:
        """Validate a batch of trades and return aggregate results with timing."""
        batch_start = time.perf_counter()
        results: List[Dict[str, Any]] = []
        for trade in trades:
            results.append(self.run(trade))
        batch_ms = (time.perf_counter() - batch_start) * 1000
        errors = sum(1 for r in results if r.get("status") == "ERROR")
        warnings = sum(1 for r in results if r.get("status") == "WARNING")
        return {
            "results": results,
            "summary": {
                "total": len(results),
                "errors": errors,
                "warnings": warnings,
                "ok": len(results) - errors - warnings,
                "total_ms": batch_ms,
                "within_budget": batch_ms <= self._batch_budget_ms(),
            },
        }

    def evaluate_scenarios(self, scenarios: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Evaluate scenarios against expected_status/expected_issues fields."""
        results = []
        for scenario in scenarios:
            name = scenario.get("name", "unknown")
            expected_status = scenario.get("expected_status")
            expected_issues = scenario.get("expected_issues", [])
            res = self.run(scenario["trade"])
            pass_status = res["status"] == expected_status if expected_status else True
            missing = []
            for expected in expected_issues:
                match = [
                    i
                    for i in res["issues"]
                    if i["type"] == expected["type"] and i["severity"] == expected["severity"]
                ]
                if not match:
                    missing.append(expected)
            results.append({"name": name, "status": res["status"], "pass_status": pass_status, "missing_issues": missing})
        pass_count = sum(1 for r in results if r["pass_status"] and not r["missing_issues"])
        return {"results": results, "pass_rate": pass_count / len(results) if results else 0.0}

    def _coerce_trade_dict(self, trade_json: Any) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Accept dict/JSON string or data_tools Trade; return dict plus any coercion issues."""
        issues: List[Dict[str, Any]] = []
        raw = trade_json
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError as exc:
                issues.append(_issue("schema_validation", "ERROR", f"Invalid JSON: {exc}", "trade"))
                return {}, issues
        try:
            from src.data_tools.schemas import Trade as DataTrade  # type: ignore
        except Exception:
            DataTrade = None
        if DataTrade and isinstance(raw, DataTrade):
            raw = raw.model_dump()
        if not isinstance(raw, dict):
            issues.append(_issue("schema_validation", "ERROR", "trade_json must be dict or JSON string", "trade"))
            return {}, issues
        return raw, issues

    def _parse_trade(self, trade_json: Dict[str, Any]) -> Trade:
        return Trade(**trade_json)

    def _validation_issues(self, exc: ValidationError) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        for err in exc.errors():
            field = ".".join(str(loc) for loc in err.get("loc", ()))
            issues.append(
                _issue(
                    "schema_validation",
                    "ERROR",
                    err.get("msg", "Invalid value"),
                    field or "trade",
                )
            )
        return issues

    def _check_required(self, trade_json: Any) -> List[Dict[str, Any]]:
        required = ["ticker", "quantity", "price", "currency", "counterparty", "trade_dt", "settle_dt"]
        issues: List[Dict[str, Any]] = []
        for field in required:
            if field not in trade_json or trade_json[field] in (None, ""):
                issues.append(_issue("missing_field", "ERROR", f"Missing {field}", field))
        return issues

    def _check_identifier(self, trade: Trade) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        try:
            results = self.normalizer.normalize(trade.ticker, top_k=3)
        except Exception as exc:
            issues.append(_issue("identifier_mismatch", "ERROR", f"Normalization failed: {exc}", "ticker"))
            return issues
        if not results:
            issues.append(_issue("identifier_mismatch", "ERROR", "Ticker not recognized", "ticker"))
            return issues
        top: NormalizationResult = results[0]
        logger.debug("identifier check ticker=%s top_conf=%.2f ambiguous=%s", trade.ticker, top.confidence, top.ambiguous)
        if top.ambiguous:
            issues.append(_issue("identifier_mismatch", "WARNING", "Ticker ambiguous", "ticker"))
        if top.confidence < 0.9:
            issues.append(_issue("identifier_mismatch", "WARNING", "Low-confidence match", "ticker"))
        return issues

    def _check_currency(self, trade: Trade) -> List[Dict[str, Any]]:
        ref_ccy = self.ref_currency_map.get(trade.ticker, "USD")
        if trade.currency != ref_ccy:
            return [_issue("currency_mismatch", "WARNING", f"Currency {trade.currency} vs ref {ref_ccy}", "currency")]
        return []

    def _check_price(self, trade: Trade) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        try:
            snap = get_price_snapshot(trade.ticker, trade._parse_date(trade.trade_dt))
        except Exception as exc:
            issues.append(_issue("price_tolerance", "WARNING", f"Market data unavailable: {exc}", "price"))
            return issues
        deviation_pct = abs(trade.price - snap.price) / snap.price if snap.price else 0
        logger.info(
            "price check ticker=%s trade_price=%s market=%s deviation_pct=%.4f",
            trade.ticker,
            trade.price,
            snap.price,
            deviation_pct,
        )
        if deviation_pct > self.thresholds["error"]:
            issues.append(
                _issue("price_tolerance", "ERROR", f"Price deviates {deviation_pct:.2%} from market", "price")
            )
        elif deviation_pct > self.thresholds["warning"]:
            issues.append(
                _issue("price_tolerance", "WARNING", f"Price deviates {deviation_pct:.2%} from market", "price")
            )
        return issues

    def _check_counterparty(self, trade: Trade) -> List[Dict[str, Any]]:
        if trade.counterparty and trade.counterparty.strip().upper() not in self.valid_counterparties:
            return [_issue("counterparty", "WARNING", "Counterparty not in approved list", "counterparty")]
        return []

    def _check_settlement(self, trade: Trade) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        trade_dt = trade._parse_date(trade.trade_dt)
        settle_dt = trade._parse_date(trade.settle_dt)
        if settle_dt < trade_dt:
            issues.append(_issue("settlement_date", "ERROR", "Settlement before trade date", "settle_dt"))
        if settle_dt.weekday() >= 5:
            issues.append(_issue("settlement_date", "ERROR", "Settlement on weekend", "settle_dt"))
        delta_days = (settle_dt - trade_dt).days
        if delta_days < self.settlement_days:
            issues.append(
                _issue(
                    "settlement_date",
                    "ERROR",
                    f"Settlement earlier than expected T+{self.settlement_days}",
                    "settle_dt",
                )
            )
        elif delta_days > self.settlement_days + 1:
            issues.append(
                _issue(
                    "settlement_date",
                    "WARNING",
                    f"Non-standard settlement interval T+{delta_days} (expected ~T+{self.settlement_days})",
                    "settle_dt",
                )
            )
        return issues

    def _status(self, issues: List[Dict[str, Any]]) -> str:
        """Overall status: ERROR if any errors, WARNING if warnings only, otherwise OK."""
        if any(i["severity"] == "ERROR" for i in issues):
            return "ERROR"
        if any(i["severity"] == "WARNING" for i in issues):
            return "WARNING"
        return "OK"

    def _explain(self, status: str, issues: List[Dict[str, Any]]) -> str:
        if not issues:
            return "All checks passed."
        parts = [f"{status}: {len(issues)} issue(s)."]
        for i in issues:
            parts.append(f"{i['severity']} {i['type']} on {i['field']}: {i['message']}")
        return " ".join(parts)


def _count_by(issues: List[Dict[str, Any]], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for i in issues:
        val = i.get(key)
        if val:
            counts[val] = counts.get(val, 0) + 1
    return counts
