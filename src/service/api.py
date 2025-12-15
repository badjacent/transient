"""FastAPI service wrapper for the desk agent orchestrator."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from functools import lru_cache
import uuid
from pathlib import Path
from typing import Any, Dict, Optional, List

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.desk_agent.orchestrator import DeskAgentOrchestrator
from src.oms import OMSAgent
from src.pricing import PricingAgent
from src.service.config import load_config, validate_config

logger = logging.getLogger(__name__)
SLOW_THRESHOLD_MS = 2000


class RunDeskAgentRequest(BaseModel):
    scenario: Optional[str] = Field(None, description="Scenario name/path")
    data: Optional[Dict[str, Any]] = Field(None, description="Custom scenario payload")
    config_overrides: Optional[Dict[str, Any]] = None

    def scenario_payload(self) -> Any:
        return self.data if self.data is not None else self.scenario


class ValidateTradeRequest(BaseModel):
    trade: Dict[str, Any]


class ValidatePricingRequest(BaseModel):
    marks: List[Dict[str, Any]]


app = FastAPI(title="Desk Agent Service", version=load_config().get("version", "dev"))


class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class ScenarioNotFound(ServiceError):
    def __init__(self, message: str):
        super().__init__(message, status_code=404)


class DependencyUnavailable(ServiceError):
    def __init__(self, message: str):
        super().__init__(message, status_code=503)


def _audit_log(record: Dict[str, Any]) -> None:
    cfg = load_config()
    path = cfg.get("audit_log_path")
    if not path:
        return
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as exc:
        logger.warning("audit log failed: %s", exc)


def _metrics_log(record: Dict[str, Any]) -> None:
    cfg = load_config()
    metrics_path = Path(cfg.get("logs_path", "logs")) / "service_metrics.log"
    try:
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        with metrics_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as exc:
        logger.warning("metrics log failed: %s", exc)

# Basic CORS (open by default; tighten as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _setup_logging():
    cfg = load_config()
    if logging.getLogger().handlers:
        logging.getLogger().setLevel(cfg.get("log_level", "INFO"))
        return cfg
    log_path = Path(cfg.get("logs_path", "logs"))
    log_path.mkdir(parents=True, exist_ok=True)
    fmt = '{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}'
    logging.basicConfig(
        level=getattr(logging, cfg.get("log_level", "INFO").upper(), logging.INFO),
        format=fmt if cfg.get("log_format", "json") == "json" else "%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_path / "service.log")],
        force=True,
    )
    return cfg


def _get_orchestrator():
    """Factory for orchestrator; isolated for test monkeypatching."""
    return DeskAgentOrchestrator()


def _get_oms():
    """Factory for OMS agent; isolated for test monkeypatching."""
    return OMSAgent()


def _get_pricing():
    """Factory for Pricing agent; isolated for test monkeypatching."""
    return PricingAgent()


@lru_cache(maxsize=32)
def _cached_scenario(name_or_path: str) -> Dict[str, Any]:
    """Cache loaded scenarios to reduce I/O on repeated runs."""
    return _get_orchestrator().load_scenario(name_or_path)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    cfg = _setup_logging() or load_config()
    content_length = request.headers.get("content-length")
    max_bytes = cfg.get("max_body_bytes", 1_000_000)
    if content_length and content_length.isdigit() and int(content_length) > max_bytes:
        return JSONResponse(status_code=413, content={"error": "payload too large"})
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "request_id=%s path=%s method=%s duration_ms=%.2f content_length=%s status=%s",
            request_id,
            request.url.path,
            request.method,
            duration_ms,
            request.headers.get("content-length"),
            getattr(locals().get("response", None), "status_code", None),
        )
        if duration_ms > SLOW_THRESHOLD_MS:
            logger.warning("slow_request request_id=%s path=%s duration_ms=%.2f", request_id, request.url.path, duration_ms)
        _audit_log(
            {
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "duration_ms": duration_ms,
                "status": getattr(locals().get("response", None), "status_code", None),
                "ts": int(time.time() * 1000),
            }
        )
        _metrics_log(
            {
                "ts": int(time.time() * 1000),
                "request_id": request_id,
                "path": request.url.path,
                "method": request.method,
                "duration_ms": duration_ms,
                "status": getattr(locals().get("response", None), "status_code", None),
            }
        )
    if response:
        response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
async def health():
    cfg = validate_config(load_config())
    scenarios_path = Path(cfg.get("scenarios_path", "scenarios"))
    details = {
        "status": "ok",
        "version": cfg.get("version"),
        "env": cfg.get("env"),
        "dependencies": {
            "refmaster": "stub",
            "oms": "stub",
            "pricing": "stub",
            "ticker_agent": "stub",
            "scenarios_path": str(scenarios_path),
            "scenarios_path_exists": scenarios_path.exists(),
        },
    }
    return details


@app.post("/run-desk-agent")
async def run_desk_agent(payload: RunDeskAgentRequest):
    """Execute the desk agent orchestrator for a named or inline scenario with timeout protection."""
    if payload.scenario is None and payload.data is None:
        raise HTTPException(status_code=400, detail="Provide scenario name/path or data payload.")
    orchestrator = _get_orchestrator()
    cfg = load_config()
    try:
        loop = asyncio.get_event_loop()
        report = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                orchestrator.run_scenario,
                payload.scenario_payload() if payload.data is None else payload.data,
            ),
            timeout=cfg.get("request_timeout_s", 30),
        )
        return report
    except FileNotFoundError as exc:
        raise ScenarioNotFound(str(exc))
    except asyncio.TimeoutError:
        raise ServiceError(f"request timed out after {cfg.get('request_timeout_s', 30)}s", status_code=503)
    except Exception as exc:
        logger.exception("desk agent failed: %s", exc)
        raise ServiceError(str(exc))


@app.get("/scenarios")
async def list_scenarios():
    """List available scenario files in the configured path."""
    cfg = load_config()
    scenarios_path = cfg.get("scenarios_path", "scenarios")
    path = Path(scenarios_path)
    if not path.exists():
        raise ScenarioNotFound("Scenarios path not found")
    files = [p.name for p in path.iterdir() if p.is_file() and p.suffix.lower() in {".json", ".yaml", ".yml"}]
    return {"scenarios": files}


@app.get("/scenarios/{name}")
async def get_scenario(name: str):
    """Return the contents of a scenario file by name/path."""
    orch = _get_orchestrator()
    try:
        data = orch.load_scenario(name)
        return data
    except FileNotFoundError as exc:
        raise ScenarioNotFound(str(exc))
    except Exception as exc:
        logger.exception("load scenario failed: %s", exc)
        raise ServiceError(str(exc))


@app.post("/validate-trade")
async def validate_trade(payload: ValidateTradeRequest):
    """Validate a trade via OMS agent."""
    try:
        res = _get_oms().run(payload.trade)
        return res
    except Exception as exc:
        logger.exception("validate-trade failed: %s", exc)
        raise ServiceError(str(exc))


@app.post("/validate-pricing")
async def validate_pricing(payload: ValidatePricingRequest):
    """Validate pricing marks via pricing agent."""
    try:
        res = _get_pricing().run(payload.marks)
        return res
    except Exception as exc:
        logger.exception("validate-pricing failed: %s", exc)
        raise ServiceError(str(exc))


@app.get("/status")
async def status():
    cfg = load_config()
    return {"status": "ok", "version": cfg.get("version"), "env": cfg.get("env")}


@app.exception_handler(ServiceError)
async def handle_service_error(request: Request, exc: ServiceError):
    _setup_logging()
    request_id = request.headers.get("X-Request-ID", "")
    logger.error(
        "service_error path=%s request_id=%s status=%s detail=%s",
        request.url.path,
        request_id,
        exc.status_code,
        exc.message,
    )
    return JSONResponse(status_code=exc.status_code, content={"error": exc.message, "request_id": request_id})


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    _setup_logging()
    request_id = request.headers.get("X-Request-ID", "")
    logger.exception("unhandled_error path=%s request_id=%s", request.url.path, request_id)
    return JSONResponse(status_code=500, content={"error": "internal_error", "detail": str(exc), "request_id": request_id})
