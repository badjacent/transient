"""FastAPI service wrapper for the desk agent orchestrator."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.desk_agent.orchestrator import DeskAgentOrchestrator
from src.oms import OMSAgent
from src.pricing import PricingAgent
from src.refmaster.normalizer_agent import NormalizerAgent
from src.service.config import load_config, validate_config
from src.ticker_agent import ticker_agent

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
    verbose: bool = Field(
        default=False, description="Return detailed step-by-step validation results"
    )


class ValidatePricingRequest(BaseModel):
    marks: List[Dict[str, Any]]
    verbose: bool = Field(
        default=False, description="Return detailed step-by-step validation results"
    )


class TickerAgentRequest(BaseModel):
    question: str = Field(..., description="Natural language question about a ticker")


class NormalizeRequest(BaseModel):
    identifier: str = Field(
        ...,
        description=(
            "Ticker identifier to normalize "
            "(e.g., 'AAPL US', 'US0378331005', 'AAPL.OQ')"
        ),
    )
    top_k: int = Field(
        default=5, ge=1, le=20, description="Maximum number of results to return"
    )


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
        format=(
            fmt
            if cfg.get("log_format", "json") == "json"
            else "%(asctime)s %(levelname)s %(name)s %(message)s"
        ),
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path / "service.log"),
        ],
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


def _get_ticker_agent():
    """Factory for Ticker agent; isolated for test monkeypatching."""
    return ticker_agent


def _get_refmaster():
    """Factory for Refmaster normalizer; isolated for test monkeypatching."""
    return NormalizerAgent()


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
            logger.warning(
                "slow_request request_id=%s path=%s duration_ms=%.2f",
                request_id,
                request.url.path,
                duration_ms,
            )
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
            "refmaster": "active",
            "oms": "stub",
            "pricing": "stub",
            "ticker_agent": "active",
            "scenarios_path": str(scenarios_path),
            "scenarios_path_exists": scenarios_path.exists(),
        },
    }
    return details


@app.post("/run-desk-agent")
async def run_desk_agent(payload: RunDeskAgentRequest):
    """Execute the desk agent orchestrator for a named or inline scenario with timeout protection."""
    if payload.scenario is None and payload.data is None:
        raise HTTPException(
            status_code=400, detail="Provide scenario name/path or data payload."
        )
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
        raise ServiceError(
            f"request timed out after {cfg.get('request_timeout_s', 30)}s",
            status_code=503,
        )
    except Exception as exc:
        logger.exception("desk agent failed: %s", exc)
        raise ServiceError(str(exc))


@app.get("/run-desk-agent/verbose")
async def get_desk_agent_verbose_info():
    """Return detailed information about desk agent execution structure."""
    orchestrator = _get_orchestrator()
    return {
        "execution_steps": [
            {
                "step": "normalize",
                "description": "Normalize ticker identifiers via refmaster",
                "agent": "refmaster",
                "inputs": ["trades", "marks", "questions"],
                "outputs": ["ticker_normalizations", "normalization_issues"],
            },
            {
                "step": "trade_qa",
                "description": "Validate trades via OMS agent",
                "agent": "oms",
                "inputs": ["trades"],
                "outputs": ["trade_issues"],
            },
            {
                "step": "pricing",
                "description": "Validate marks via pricing agent",
                "agent": "pricing",
                "inputs": ["marks"],
                "outputs": ["pricing_flags"],
            },
            {
                "step": "ticker",
                "description": "Answer questions via ticker agent",
                "agent": "ticker_agent",
                "inputs": ["questions"],
                "outputs": ["ticker_agent_results"],
            },
            {
                "step": "market_context",
                "description": "Aggregate market snapshots and sector performance",
                "agent": "market_data",
                "inputs": ["trades", "marks"],
                "outputs": ["market_context"],
            },
        ],
        "report_structure": {
            "scenario": "Scenario metadata",
            "data_quality": "Ticker normalization results",
            "trade_issues": "Trade validation results",
            "pricing_flags": "Pricing validation results",
            "market_context": "Market snapshots and sector aggregation",
            "ticker_agent_results": "Q&A responses",
            "narrative": "Human-readable summary",
            "summary": "Aggregated statistics",
            "execution_metadata": {
                "execution_time_ms": "Total execution time",
                "timestamp": "Execution timestamp",
                "agents_executed": "List of agents that ran",
                "trace": "Step-by-step execution trace",
                "config": "Configuration used",
                "errors": "List of errors encountered",
            },
        },
        "configuration": {
            "retry_max": orchestrator.retry_cfg.get("max"),
            "retry_backoff_ms": orchestrator.retry_cfg.get("backoff_ms"),
            "parallel_ticker": orchestrator.parallel_ticker,
        },
    }


@app.get("/scenarios")
async def list_scenarios():
    """List available scenario files in the configured path."""
    cfg = load_config()
    scenarios_path = cfg.get("scenarios_path", "scenarios")
    path = Path(scenarios_path)
    if not path.exists():
        raise ScenarioNotFound("Scenarios path not found")
    files = [
        p.name
        for p in path.iterdir()
        if p.is_file() and p.suffix.lower() in {".json", ".yaml", ".yml"}
    ]
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
    """Validate a trade via OMS agent with optional verbose step-by-step details."""
    try:
        oms = _get_oms()
        if payload.verbose:
            # Enhanced response with step-by-step details
            res = _get_oms().run(payload.trade)
            # Add verbose details by re-running checks with intermediate data
            verbose_res = _validate_trade_verbose(oms, payload.trade)
            res["verbose"] = verbose_res
        else:
            res = oms.run(payload.trade)
        return res
    except Exception as exc:
        logger.exception("validate-trade failed: %s", exc)
        raise ServiceError(str(exc))


def _validate_trade_verbose(oms: OMSAgent, trade_json: Any) -> Dict[str, Any]:
    """Run validation with verbose step-by-step details."""
    from pydantic import ValidationError

    from src.data_tools.fd_api import get_price_snapshot
    from src.oms.schema import Trade

    trade_dict, parse_issues = oms._coerce_trade_dict(trade_json)
    steps = []
    trade: Optional[Trade] = None

    # Step 1: Required fields check
    required_issues = oms._check_required(trade_dict)
    steps.append(
        {
            "step": "required_fields",
            "description": "Check all required fields are present",
            "status": "ok" if not required_issues else "error",
            "issues": required_issues,
            "checked_fields": [
                "ticker",
                "quantity",
                "price",
                "currency",
                "counterparty",
                "trade_dt",
                "settle_dt",
            ],
        }
    )

    # Step 2: Schema validation
    try:
        trade = oms._parse_trade(trade_dict)
        steps.append(
            {
                "step": "schema_validation",
                "description": "Validate trade schema and data types",
                "status": "ok",
                "parsed_trade": {
                    "ticker": trade.ticker,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "currency": trade.currency,
                    "counterparty": trade.counterparty,
                    "trade_dt": trade.trade_dt,
                    "settle_dt": trade.settle_dt,
                },
            }
        )
    except ValidationError as exc:
        validation_issues = oms._validation_issues(exc)
        steps.append(
            {
                "step": "schema_validation",
                "description": "Validate trade schema and data types",
                "status": "error",
                "issues": validation_issues,
            }
        )
        return {"steps": steps}

    if not trade:
        return {"steps": steps}

    # Step 3: Identifier normalization
    identifier_issues = oms._check_identifier(trade)
    normalization_results = []
    try:
        norm_results = oms.normalizer.normalize(trade.ticker, top_k=3)
        normalization_results = [
            {
                "symbol": r.equity.symbol,
                "confidence": r.confidence,
                "ambiguous": r.ambiguous,
                "reasons": r.reasons,
            }
            for r in norm_results
        ]
    except Exception:
        pass

    steps.append(
        {
            "step": "identifier_normalization",
            "description": "Normalize ticker identifier via refmaster",
            "status": "ok" if not identifier_issues else "warning",
            "input_ticker": trade.ticker,
            "normalization_results": normalization_results,
            "issues": identifier_issues,
        }
    )

    # Step 4: Currency check
    currency_issues = oms._check_currency(trade)
    ref_currency = oms.ref_currency_map.get(trade.ticker, "USD")
    steps.append(
        {
            "step": "currency_validation",
            "description": "Validate trade currency matches reference",
            "status": "ok" if not currency_issues else "warning",
            "trade_currency": trade.currency,
            "reference_currency": ref_currency,
            "issues": currency_issues,
        }
    )

    # Step 5: Price validation
    price_issues = []
    market_data = None
    try:
        trade_date = trade._parse_date(trade.trade_dt)
        snap = get_price_snapshot(trade.ticker, trade_date)
        market_data = {
            "market_price": snap.price,
            "as_of_date": str(snap.as_of),
            "source": snap.source,
        }
        price_issues = oms._check_price(trade)
    except Exception as exc:
        price_issues = [
            {
                "type": "price_tolerance",
                "severity": "WARNING",
                "message": f"Market data unavailable: {exc}",
                "field": "price",
            }
        ]

    steps.append(
        {
            "step": "price_validation",
            "description": "Validate trade price against market data",
            "status": "ok" if not price_issues else "warning",
            "trade_price": trade.price,
            "market_data": market_data,
            "thresholds": {
                "warning_pct": oms.thresholds["warning"] * 100,
                "error_pct": oms.thresholds["error"] * 100,
            },
            "issues": price_issues,
        }
    )

    # Step 6: Counterparty validation
    counterparty_issues = oms._check_counterparty(trade)
    steps.append(
        {
            "step": "counterparty_validation",
            "description": "Validate counterparty is in approved list",
            "status": "ok" if not counterparty_issues else "warning",
            "counterparty": trade.counterparty,
            "valid_counterparties": list(oms.valid_counterparties),
            "issues": counterparty_issues,
        }
    )

    # Step 7: Settlement date validation
    settlement_issues = oms._check_settlement(trade)
    trade_date = trade._parse_date(trade.trade_dt)
    settle_date = trade._parse_date(trade.settle_dt)
    delta_days = (settle_date - trade_date).days
    steps.append(
        {
            "step": "settlement_validation",
            "description": "Validate settlement date rules",
            "status": "ok" if not settlement_issues else "error",
            "trade_date": trade.trade_dt,
            "settle_date": trade.settle_dt,
            "settlement_days": delta_days,
            "expected_settlement_days": oms.settlement_days,
            "is_weekend": settle_date.weekday() >= 5,
            "issues": settlement_issues,
        }
    )

    return {"steps": steps}


@app.post("/validate-pricing")
async def validate_pricing(payload: ValidatePricingRequest):
    """Validate pricing marks via pricing agent with optional verbose step-by-step details."""
    try:
        pricing = _get_pricing()
        if payload.verbose:
            # Enhanced response with step-by-step details
            res = pricing.run(payload.marks)
            verbose_res = _validate_pricing_verbose(pricing, payload.marks)
            res["verbose"] = verbose_res
        else:
            res = pricing.run(payload.marks)
        return res
    except Exception as exc:
        logger.exception("validate-pricing failed: %s", exc)
        raise ServiceError(str(exc))


def _validate_pricing_verbose(
    pricing: PricingAgent, marks_input: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Run pricing validation with verbose step-by-step details."""
    from datetime import date

    from src.pricing.schema import Mark

    steps = []
    marks_records = pricing._load_marks(marks_input)

    # Step 1: Load and parse marks
    parsed_marks = []
    for idx, mark_dict in enumerate(marks_records):
        try:
            mark = Mark(**mark_dict)
            parsed_marks.append((idx, mark, None))
        except Exception as exc:
            parsed_marks.append((idx, None, str(exc)))

    steps.append(
        {
            "step": "load_marks",
            "description": "Load and parse mark records",
            "status": "ok" if all(m[1] for m in parsed_marks) else "error",
            "total_marks": len(marks_records),
            "parsed_successfully": sum(1 for m in parsed_marks if m[1]),
            "parse_errors": [
                {"index": idx, "error": err}
                for idx, _, err in parsed_marks
                if err is not None
            ],
        }
    )

    # Step 2: Normalize tickers (refmaster)
    normalization_steps = []
    for idx, mark, _ in parsed_marks:
        if mark is None:
            continue
        norm_results = []
        try:
            if pricing.normalizer.refmaster:
                results = pricing.normalizer.refmaster.normalize(mark.ticker, top_k=1)
                norm_results = [
                    {
                        "symbol": r.equity.symbol,
                        "confidence": r.confidence,
                        "ambiguous": r.ambiguous,
                    }
                    for r in results
                ]
        except Exception:
            pass

        normalization_steps.append(
            {
                "ticker": mark.ticker,
                "normalization_results": norm_results,
            }
        )

    steps.append(
        {
            "step": "ticker_normalization",
            "description": "Normalize ticker identifiers via refmaster",
            "normalizations": normalization_steps,
        }
    )

    # Step 3: Fetch market data and enrich (simulate what normalizer does)
    enrichment_steps = []
    for idx, mark, _ in parsed_marks:
        if mark is None:
            continue

        market_data = None
        deviation = None
        classification = None
        error = None
        is_stale = False

        try:
            # Fetch market price
            result = pricing.normalizer.fetch_market_price(mark.ticker, mark.as_of_date)
            if result.get("error"):
                error = result["error"]
                classification = "NO_MARKET_DATA"
            else:
                market_price = result.get("price")
                market_data = {
                    "market_price": market_price,
                    "as_of_date": str(result.get("date", "")),
                    "source": "financialdatasets.ai",
                }

                # Check if stale
                try:
                    mark_date = date.fromisoformat(mark.as_of_date)
                    age_days = (date.today() - mark_date).days
                    stale_days = pricing.normalizer.tolerances.get("stale_days", 2)
                    is_stale = age_days > stale_days
                except Exception:
                    pass

                # Calculate deviation and classification
                if market_price and market_price != 0:
                    deviation = abs(mark.internal_mark - market_price) / market_price
                    comparison = pricing.normalizer.compare_mark_to_market(
                        mark.internal_mark, market_price, mark.ticker
                    )
                    classification = comparison.get("classification", "OK")
                else:
                    classification = "NO_MARKET_DATA"

                # Override with STALE_MARK if applicable
                if is_stale and classification != "NO_MARKET_DATA":
                    classification = "STALE_MARK"

        except Exception as exc:
            error = str(exc)
            classification = "NO_MARKET_DATA"

        enrichment_steps.append(
            {
                "ticker": mark.ticker,
                "internal_mark": mark.internal_mark,
                "market_data": market_data,
                "deviation_percentage": deviation * 100 if deviation else None,
                "classification": classification,
                "is_stale": is_stale,
                "error": error,
                "thresholds": {
                    "ok_threshold_pct": pricing.normalizer.tolerances.get(
                        "ok_threshold", 0.02
                    )
                    * 100,
                    "review_threshold_pct": pricing.normalizer.tolerances.get(
                        "review_threshold", 0.05
                    )
                    * 100,
                    "stale_days": pricing.normalizer.tolerances.get("stale_days", 2),
                },
            }
        )

    steps.append(
        {
            "step": "market_data_enrichment",
            "description": "Fetch market prices and calculate deviations",
            "enrichments": enrichment_steps,
        }
    )

    # Step 4: Classification summary
    classifications = {}
    for step in enrichment_steps:
        cls = step.get("classification", "UNKNOWN")
        classifications[cls] = classifications.get(cls, 0) + 1

    steps.append(
        {
            "step": "classification_summary",
            "description": "Aggregate classification counts",
            "classifications": classifications,
            "total_marks": len(enrichment_steps),
        }
    )

    return {"steps": steps}


