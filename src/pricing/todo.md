# Week 5 - EOD Pricing Agent & Market Data Normalizer TODO (implementation-ready)
Audience: implementation agent. Treat all external modules as stubs (e.g., `data_tools.fd_api`, `refmaster.NormalizerAgent`). Paths are repo-root-relative.

## Module Structure Setup
- [x] Ensure `src/pricing/` contains importable stubs: `__init__.py`, `pricing_agent.py`, `normalizer.py`, `schema.py`.
- [x] Ensure `tests/pricing/` exists with `__init__.py`, `test_pricing_agent.py`, and `test_normalizer.py` placeholders.
- [x] Ensure `config/` (with `tolerances.yaml`) and `data/` (with `marks.csv`) exist; stub them if absent.
- [x] Ensure `examples/pricing_report.md` exists as a template output.

## Task 1: Create Synthetic EOD Mark File

### 1.1 Mark Schema
- [x] Define schema in code for marks: `{"ticker": str, "internal_mark": float, "as_of_date": "YYYY-MM-DD", "notes": str optional, "source": str optional, "position_id": str optional, "portfolio_id": str optional, "instrument_type": str optional, "currency": str optional}`.

### 1.2 Generate `data/marks.csv`
- [ ] Create ~50 instruments with diverse tickers (NASDAQ/NYSE, sectors, caps) and realistic marks: exact matches, <2% deviations, 2–5% deviations, >5% deviations, and stale dates.
- [ ] Vary `as_of_date` (recent and stale, avoid weekends), include mixed `notes` (explanations/empty/placeholders), allow missing optional fields.
- [x] CSV with headers; dates in `YYYY-MM-DD`; handle commas/special chars in notes.

## Task 2: Build Market Normalizer (`src/pricing/normalizer.py`)

### 2.1 Class Structure
- [x] Implement `MarketNormalizer` init: load tolerances from `config/tolerances.yaml`, wire FD API stub (`data_tools.fd_api`), optionally accept refmaster stub for ticker validation (dependency-injected for tests).

### 2.2 Market Data Fetch
- [x] Implement `fetch_market_price(ticker, as_of_date)` using FD API stub (`get_price_snapshot` or `get_equity_snapshot`); return close for the date.
- [x] Handle: no data for date, ticker missing, API errors/timeouts, weekends/holidays, future dates. Log and surface structured errors without throwing by default.

### 2.3 Mark vs Market Comparison
- [x] Implement `compare_mark_to_market(internal_mark, market_price, tolerance_cfg)` returning absolute and percentage deviations plus classification.
- [x] Classification rules (config-driven): `OK` (within ok_threshold), `REVIEW_NEEDED` (between ok_threshold and review_threshold), `OUT_OF_TOLERANCE` (above review_threshold), `NO_MARKET_DATA` (missing market), `STALE_MARK` (mark older than stale_days).

### 2.4 Enrichment
- [x] Implement `enrich_marks(marks)` accepting DataFrame or list[dict]:
  - [x] For each mark: fetch market price; compare; attach `market_price`, `deviation_absolute`, `deviation_percentage`, `classification`, `market_data_date` (used date), and any fetch/validation error objects.
  - [ ] Process efficiently (batch/caching if available) and log progress for larger sets.

## Task 3: Build Pricing Agent (`src/pricing/pricing_agent.py`)

### 3.1 Class Structure
- [x] Implement `PricingAgent` with injected `MarketNormalizer` and config; allow dependency overrides for tests.

### 3.2 Main Run Method
- [x] Implement `run(marks_input)`:
  - [x] Accept CSV path, DataFrame, list[dict], or JSON path.
  - [x] Load/validate against mark schema.
  - [x] Enrich via normalizer.
  - [x] Generate explanations per mark.
  - [x] Aggregate results and return structured report payload.

