# Desk Agent Orchestrator (Week 6)

Runs scenarios end-to-end: normalization, OMS QA, pricing validation, ticker Q&A, and market context aggregation.

## Usage
```python
from src.desk_agent.orchestrator import DeskAgentOrchestrator

agent = DeskAgentOrchestrator()
report = agent.run_scenario("scenarios/clean_day.json")  # or a scenario dict
agent.generate_report(report, "logs/last_report.json")
```

## Flow
1. Load scenario (JSON/YAML or dict) with trades, marks, questions, metadata.
2. Validate scenario schema; fail fast with descriptive errors.
3. Normalize tickers via `refmaster`; surface ambiguity/unknowns in `data_quality`.
4. OMS checks on trades.
5. Pricing validation on marks (maps `as_of` → `as_of_date` for the pricing agent).
6. Ticker agent answers questions.
7. Market snapshots via `data_tools.fd_api` plus simple sector/market rollups.
8. Aggregate summary, narrative, and execution metadata.

## Report shape
- `scenario`: name/description/metadata/execution_date
- `data_quality`: ticker_normalizations, normalization_issues, confidence_scores
- `trade_issues`: per-trade status/issues with trade_id/ticker/counterparty
- `pricing_flags`: marks with classification/deviation/explanation
- `market_context`: snapshots, key_tickers, market_movements, sector_performance, as_of_date
- `ticker_agent_results`: question, intent, summary, metrics
- `narrative`: exec-ready one-liner
- `summary`: totals, percentages, overall_status, breakdowns, performance budget
- `execution_metadata`: timings, timestamp, agents_executed, trace, config

See `examples/combined_report_example.json` for a complete example.

## Config
- Loaded via `src/desk_agent/config.py` (defaults → YAML/JSON → env). Environment keys:
  - `DESK_AGENT_SCENARIOS_PATH`, `DESK_AGENT_LOG_PATH`, `DESK_AGENT_LOG_LEVEL`
  - `DESK_AGENT_MAX_RETRIES`, `DESK_AGENT_BACKOFF_MS`, `DESK_AGENT_ABORT_AFTER_RETRY`, `DESK_AGENT_PARALLEL_TICKER`
  - `DESK_AGENT_PERF_BUDGET_MS`
  - Sub-agent overrides: `REFMASTER_DATA_PATH`, `OMS_PRICE_WARNING_THRESHOLD`, `OMS_PRICE_ERROR_THRESHOLD`, `OMS_COUNTERPARTIES`, `OMS_SETTLEMENT_DAYS`, `PRICING_TOLERANCE`, `PRICING_STALE_DAYS`, `TICKER_AGENT_MODEL`, `TICKER_AGENT_INTENTS`
- Paths are workspace-relative by default (`scenarios/`, `logs/`).

## Scenario schema
- Top-level: `{"name": str, "description": str, "trades": list, "marks": list, "questions": list, "metadata": dict}`
- Trade: `{"trade_id": str, "ticker": str, "quantity": number, "price": number, "currency": str, "counterparty": str, "trade_dt": ISO str, "settle_dt": ISO str, "side": "BUY"|"SELL" optional, "notes": optional}`
- Mark: `{"ticker": str, "internal_mark": number, "as_of": ISO str (or as_of_date), "source": optional, "notes": optional}`
- Question: `{"question": str, "ticker": optional, "intent_hint": optional, "context": optional dict}`

## Scenarios provided
- `clean_day.json`: happy path; all trades/marks clean.
- `bad_mark.json`: pricing deviations on marks.
- `wrong_ticker_mapping.json`: ambiguous/invalid tickers.
- `mis_booked_trade.json`: multiple OMS issues.
- `high_vol_day.json`: volatile pricing and context questions.
All files live in `scenarios/` and are validated by the orchestrator.

## Report structure (key sections)
- `scenario`: name/description/metadata/execution_date
- `data_quality`: normalization outcomes and issues
- `trade_issues`: per-trade status/issues with identifiers
- `pricing_flags`: mark classifications with deviations/explanations
- `market_context`: snapshots, market/sector aggregates, as_of_date
- `ticker_agent_results`: question/intent/summary/metrics
- `narrative`: exec-ready blurb
- `summary`: totals, percentages, breakdowns, overall_status
- `execution_metadata`: timings, timestamp, agents executed, trace, config

See `examples/combined_report_example.json` for a full example payload.

## CLI
- Run single scenario: `python -m src.desk_agent --scenario scenarios/clean_day.json`
- Smoke test all scenarios: `python -m src.desk_agent --smoke-all`
- Add `--output path.json` to save the result.
