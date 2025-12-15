# Week 7 - Service Wrapper & Demo Prep TODO (implementation-ready)
Audience: implementation agent. Treat other modules as stubs (e.g., `desk_agent.orchestrator`). Paths are repo-root-relative.

## Module Structure Setup
- [x] Ensure `src/service/` exists with importable stubs: `__init__.py`, `api.py` (FastAPI endpoints), `main.py` (entrypoint), `config.py` (config loader).
- [x] Ensure `tests/service/` exists with `__init__.py` and `test_api.py` placeholder.
- [x] Ensure `docs/` exists with placeholders: `ARCHITECTURE.md`, `INSTALL.md`, `DEMO_SCRIPT.md`, `README.md` (or updated main README).
- [x] Ensure `logs/` directory exists (configurable path).

## Task 1: FastAPI Wrapper

### 1.1 App Setup
- [x] Create FastAPI app in `src/service/api.py`; configure CORS if needed; add request/response models (Pydantic); include error-handling middleware; expose OpenAPI docs.

### 1.2 Health Endpoint
- [x] Implement `GET /health` returning service status, version, dependency checks (API keys, data sources), and sub-agent uptimes if available.

### 1.3 Main Desk Agent Endpoint
- [x] Implement `POST /run-desk-agent`:
  - [x] Request schema: `scenario` (str name), optional `data` (dict/custom scenario), optional `config_overrides` (dict).
  - [x] Call `desk_agent.orchestrator` stub; handle errors gracefully; validate request; serialize response matching integrated report structure (data_quality, trade_issues, pricing_flags, market_context, narrative, execution_time_ms, timestamp).

### 1.4 Optional Endpoints
- [x] `GET /scenarios` (list), `GET /scenarios/{name}` (details), `POST /validate-trade`, `POST /validate-pricing`, `GET /status` for detailed service status.

### 1.5 Error Handling
- [x] Define custom exceptions and global handlers; map to HTTP codes (200, 400 validation, 404 scenario missing, 500 internal, 503 dependency down); include error details and logging.

## Task 2: Logging
- [x] Structured JSON logging with levels; console for dev, file for prod (rotation optional).
- [x] Request/response logging: endpoint/method, request ID (UUID), timestamp, sanitized payload; response status/time/size; include request ID in headers.
- [x] Timing/perf logging: per-endpoint duration, per-sub-agent timings (refmaster/OMS/pricing/ticker/data snapshots), total orchestrator time; flag slow requests.
- [x] Error tracing: full stack traces with context (request ID, params, user context if any); correlation IDs; external API failures and validation errors.
- [x] Audit logging: record scenario runs, trade validations, pricing validations with timestamps and request IDs; tamper-evident optional.

## Task 3: Architecture Docs (`docs/ARCHITECTURE.md`)
- [x] Executive summary; high-level architecture; component roles.
- [x] Diagram (ASCII/Mermaid/image) showing service layer, orchestrator, sub-agents, data sources, data flow, interactions.
- [x] End-to-end workflow steps (request → parse → orchestrator → sub-agents → aggregate → response) with decision/error paths.
- [x] Data flow: input/output schemas, transformations, caching (if any), external API deps.
- [x] Extension points: adding agents/scenarios, config options, plugin/versioning strategy.
- [x] Technical details: stack, dependencies, deployment architecture, scaling, security considerations.

## Task 4: Demo Script (`docs/DEMO_SCRIPT.md`)
- [x] CTO-ready structure with timing and talking points.
- [x] Problem statement (booking/pricing errors, manual pain, regulatory pressure) with concrete examples/impact.
- [x] Workflow demo: end-to-end run, show components, scenarios, real-time results, automation benefits.
- [x] Value props: time/error/cost savings, compliance, scalability, ROI (if available).
- [x] Differentiators: AI-augmented validation, integrated workflow, real-time processing, reporting, extensibility; competitive positioning.
- [x] Demo scenarios: 2–3 (clean day, mis-booked trade, complex multi-issue) with expected outputs and backups for API issues.

## Configuration Management (`src/service/config.py`)
- [x] Load config from env vars (via `load_dotenv()`), then file (YAML/JSON), then defaults.
- [x] Support: API keys, endpoints, timeouts, logging levels, feature flags, scenario paths, tolerance thresholds, environment selection (dev/stage/prod).
- [x] Document required env vars; validate on startup.

## Packaging and Installation
- [x] Review/update `pyproject.toml` for metadata, deps, entry points, version.
- [x] `docs/INSTALL.md`: prerequisites (Python, system reqs, external deps), install steps (clone, deps, env vars, run service), Docker/deployment options.
- [x] Build/distribution: create wheel/sdist, test install, document package install.

## Testing
- [x] API tests: health, main endpoint (valid/invalid scenario, custom data, errors), request validation, response format, error responses.
- [x] Integration: full workflow with real scenarios; optional mocks for external APIs; error recovery; concurrent requests if applicable.
- [x] Performance: response times, load if applicable, timing logs accuracy, timeout handling.

## Documentation
- [x] Main `README.md`: overview, quick start, features, architecture summary, install link, usage examples, contributing, license.
- [x] API docs: ensure OpenAPI generation; endpoint docstrings; request/response examples; error codes; auth (if any).
- [x] Code docs: docstrings, type hints, complex logic notes, minimal inline comments where needed.

## Production Readiness
- [x] Error handling: graceful degradation, retries for transient failures, circuit breakers (optional), timeouts, resource cleanup.
- [x] Security: input validation, output sanitization, sensitive data redaction in logs, secure defaults; document considerations.
- [x] Monitoring: health monitoring, metrics (request/error rates, response times, success rate), alerts if applicable.
- [x] Performance: optimize slow paths, caching where appropriate, profile hot paths.

## Demo Preparation
- [ ] Demo environment: clean setup, preload test data, verify scenarios, backups for API failures, end-to-end rehearsal. (Non-coding/field task)
- [ ] Materials: slides (if needed), demo script, example outputs, Q&A prep, technical deep-dive materials. (Non-coding/field task)
- [ ] Practice: run through script, time it, identify/presolve risks, refine talking points. (Non-coding/field task)

## Evaluation Criteria
- [ ] Functionality: service runs cleanly; endpoints correct; robust error handling; comprehensive logging.
- [ ] Documentation: architecture clear, install accurate, demo script compelling, README professional.
- [ ] Client readiness: shows domain and engineering competence; polished presentation; demo-ready. (Non-coding/field task)
- [ ] Code quality: clean, tested, documented, best practices.

## Optional Enhancements
- [ ] Advanced: authZ/authN, rate limiting, request queuing, WebSocket updates, GraphQL or gRPC.
- [ ] Observability: distributed tracing, metrics dashboard, log aggregation, perf monitoring, error tracking integration.
- [ ] Deployment: Docker/K8s configs, CI/CD pipeline, automated tests in pipeline, deployment docs.
- [ ] Developer experience: dev setup script, hot reload, API client/SDK, example integrations, developer guide.
