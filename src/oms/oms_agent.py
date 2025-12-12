"""Trade QA agent for OMS."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.oms.schema import Trade
from src.refmaster import NormalizerAgent
from src.data_tools.fd_api import get_price_snapshot


DEFAULT_THRESHOLDS = {"warning": 0.02, "error": 0.05}
DEFAULT_COUNTERPARTIES = {"MS", "GS", "JPM", "BAML", "BARC", "CITI"}


def _issue(issue_type: str, severity: str, message: str, field: str) -> Dict[str, Any]:
    return {"type": issue_type, "severity": severity, "message": message, "field": field}


class OMSAgent:
    """Validates trades with reference data and market checks."""

    def __init__(
        self,
        normalizer: Optional[NormalizerAgent] = None,
        thresholds: Optional[Dict[str, float]] = None,
        valid_counterparties: Optional[set[str]] = None,
    ) -> None:
        self.normalizer = normalizer or NormalizerAgent()
        self.thresholds = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.valid_counterparties = valid_counterparties or DEFAULT_COUNTERPARTIES

    def run(self, trade_json: Any) -> Dict[str, Any]:
        trade = self._parse_trade(trade_json)
        issues: List[Dict[str, Any]] = []
        issues.extend(self._check_required(trade_json))
        issues.extend(self._check_identifier(trade))
        issues.extend(self._check_currency(trade))
        issues.extend(self._check_price(trade))
        issues.extend(self._check_counterparty(trade))
        issues.extend(self._check_settlement(trade))
        status = self._status(issues)
        explanation = self._explain(status, issues)
        return {"status": status, "issues": issues, "explanation": explanation}

    def _parse_trade(self, trade_json: Any) -> Trade:
        if isinstance(trade_json, str):
            trade_json = json.loads(trade_json)
        if not isinstance(trade_json, dict):
            raise ValueError("trade_json must be dict or JSON string")
        return Trade(**trade_json)

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
        top = results[0]
        if top.ambiguous:
            issues.append(_issue("identifier_mismatch", "WARNING", "Ticker ambiguous", "ticker"))
        if top.confidence < 0.9:
            issues.append(_issue("identifier_mismatch", "WARNING", "Low-confidence match", "ticker"))
        return issues

    def _check_currency(self, trade: Trade) -> List[Dict[str, Any]]:
        # Stub: assume USD reference; warn if not USD.
        if trade.currency != "USD":
            return [_issue("currency_mismatch", "WARNING", "Non-USD trade; reference currency unknown", "currency")]
        return []

    def _check_price(self, trade: Trade) -> List[Dict[str, Any]]:
        issues: List[Dict[str, Any]] = []
        try:
            snap = get_price_snapshot(trade.ticker, trade._parse_date(trade.trade_dt))
        except Exception as exc:
            issues.append(_issue("price_tolerance", "WARNING", f"Market data unavailable: {exc}", "price"))
            return issues
        deviation_pct = abs(trade.price - snap.price) / snap.price if snap.price else 0
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
        if trade.counterparty and trade.counterparty.upper() not in self.valid_counterparties:
            return [_issue("counterparty", "WARNING", "Counterparty not in approved list", "counterparty")]
        return []

    def _check_settlement(self, trade: Trade) -> List[Dict[str, Any]]:
        if not trade.settle_not_before_trade():
            return [_issue("settlement_date", "ERROR", "Settlement before trade date", "settle_dt")]
        return []

    def _status(self, issues: List[Dict[str, Any]]) -> str:
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
