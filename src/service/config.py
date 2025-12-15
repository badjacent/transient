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
    "log_level": "INFO",
    "log_format": "json",
    "host": "0.0.0.0",
    "port": 8000,
    "request_timeout_s": 30,
    "feature_flags": {},
    "audit_log_path": None,
    "max_body_bytes": 1_000_000,
}


def load_config(path: str | None = None) -> Dict[str, Any]:
    """Load service configuration from defaults, optional YAML/JSON file, then environment overrides."""
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
    cfg["log_level"] = os.getenv("SERVICE_LOG_LEVEL", cfg["log_level"])
    cfg["log_format"] = os.getenv("SERVICE_LOG_FORMAT", cfg["log_format"])
    cfg["host"] = os.getenv("SERVICE_HOST", cfg["host"])
    cfg["port"] = int(os.getenv("SERVICE_PORT", cfg["port"]))
    cfg["request_timeout_s"] = int(os.getenv("SERVICE_REQUEST_TIMEOUT_S", cfg["request_timeout_s"]))
    cfg["max_body_bytes"] = int(os.getenv("SERVICE_MAX_BODY_BYTES", cfg.get("max_body_bytes", 1_000_000)))
    cfg["feature_flags"] = cfg.get("feature_flags") or {}
    cfg["audit_log_path"] = os.getenv("SERVICE_AUDIT_LOG_PATH", cfg.get("audit_log_path"))
    return cfg


def validate_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    """Validate required config keys; raises on missing required entries."""
    required_env: list[str] = []
    missing = [key for key in required_env if not cfg.get(key)]
    if missing:
        raise ValueError(f"Missing required config keys: {', '.join(missing)}")
    return cfg
