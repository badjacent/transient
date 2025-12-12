"""Config loader for pricing tolerances and paths."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

load_dotenv()


DEFAULTS = {
    "ok_threshold": 0.02,
    "review_threshold": 0.05,
    "stale_days": 5,
    "retry_count": 0,
    "retry_backoff_ms": 200,
    "max_workers": 1,
}


def load_tolerances(path: str | None = None) -> Dict[str, Any]:
    """Load tolerance config from YAML with defaults."""
    cfg = dict(DEFAULTS)
    cfg_path = Path(path) if path else Path("config") / "tolerances.yaml"
    if cfg_path.exists():
        data = yaml.safe_load(cfg_path.read_text()) or {}
        if isinstance(data, dict):
            cfg.update({k: v for k, v in data.items() if v is not None})
    # allow env overrides
    cfg["ok_threshold"] = float(os.getenv("PRICING_OK_THRESHOLD", cfg["ok_threshold"]))
    cfg["review_threshold"] = float(os.getenv("PRICING_REVIEW_THRESHOLD", cfg["review_threshold"]))
    cfg["stale_days"] = int(os.getenv("PRICING_STALE_DAYS", cfg["stale_days"]))
    cfg["retry_count"] = int(os.getenv("PRICING_RETRY_COUNT", cfg["retry_count"]))
    cfg["retry_backoff_ms"] = int(os.getenv("PRICING_RETRY_BACKOFF_MS", cfg["retry_backoff_ms"]))
    cfg["max_workers"] = int(os.getenv("PRICING_MAX_WORKERS", cfg["max_workers"]))
    return cfg
