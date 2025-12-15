# Install & Run

## Prereqs
- Python 3.10+
- Dependencies: `pip install -e .` (installs FastAPI, uvicorn, etc.)
- `.env` for overrides (optional): `SERVICE_ENV`, `SERVICE_LOG_LEVEL`, `SERVICE_SCENARIOS_PATH`, `SERVICE_PORT`, `SERVICE_LOGS_PATH`, `SERVICE_AUDIT_LOG_PATH`

## Quick start
1) Install deps: `pip install -e .`  
2) Run service: `python -m src.service.main` (defaults to 0.0.0.0:8000)  
3) Health check: `GET http://localhost:8000/health`  
4) Run desk agent:  
   ```bash
   curl -X POST http://localhost:8000/run-desk-agent -H "Content-Type: application/json" \
     -d '{"scenario": "scenarios/clean_day.json"}'
   ```
5) List scenarios: `GET http://localhost:8000/scenarios`

## Docker (optional)
- Build: `docker build -t desk-agent-service .`
- Run: `docker run -p 8000:8000 -e SERVICE_ENV=prod desk-agent-service`

## Packaging / distribution
- Build wheel/sdist: `python -m build` (requires `pip install build`)
- Install from wheel: `pip install dist/transient-*.whl`
- CLI entrypoint: `desk-agent-service` (uses config/env for host/port)

## Config reference
- `SERVICE_ENV` (dev/stage/prod), `SERVICE_VERSION`
- `SERVICE_LOG_LEVEL` (INFO/DEBUG), `SERVICE_LOG_FORMAT` (json/text)
- `SERVICE_SCENARIOS_PATH`, `SERVICE_LOGS_PATH`, `SERVICE_AUDIT_LOG_PATH`
- `SERVICE_PORT`, `SERVICE_HOST`, `SERVICE_REQUEST_TIMEOUT_S`, `SERVICE_MAX_BODY_BYTES`

## Troubleshooting
- Missing scenarios path → ensure `scenarios/` exists or set `SERVICE_SCENARIOS_PATH`.
- Logging not writing → check `logs/service.log` path permissions.
- API errors → inspect response `request_id` and grep in logs.
