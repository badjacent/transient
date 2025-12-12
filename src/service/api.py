"""FastAPI service wrapper for the desk agent orchestrator."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from pydantic import BaseModel, Field

from src.desk_agent.orchestrator import DeskAgentOrchestrator
from src.oms import OMSAgent
from src.pricing import PricingAgent
from src.service.config import load_config

logger = logging.getLogger(__name__)


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

# Basic CORS (open by default; tighten as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _setup_logging():
    if logging.getLogger().handlers:
        return
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _get_orchestrator():
    return DeskAgentOrchestrator()


def _get_oms():
    return OMSAgent()


def _get_pricing():
    return PricingAgent()


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    _setup_logging()
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.perf_counter()
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
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
async def health():
    cfg = load_config()
    details = {
        "status": "ok",
        "version": cfg.get("version"),
        "env": cfg.get("env"),
        "dependencies": {"refmaster": "stub", "oms": "stub", "pricing": "stub", "ticker_agent": "stub"},
    }
    return details


@app.post("/run-desk-agent")
async def run_desk_agent(payload: RunDeskAgentRequest):
    if payload.scenario is None and payload.data is None:
        raise HTTPException(status_code=400, detail="Provide scenario name/path or data payload.")
    orchestrator = _get_orchestrator()
    try:
        report = orchestrator.run_scenario(payload.scenario_payload())
        return report
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("desk agent failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/scenarios")
async def list_scenarios():
    cfg = load_config()
    scenarios_path = cfg.get("scenarios_path", "scenarios")
    path = Path(scenarios_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Scenarios path not found")
    files = [p.name for p in path.iterdir() if p.is_file() and p.suffix.lower() in {".json", ".yaml", ".yml"}]
    return {"scenarios": files}


@app.get("/scenarios/{name}")
async def get_scenario(name: str):
    orch = _get_orchestrator()
    try:
        data = orch.load_scenario(name)
        return data
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("load scenario failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/validate-trade")
async def validate_trade(payload: ValidateTradeRequest):
    try:
        res = _get_oms().run(payload.trade)
        return res
    except Exception as exc:
        logger.exception("validate-trade failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/validate-pricing")
async def validate_pricing(payload: ValidatePricingRequest):
    try:
        res = _get_pricing().run(payload.marks)
        return res
    except Exception as exc:
        logger.exception("validate-pricing failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/status")
async def status():
    cfg = load_config()
    return {"status": "ok", "version": cfg.get("version"), "env": cfg.get("env")}
