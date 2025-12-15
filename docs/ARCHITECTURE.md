# Service Architecture (Week 7)

## Executive summary
FastAPI wrapper that exposes the Desk Agent orchestrator as an HTTP service. Requests flow through validation, logging, orchestration, and response formatting with structured output and error handling.

## High-level architecture
- **Service layer:** `src/service/api.py` (FastAPI) + `src/service/main.py` (uvicorn entry).
- **Orchestrator:** `src/desk_agent/orchestrator.py` — runs normalization, OMS QA, pricing, ticker agent, market context.
- **Sub-agents:** Refmaster, OMS, Pricing, Ticker Agent, Market Data stubs.
- **Config:** `src/service/config.py` (defaults → YAML/JSON override → env overrides).
- **Docs/Examples:** `examples/combined_report_example.json`, `scenarios/*.json`.

## Diagram (text)
```
Client -> FastAPI (api.py)
          | validate & log
          v
      DeskAgentOrchestrator
       |--> Refmaster (normalize)
       |--> OMS (trade QA)
       |--> Pricing (marks)
       |--> Ticker Agent (Q&A)
       |--> Market Data (snapshots)
          v
      Aggregated report -> Response
```

## Workflow steps
1. Request hits FastAPI route (`/health`, `/run-desk-agent`, etc.).
2. Middleware assigns `X-Request-ID`, logs start/end with timings.
3. Request validated (Pydantic models) and dispatched.
4. Orchestrator loads/validates scenario, executes sub-agents with retries.
5. Results aggregated into structured report (data_quality, trade_issues, pricing_flags, market_context, ticker_agent_results, narrative, summary, execution_metadata).
6. Response serialized to JSON; errors mapped to HTTP codes with JSON body.

## Data flow
- **Input schemas:** RunDeskAgentRequest (scenario name or inline data), ValidateTradeRequest, ValidatePricingRequest.
- **Output schemas:** Integrated report (see orchestrator README) or validation results.
- **Transforms:** Scenario validation → normalization → QA/mark enrichment → aggregation/stats → narrative.
- **External deps:** Market data stubs (`data_tools.fd_api`), refmaster data (`REFMASTER_DATA_PATH` optional).

## Extension points
- Add new endpoints in `api.py`.
- Plug new agents into the orchestrator or swap stubs via dependency injection.
- Feature flags/config keys in `config.py` for logging, retries, paths, timeouts.
- Additional report formats could be layered in `generate_report`.

## Technical details
- **Stack:** FastAPI, uvicorn, Pydantic, standard logging.
- **Deployment:** `uvicorn src.service.api:app --host 0.0.0.0 --port 8000` (or via `python -m src.service.main`).
- **Logging:** Structured JSON by default to stdout and `logs/service.log`; request IDs propagated.
- **Security considerations:** validate inputs via Pydantic; redaction/sanitization recommended for sensitive fields; enable CORS restrictions for production.
- **Audit:** Optional JSONL audit log via `SERVICE_AUDIT_LOG_PATH` (records request id/path/duration/status).
