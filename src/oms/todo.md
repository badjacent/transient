# Week 4 - OMS & Trade Capture QA TODO (implementation-ready)
Audience: implementation agent. Treat external dependencies as stubs (e.g., `refmaster.NormalizerAgent`, `data_tools.fd_api`, `data_tools.schemas.Trade`). Paths are repo-root-relative.

## Module Structure Setup
- [x] Ensure `src/oms/` exists with importable stubs: `__init__.py`, `schema.py`, `oms_agent.py`.
- [x] Ensure `tests/oms/` exists with `__init__.py` and `test_oms_agent.py` placeholder.
- [x] Ensure project-root `scenarios/` exists with `scenarios.json` placeholder for synthetic trades.

## Task 1: Define Trade Schema (`src/oms/schema.py`)
- [x] Define trade schema (Pydantic or equivalent) with required fields: `ticker` (str), `quantity` (float), `price` (float), `currency` (3-letter ISO str), `counterparty` (str), `trade_dt` (YYYY-MM-DD), `settle_dt` (YYYY-MM-DD).
- [x] Include optional fields if needed later, but required set must validate.
- [x] Add validation: date format, positive quantity/price, currency code format, required fields. Reuse `data_tools.schemas.Trade` if compatible; otherwise implement OMS-specific schema with same fields.

## Task 2: Build QA Checks (orchestrated in `oms_agent`)

### 2.1 Missing Fields
- [x] Check required fields and return specific error per missing field; distinguish optional vs required.

### 2.2 Identifier Mismatch
- [x] Use `refmaster.NormalizerAgent` stub to validate ticker; handle unknown/invalid/ambiguous/format issues (e.g., "AAPL" vs "AAPL.OQ"); include confidence scores and warnings for low-confidence matches.

### 2.3 Currency Mismatch
- [x] Load currency from reference master for ticker; compare with trade currency; handle missing currency in ref data; emit warnings/errors on mismatch.

### 2.4 Price Out of Tolerance
- [x] Use `data_tools.fd_api.get_price_snapshot` or `get_equity_snapshot` stub to fetch market price (prefer using `trade_dt` for historical price if available).
- [x] Compute percentage deviation; configurable thresholds: ERROR >5%, WARNING 2–5%, OK <2% (make configurable).
- [x] Handle no market data, future trade dates, stale historical data; log structured errors instead of crashing.

### 2.5 Counterparty Validation
- [x] Validate against configured list of valid counterparties (config-driven); check format/typos; warn on suspicious names.

### 2.6 Settlement Date
- [x] Validate format; ensure `settle_dt >= trade_dt`; apply settlement rules (default T+2 equities US, T+1 optional overrides, custom per instrument); adjust for weekends/holidays.

## Task 3: Build Trade QA Agent (`src/oms/oms_agent.py`)

### 3.1 Core Agent Structure
- [x] Implement `OMSAgent` with dependencies injected (refmaster normalizer, FD API client/stub, config). Provide overrides for tests.

### 3.2 Run Method
- [x] Implement `run(trade_json)` accepting dict or JSON string; parse/validate via schema; run all checks; return structured response:
  ```python
  {
    "status": "OK" | "WARNING" | "ERROR",
    "issues": [
      {"type": "identifier_mismatch|currency_mismatch|price_tolerance|counterparty|missing_field|settlement_date",
       "severity": "ERROR|WARNING",
       "message": "...",
       "field": "ticker|currency|price|..."}
    ],
    "explanation": "Human-readable summary"
  }
  ```
- [ ] Overall status rules: ERROR if any ERROR issues; WARNING if no ERROR but at least one WARNING; else OK. Collect all issues (no early exit).

### 3.3 Initialization
- [ ] Initialize refmaster normalizer stub; load config (price tolerances, counterparties, settlement rules, API keys/paths).

### 3.4 Explanation Generation
- [x] Produce concise, actionable summary with counts/types of issues and recommendations for fixes.

## Task 4: Build Synthetic Test Cases (`scenarios/scenarios.json`)

### 4.1 Scenarios File
- [x] Create ~20 test cases with structure:
  ```json
  {"name": "...", "trade": {...}, "expected_status": "OK|WARNING|ERROR", "expected_issues": [{"type": "...", "severity": "...", "field": "..."}], "description": "..."}
  ```

- [ ] Valid trades (3–5): normal equity, valid multi-currency if allowed, standard settlement.
- [ ] Missing fields (3–4): missing ticker/quantity/price/currency/counterparty/dates.
- [ ] Identifier mismatches (2–3): invalid ticker, ambiguous ticker, format issues.
- [ ] Currency mismatches (2): wrong currency vs ref, bad currency code format.
- [ ] Price tolerance (3–4): >5% high/low, 2–5% high/low, stale price data.
- [ ] Counterparty issues (1–2): invalid format, suspicious name.
- [ ] Settlement issues (2–3): settle before trade, non-standard T+1/T+3, weekend/holiday settle.

## Testing
- [ ] Unit: each QA check individually.
- [ ] Integration: `OMSAgent.run` with valid trades, each error type, multiple errors in one trade, edge cases (missing data, API failures).
- [ ] Scenario-driven: run all `scenarios.json` cases and assert expected status/issues.
- [ ] Error handling: market data API failures, missing ref data, invalid JSON input, network timeouts.
- [ ] Performance: batch of trades completes in <30s.

## Documentation
- [x] `src/oms/README.md`: OMS agent overview, usage examples, config options, response format, integration guide.
- [ ] Document QA checks and thresholds; provide example trade JSON inputs/outputs; document error codes/messages.

## Integration Points
- [x] Refmaster: ticker normalization, ambiguous handling, confidence usage (stub).
- [x] FD API: price fetch (`get_price_snapshot`/`get_equity_snapshot` stub), handle API errors, optional caching.
- [ ] data_tools.schemas.Trade: ensure compatibility or map to OMS schema; handle Pydantic validation errors.

## Production Readiness
- [ ] Logging: validation results, API calls, errors/warnings.
- [ ] Metrics/telemetry (optional): validation time, error rates by type, API call success rates.
- [ ] Config support: price tolerances, counterparties, settlement rules, API endpoints/keys.
- [ ] Audit trail: log all validated trades, store validation results, timestamp validations.

## Evaluation Criteria
- [ ] Catch 80%+ of scripted scenario errors; explanations are clear/actionable; structured output consistent; performs batch validation <30s; works on real-world-like trades if available.

## Optional Enhancements
- [ ] Extend schema for options and bond/CDS; multi-currency with FX checks; historical price validation using `trade_dt`; external counterparty validation; batch validation endpoint; webhook for real-time validation; dashboard/UI for results.
