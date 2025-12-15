# Desk Agent Service

FastAPI wrapper around the Desk Agent orchestrator (normalization + OMS + pricing + ticker agent + market context). Ships with sample scenarios and structured reports.

## Quick start
1. Install: `pip install -e .`
2. Run: `python -m src.service.main` (defaults to `0.0.0.0:8000`)
3. Health: `GET http://localhost:8000/health`
4. Execute: `POST http://localhost:8000/run-desk-agent` with `{"scenario": "scenarios/clean_day.json"}` or inline `data`.

## Endpoints
- `GET /health`, `GET /status`
- `POST /run-desk-agent`
- `GET /scenarios`, `GET /scenarios/{name}`
- `POST /validate-trade`
- `POST /validate-pricing`

OpenAPI docs at `/docs` and `/openapi.json`.

## Config
Environment overrides (see `src/service/config.py`):
- `SERVICE_ENV`, `SERVICE_VERSION`
- `SERVICE_LOG_LEVEL`, `SERVICE_LOG_FORMAT`, `SERVICE_LOGS_PATH`, `SERVICE_AUDIT_LOG_PATH`
- `SERVICE_SCENARIOS_PATH`, `SERVICE_HOST`, `SERVICE_PORT`, `SERVICE_REQUEST_TIMEOUT_S`

## Docs
- `docs/INSTALL.md` for setup/run
- `docs/ARCHITECTURE.md` for design
- `docs/DEMO_SCRIPT.md` for demo flow
- `docs/API_SERVICE.md` for endpoint examples
