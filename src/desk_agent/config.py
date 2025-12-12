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
    "retry_max": 2,
    "retry_backoff_ms": 500,
    "abort_after_retry": True,
}


def load_config(path: str | None = None) -> Dict[str, Any]:
    cfg = dict(DEFAULTS)
    cfg_path = Path(path) if path else None
    if cfg_path and cfg_path.exists():
        data = yaml.safe_load(cfg_path.read_text()) or {}
        if isinstance(data, dict):
            cfg.update({k: v for k, v in data.items() if v is not None})
    cfg["retry_max"] = int(os.getenv("DESK_AGENT_MAX_RETRIES", cfg["retry_max"]))
    cfg["retry_backoff_ms"] = int(os.getenv("DESK_AGENT_BACKOFF_MS", cfg["retry_backoff_ms"]))
    cfg["abort_after_retry"] = str(os.getenv("DESK_AGENT_ABORT_AFTER_RETRY", cfg["abort_after_retry"])).lower() in (
        "1",
        "true",
        "yes",
    )
    return cfg
