# Desk Agent Service API

FastAPI wrapper around the Desk Agent orchestrator. OpenAPI is available at `/docs` and `/openapi.json`.

## Endpoints
- `GET /health`: returns status, version, env, and dependency checks.
- `POST /run-desk-agent`: run a scenario by name or inline data.
- `GET /scenarios`: list available scenario files (JSON/YAML).
- `GET /scenarios/{name}`: fetch a scenario file.
- `POST /validate-trade`: run OMS trade QA on a payload.
- `POST /validate-pricing`: validate marks via pricing agent.
- `GET /status`: lightweight status/version.

## Examples
Run desk agent by scenario name:
```bash
curl -X POST http://localhost:8000/run-desk-agent \
  -H "Content-Type: application/json" \
  -d '{"scenario": "scenarios/clean_day.json"}'
```

Inline scenario data:
```bash
curl -X POST http://localhost:8000/run-desk-agent \
  -H "Content-Type: application/json" \
  -d '{"data": {"name": "inline", "description": "demo", "trades": [], "marks": [], "questions": [], "metadata": {}}}'
```

Validate a trade:
```bash
curl -X POST http://localhost:8000/validate-trade \
  -H "Content-Type: application/json" \
  -d '{"trade": {"ticker": "AAPL", "quantity": 100, "price": 190, "currency": "USD", "counterparty": "MS", "trade_dt": "2024-06-05", "settle_dt": "2024-06-07"}}'
```