@app.post("/ticker-agent")
async def ticker_agent_endpoint(payload: TickerAgentRequest):
    """Answer a question about a ticker using the ticker agent."""
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            _get_ticker_agent().run,
            payload.question,
        )
        return result
    except Exception as exc:
        logger.exception("ticker-agent failed: %s", exc)
        raise ServiceError(str(exc))


@app.post("/normalize")
async def normalize_endpoint(payload: NormalizeRequest):
    """Normalize a ticker identifier to canonical equity records."""
    try:
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            _get_refmaster().normalize,
            payload.identifier,
            payload.top_k,
        )
        # Convert Pydantic models to dicts for JSON serialization
        return {
            "identifier": payload.identifier,
            "results": [
                {
                    "equity": result.equity.model_dump(),
                    "confidence": result.confidence,
                    "reasons": result.reasons,
                    "ambiguous": result.ambiguous,
                }
                for result in results
            ],
            "count": len(results),
        }
    except Exception as exc:
        logger.exception("normalize failed: %s", exc)
        raise ServiceError(str(exc))


@app.get("/status")
async def status():
    cfg = load_config()
    return {"status": "ok", "version": cfg.get("version"), "env": cfg.get("env")}


@app.get("/config")
async def get_config():
    """Return current service configuration (sanitized, no secrets)."""
    cfg = load_config()
    # Sanitize: remove sensitive data, show what's configured
    sanitized = {
        "env": cfg.get("env"),
        "version": cfg.get("version"),
        "host": cfg.get("host"),
        "port": cfg.get("port"),
        "log_level": cfg.get("log_level"),
        "log_format": cfg.get("log_format"),
        "request_timeout_s": cfg.get("request_timeout_s"),
        "max_body_bytes": cfg.get("max_body_bytes"),
        "scenarios_path": cfg.get("scenarios_path"),
        "logs_path": cfg.get("logs_path"),
        "audit_log_path": cfg.get("audit_log_path"),
        "feature_flags": cfg.get("feature_flags", {}),
    }
    return sanitized


