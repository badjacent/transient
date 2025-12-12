# Service Architecture (Week 7)

- FastAPI service in `src/service/api.py`.
- Routes: `GET /health`, `POST /run-desk-agent` (invokes `DeskAgentOrchestrator`).
- Orchestrator composes Refmaster, OMS, Pricing, Ticker, and market data tools.
- Config: `src/service/config.py` (env/file/defaults). Scenario path defaults to `scenarios/`.
- Entry: `src/service/main.py` (uvicorn).
