# Week 2 Agent Deliverables

## Artifacts
- [ ] Create the `ticker_agent/` package scaffold (`__init__.py`, `ticker_agent.py`, `prompts.py`) under `week2/` (aka `src/ticker_agent/` in this repo) plus `tests/` and `examples/` folders.
- [x] Implement `prompts.py` with system prompt(s) and tool descriptions the agent uses.
- [ ] Implement `ticker_agent.py` exposing `run(question: str, ticker: str)` with the flow: parse question → call Week 1 data tools → build structured answer → generate NL explanation → handle missing/invalid tickers.
- [ ] Add placeholder logic to support business questions (e.g., 4-year revenue summaries, realized vs implied vol) by stitching Week 1 data + stubs where data is missing.
- [ ] Ensure agent responses always include structured fields (`summary`, `metrics`, `source` citations) and natural-language reasoning.
- [ ] Implement error handling for network failures, missing fields, empty results, and timeouts returning `{"status": "error", "reason": "..."}`.
- [ ] Add tests (`tests/test_ticker_agent.py`) covering happy path, unsupported ticker, missing data surfacing as errors, and question pattern routing.
- [ ] Create example outputs under `examples/` demonstrating at least two question types and the production-pressure scenario.
- [x] Write README describing objectives, API (`run` signature), supported question patterns, error modes, configuration, and sample inputs/outputs; align naming to “Week 2 agent”.
- [ ] Document expected inputs (questions, tickers) and outputs (structured JSON + narrative) for future agent integration.

## Non-Artifacts (Evaluation Checklist / Tests)
- [ ] Tests assert answers remain grounded in real data (call Week 1 tools) and include source citations.
- [ ] Tests ensure `run` returns both structured data and human-readable explanation for each supported question pattern.
- [ ] Tests validate error handling paths (invalid ticker, timeouts simulated via mocks) return `{"status": "error", ...}`.
