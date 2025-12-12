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
    return cfg
