"""Config loader for desk agent."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

load_dotenv()


DEFAULTS = {
    "scenarios_path": "scenarios",
    "logs_path": "logs",
    "log_level": "INFO",
    "retry_max": 2,
    "retry_backoff_ms": 500,
    "abort_after_retry": False,
    "refmaster_data_path": None,
    "oms_price_warning": None,
    "oms_price_error": None,
    "oms_counterparties": None,
    "settlement_days": None,
    "pricing_tolerance": None,
    "pricing_stale_days": None,
    "ticker_agent_model": None,
    "ticker_agent_intents": None,
    "parallel_ticker": False,
    "performance_budget_ms": 30000,
}


def load_config(path: str | None = None) -> Dict[str, Any]:
    cfg = dict(DEFAULTS)
    cfg_path = Path(path) if path else None
    if cfg_path and cfg_path.exists():
        data = yaml.safe_load(cfg_path.read_text()) or {}
        if isinstance(data, dict):
            cfg.update({k: v for k, v in data.items() if v is not None})
    cfg["scenarios_path"] = os.getenv("DESK_AGENT_SCENARIOS_PATH", cfg["scenarios_path"])
    cfg["logs_path"] = os.getenv("DESK_AGENT_LOG_PATH", cfg["logs_path"])
    cfg["log_level"] = os.getenv("DESK_AGENT_LOG_LEVEL", cfg["log_level"])
    cfg["retry_max"] = int(os.getenv("DESK_AGENT_MAX_RETRIES", cfg["retry_max"]))
    cfg["retry_backoff_ms"] = int(os.getenv("DESK_AGENT_BACKOFF_MS", cfg["retry_backoff_ms"]))
    cfg["abort_after_retry"] = str(os.getenv("DESK_AGENT_ABORT_AFTER_RETRY", cfg["abort_after_retry"])).lower() in (
        "1",
        "true",
        "yes",
    )
    cfg["refmaster_data_path"] = os.getenv("REFMASTER_DATA_PATH", cfg.get("refmaster_data_path"))
    cfg["oms_price_warning"] = _maybe_float(os.getenv("OMS_PRICE_WARNING_THRESHOLD", cfg.get("oms_price_warning")))
    cfg["oms_price_error"] = _maybe_float(os.getenv("OMS_PRICE_ERROR_THRESHOLD", cfg.get("oms_price_error")))
    cfg["oms_counterparties"] = os.getenv("OMS_COUNTERPARTIES", cfg.get("oms_counterparties"))
    cfg["settlement_days"] = _maybe_int(os.getenv("OMS_SETTLEMENT_DAYS", cfg.get("settlement_days")))
    cfg["pricing_tolerance"] = _maybe_float(os.getenv("PRICING_TOLERANCE", cfg.get("pricing_tolerance")))
    cfg["pricing_stale_days"] = _maybe_int(os.getenv("PRICING_STALE_DAYS", cfg.get("pricing_stale_days")))
    cfg["ticker_agent_model"] = os.getenv("TICKER_AGENT_MODEL", cfg.get("ticker_agent_model"))
    cfg["ticker_agent_intents"] = os.getenv("TICKER_AGENT_INTENTS", cfg.get("ticker_agent_intents"))
    cfg["parallel_ticker"] = str(os.getenv("DESK_AGENT_PARALLEL_TICKER", cfg.get("parallel_ticker"))).lower() in (
        "1",
        "true",
        "yes",
    )
    cfg["performance_budget_ms"] = _maybe_int(
        os.getenv("DESK_AGENT_PERF_BUDGET_MS", cfg.get("performance_budget_ms"))
    ) or DEFAULTS["performance_budget_ms"]
    return cfg


def _maybe_float(val: Any) -> float | None:
    try:
        return float(val) if val not in (None, "", "None") else None
    except Exception:
        return None


def _maybe_int(val: Any) -> int | None:
    try:
        return int(val) if val not in (None, "", "None") else None
    except Exception:
        return None
