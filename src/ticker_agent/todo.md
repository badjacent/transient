# Week 2 - Ticker Agent TODO (implementation-ready)
Audience: implementation agent. Treat `data_tools` helpers as already available; keep all downstream calls to market data through `data_tools.fd_api`. Keep LLM usage optional; classifier stubs exist.

## Module Structure Setup
- [x] Ensure `src/ticker_agent/` includes importable stubs: `__init__.py`, `ticker_agent.py`, `prompts.py`, `classifier.py`, `intents_loader.py`, `intents_builder.py`, `intents_data.json`.
- [x] Ensure `tests/ticker_agent/` exists with `__init__.py` and `test_ticker_agent.py` placeholder.
- [x] Ensure any prompt or intent data files are checked in and loadable.

## Task 1: Core API (`ticker_agent.run`)
- [x] Expose `run(question: str) -> dict` that classifies intent, resolves ticker, fetches snapshot via `data_tools.fd_api.get_equity_snapshot`, and returns structured output with `intent`, `summary`, `metrics`, `source`, and optional `error` on failure.
- [x] Keep behavior deterministic without LLM; if LLM configured (`LLM_MODEL`/`OPENAI_MODEL`), call classifier; otherwise use heuristic fallbacks. On classifier failure, fall back silently to heuristics.
- [x] Heuristic intent coverage (align to current stubs): `price_performance_summary`, `financials_revenue_summary`, `dividend_overview`, `volatility_comparison_convertible`, `generic_unhandled`.
- [x] Ticker resolution: extract first 1–5 letter uppercase token; if none, return error response instructing user to provide a ticker.
- [x] Error handling: capture data fetch failures as `data_unavailable` with detail; return structured error payload, not exceptions.

## Task 2: Prompts & Intents
- [x] Maintain `SYSTEM_PROMPT` and `TOOLS_PROMPT` in `prompts.py`; ensure they describe available tools and expected output shape succinctly.
- [x] Ensure `intents_data.json` (or equivalent) lists supported intents with patterns/examples; loader and builder scripts should round-trip this file without breaking schema.
- [x] `classifier.classify_question` should accept model name and return `(intent, confidence, slots)`; slots may include `ticker`. If unavailable, heuristic mapping must still populate `intent` and best-effort `ticker`.

## Task 3: Metrics & Summaries
- [x] Implement metrics construction per intent using `EquitySnapshot` fields from `data_tools.schemas`: e.g., price, return_1d, return_5d, market_cap, sector/industry. For missing data (e.g., dividends), return `None` placeholders.
- [x] Implement concise summaries per intent; include ticker, price, and intent-relevant stats; avoid hallucinated data.

## Task 4: Configuration
- [x] Load environment via `load_dotenv()`; allow model selection via `LLM_MODEL`/`OPENAI_MODEL`.
- [x] Keep all external calls through `data_tools.fd_api`; do not inline API keys or endpoints here.

## Task 5: Testing (`tests/ticker_agent/test_ticker_agent.py`)
- [x] Unit: intent classification heuristics, ticker extraction, error responses for missing/invalid tickers, data fetch error handling.
- [x] Integration (with mocks for `fd_api`/classifier): verify `run` returns expected structure/fields and summaries per intent; ensure LLM path falls back to heuristics on failure.
- [x] Snapshot structure validation: metrics contain expected keys per intent; summaries are non-empty strings; errors are present when appropriate.

## Documentation
- [x] `src/ticker_agent/README.md`: overview, supported intents, expected inputs/outputs, example calls, configuration (LLM env vars), and how other agents (desk/oms/pricing) should invoke `ticker_agent.run`.
- [x] Keep prompts/intents schema documented in README or a brief comment header.

## Optional Enhancements
- [x] Add more intents (dividends with real data, risk/vol metrics, news sentiment) when data available.
- [x] Add batch `run_many` API.
- [x] Add caching of snapshots to reduce repeated API calls.
- [x] Add better ticker parsing (support “AAPL US”, “AAPL.OQ”, CIK/ISIN via refmaster hook).