@app.get("/desk-agent/config")
async def get_desk_agent_config():
    """Return desk agent orchestrator configuration."""
    from src.desk_agent.config import load_config as load_desk_config

    desk_cfg = load_desk_config()
    orchestrator = _get_orchestrator()
    return {
        "scenarios_path": desk_cfg.get("scenarios_path"),
        "logs_path": desk_cfg.get("logs_path"),
        "log_level": desk_cfg.get("log_level"),
        "retry_config": {
            "max_retries": orchestrator.retry_cfg.get("max"),
            "backoff_ms": orchestrator.retry_cfg.get("backoff_ms"),
            "abort_after_retry": orchestrator.retry_cfg.get("abort_after_retry"),
        },
        "parallel_ticker": orchestrator.parallel_ticker,
        "performance_budget_ms": desk_cfg.get("performance_budget_ms"),
        "refmaster_data_path": desk_cfg.get("refmaster_data_path"),
        "oms_config": {
            "price_warning_threshold": desk_cfg.get("oms_price_warning"),
            "price_error_threshold": desk_cfg.get("oms_price_error"),
            "settlement_days": desk_cfg.get("settlement_days"),
        },
        "pricing_config": {
            "stale_days": desk_cfg.get("pricing_stale_days"),
        },
    }


@app.get("/desk-agent/execution-trace")
async def get_execution_trace(scenario: Optional[str] = None):
    """
    Get execution trace information.

    If scenario is provided, returns trace from last execution of that scenario.
    Otherwise returns general trace information.
    """
    # Note: This is a simplified version. In production, you might want to
    # store traces in a database or cache for retrieval.
    return {
        "note": "Execution traces are included in the execution_metadata of each /run-desk-agent response",
        "trace_structure": {
            "step": "string (normalize, trade_qa, pricing, ticker, market_context)",
            "status": "string (OK, ERROR)",
            "duration_ms": "float",
            "attempts": "int",
            "error": "string (if status is ERROR)",
        },
        "scenario": scenario,
        "message": "To get execution trace, check the execution_metadata.trace field in the response from POST /run-desk-agent",
    }


@app.get("/endpoints")
async def list_endpoints():
    """List all available API endpoints with descriptions."""
    routes = []
    for route in app.routes:
        if hasattr(route, "methods") and hasattr(route, "path"):
            methods = list(route.methods)
            if "HEAD" in methods:
                methods.remove("HEAD")
            if "OPTIONS" in methods:
                methods.remove("OPTIONS")
            if methods:
                routes.append(
                    {
                        "path": route.path,
                        "methods": methods,
                        "name": getattr(route, "name", None),
                        "summary": getattr(route, "summary", None),
                    }
                )
    return {
        "endpoints": sorted(routes, key=lambda x: (x["path"], x["methods"])),
        "total": len(routes),
    }


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
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message, "request_id": request_id},
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(request: Request, exc: Exception):
    _setup_logging()
    request_id = request.headers.get("X-Request-ID", "")
    logger.exception(
        "unhandled_error path=%s request_id=%s", request.url.path, request_id
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "detail": str(exc),
            "request_id": request_id,
        },
    )
