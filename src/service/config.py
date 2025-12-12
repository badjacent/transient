"""Service configuration loader."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import yaml
from dotenv import load_dotenv

load_dotenv()


DEFAULTS = {
    "env": "dev",
    "logs_path": "logs",
    "scenarios_path": "scenarios",
    "version": "dev",
}


def load_config(path: str | None = None) -> Dict[str, Any]:
    cfg = dict(DEFAULTS)
    if path:
        cfg_path = Path(path)
        if cfg_path.exists():
            data = yaml.safe_load(cfg_path.read_text()) or {}
            if isinstance(data, dict):
                cfg.update({k: v for k, v in data.items() if v is not None})
    # env overrides
    cfg["env"] = os.getenv("SERVICE_ENV", cfg["env"])
    cfg["logs_path"] = os.getenv("SERVICE_LOGS_PATH", cfg["logs_path"])
    cfg["scenarios_path"] = os.getenv("SERVICE_SCENARIOS_PATH", cfg["scenarios_path"])
    cfg["version"] = os.getenv("SERVICE_VERSION", cfg["version"])
    return cfg
