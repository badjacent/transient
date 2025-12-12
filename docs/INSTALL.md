# Install & Run

## Prereqs
- Python 3.10+ (uvicorn/fastapi installed via project deps)
- `.env` with any required keys (see config loaders)

## Steps
- `pip install -e .` (or `uv pip install .`)
- Run service: `python -m src.service.main`
- Health check: `GET http://localhost:8000/health`
- Run desk agent: `POST http://localhost:8000/run-desk-agent` with `{"scenario": "scenarios/scenarios.json"}` or `{"data": {...}}`
