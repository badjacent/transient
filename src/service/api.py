"""FastAPI service wrapper for the desk agent orchestrator."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.desk_agent.orchestrator import DeskAgentOrchestrator
from src.service.config import load_config

logger = logging.getLogger(__name__)


class RunDeskAgentRequest(BaseModel):
    scenario: Optional[str] = Field(None, description="Scenario name/path")
    data: Optional[Dict[str, Any]] = Field(None, description="Custom scenario payload")
    config_overrides: Optional[Dict[str, Any]] = None

    def scenario_payload(self) -> Any:
        return self.data if self.data is not None else self.scenario


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


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    _setup_logging()
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info("request_id=%s path=%s method=%s duration_ms=%.2f", request_id, request.url.path, request.method, duration_ms)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
async def health():
    cfg = load_config()
    return {"status": "ok", "version": cfg.get("version"), "env": cfg.get("env")}


@app.post("/run-desk-agent")
async def run_desk_agent(payload: RunDeskAgentRequest):
    if payload.scenario is None and payload.data is None:
        raise HTTPException(status_code=400, detail="Provide scenario name/path or data payload.")
    orchestrator = DeskAgentOrchestrator()
    try:
        report = orchestrator.run_scenario(payload.scenario_payload())
        return report
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("desk agent failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
