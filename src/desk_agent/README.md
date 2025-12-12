# Desk Agent Orchestrator (Week 6)

Runs scenarios end-to-end: normalization, OMS QA, pricing validation, ticker Q&A, and market context aggregation.

## Usage
```python
from src.desk_agent.orchestrator import DeskAgentOrchestrator

agent = DeskAgentOrchestrator()
report = agent.run_scenario("scenarios/scenarios.json")  # or a scenario dict
```

## Flow
1. Load scenario (JSON/YAML or dict) with trades, marks, questions.
2. Normalize tickers via `refmaster`.
3. OMS checks on trades.
4. Pricing validation on marks.
5. Ticker agent answers questions.
6. Market snapshots via `data_tools.fd_api`.
7. Aggregate summary and narrative.

## Config
- Loaded via `src/desk_agent/config.py` with env overrides: `DESK_AGENT_MAX_RETRIES`, `DESK_AGENT_BACKOFF_MS`, `DESK_AGENT_ABORT_AFTER_RETRY`.
- Scenario/log paths configurable in config.