### 3.3 Explanation Generation
- [x] For each classification:
  - [x] `OUT_OF_TOLERANCE`: quantify deviation, list plausible causes (stale/corp action/error), recommend review/update/investigate.
  - [x] `REVIEW_NEEDED`: note moderate deviation, suggest verification.
  - [x] `NO_MARKET_DATA`: explain absence, suggest alternative source/manual review.
  - [x] `STALE_MARK`: call out age, recommend refresh.
  - [x] Include specific numbers/dates; keep concise, audit-friendly tone.

### 3.4 Aggregation
- [x] Aggregate counts by classification; compute totals, avg deviation (where market present), max deviation, and tickers with most issues; build summary section.

### 3.5 Report Generation
- [x] Implement `generate_report(enriched_marks, output_path=None)`:
  - [x] Markdown structure: executive summary; summary stats; findings by classification; per-ticker details with explanations; recommendations; timestamp and tolerances used.
  - [ ] Optionally emit JSON/CSV alongside Markdown; pretty-print as needed.

## Configuration (`config/tolerances.yaml` + loader)
- [x] Define keys: `ok_threshold` (e.g., 0.02), `review_threshold` (e.g., 0.05), `stale_days` (e.g., 5), optional per-instrument-type or per-ticker overrides.
- [x] Implement loader that pulls YAML, validates presence/types/ranges, falls back to sane defaults if missing.

## Testing
- [x] Unit: `MarketNormalizer` fetch, comparison, classification, edge cases (missing data, API errors, weekends), tolerance loading.
- [x] Integration: `PricingAgent.run` with marks covering all classifications, missing market data, stale marks, batch processing, and report generation.
- [ ] Scenario: run against `data/marks.csv`; assert processing/completion, correct classifications, explanations present, report created.
- [x] Error handling: API failures (timeouts, invalid key, rate limits, bad tickers), invalid inputs (malformed CSV, missing fields, bad dates, negative/zero prices).

## Documentation
- [x] `src/pricing/README.md`: overview, usage examples, config guide, schema, report format, integration notes.
- [x] `examples/pricing_report.md`: sample output including all classification types and explanations in auditor-friendly format.
- [ ] API docs: public methods, config schema, return formats, code examples.

## Integration Points
- [x] FinancialDatasets: use `data_tools.fd_api` stub (`get_price_snapshot`/`get_equity_snapshot`); handle API errors gracefully; optional price caching for perf.
- [ ] Refmaster (optional): use `refmaster.NormalizerAgent` stub to validate tickers and handle ambiguity/confidence where available.
- [x] Data loading: support CSV path, DataFrame, list[dict], JSON path; validate schema and emit clear errors on invalid input.

## Production Readiness
- [ ] Logging: mark processing progress, API calls/responses, classification decisions, errors/warnings, performance metrics (timings).
- [ ] Performance: optimize batch work (parallel where safe given rate limits; cache market data; efficient DataFrame ops); target 50 marks in <30s; add basic perf monitoring.
- [ ] Error recovery: retries for API calls (configurable), continue on partial failures, report which marks failed and why.
- [ ] Audit trail: log inputs, market data fetched, classifications, explanations, timestamps; optional persistence to file/db.

## Evaluation Criteria
- [ ] Functionality: processes all marks in `data/marks.csv`, classifies correctly, generates actionable explanations, and produces an audit-friendly report.
- [ ] Quality: concise explanations, professional report formatting, flexible config, clear errors.
- [ ] Performance: completes 50 marks in reasonable time (<30s), respects rate limits, efficient memory use.

## Optional Enhancements
- [ ] Advanced: options/bond/CDS validation; multi-currency with FX checks; historical trend analysis; automated mark update suggestions; portfolio system integration.
- [ ] Reporting: additional formats (HTML, PDF, JSON, Excel/CSV), charts/visualizations (deviation histogram, time series, heatmap).
- [ ] AI/LLM: richer explanations, pattern analysis across marks, root-cause suggestions, natural-language summaries.
- [ ] Configuration: per-portfolio/per-instrument tolerances, rules engine, alert thresholds/notifications.
- [ ] Data quality: detect duplicates, missing fields, type issues, and outliers prior to comparison.
