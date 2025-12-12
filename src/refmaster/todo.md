# Week 3 - Reference Master Normalization TODO (implementation-ready)
Audience: implementation agent. Treat upstream data fetchers in `data_tools` as-is, but expose everything downstream through `refmaster` interfaces.

## Module Structure Setup
- [x] Ensure `src/refmaster/` has importable stubs: `__init__.py`, `schema.py`, `normalizer_agent.py` (or adapt existing `refmaster.py`), and data loader (e.g., `refmaster_builder.py` or similar).
- [x] Ensure `tests/refmaster/` exists with `__init__.py` and `test_refmaster.py` placeholder.
- [x] Ensure `data/seed_data.csv` exists for canonical symbols; if already present in `refmaster_data.json`, add loader/adapter to support both.

## Task 1: Define Schemas (`src/refmaster/schema.py`)
- [x] Define `Equity` (or equivalent) with required fields: `symbol`, `isin`, `cusip`, `currency`, `exchange`, `pricing_source`. Optional: `cik`, `name`, `country`, `sector`, `industry`.
- [x] Add validation (formats/lengths) and normalization helpers (uppercasing symbols/exchanges).
- [x] Export schema objects so downstream modules (OMS/Pricing/Desk) import from `refmaster.schema`, not `data_tools`.

## Task 2: Seed Data
- [x] Populate `data/seed_data.csv` (30–50 equities) using `data_tools` fetchers; keep generation logic in `refmaster_builder.py` or similar, but allow reuse of `data_tools` utilities.
- [x] Provide loader to read CSV into schema objects; support fallback to `refmaster_data.json` if CSV missing.
- [x] Document placeholder quality (e.g., synthetic ISIN/CUSIP if API keys absent).

## Task 3: Normalization Agent (`src/refmaster/normalizer_agent.py`)
- [x] Implement `NormalizerAgent` with API: `normalize(description_or_id: str, top_k: int = 5) -> list[NormalizationResult]`.
- [x] Support input variations (ticker, exchange-suffixed ticker, company name, ISIN, CUSIP, CIK, country suffix like “US”).
- [x] Return ranked matches with confidence scores [0.0–1.0] and reason features (which fields matched).
- [x] Surface `ambiguous` flag when multiple close scores; surface `unknown` when no candidates above threshold.
- [x] Include simple deterministic scoring (no LLM): exact ID matches > ticker > partial/name/exchange/context.

## Task 4: Ambiguity & Thresholds
- [x] Define configurable thresholds (e.g., `exact=1.0`, `high>=0.9`, `ambiguous_range=0.6–0.85`, `reject<0.4`); make overridable via kwargs/config.
- [x] If no match passes `reject`, return empty list with `unknown` indication.
- [x] Provide tie-break rules (prefer exchange/country matches, then length of symbol, then alphabetical).

## Task 5: Integration Facade
- [x] Expose a single entrypoint `refmaster.normalize(...)` for downstream callers (OMS/Pricing/Desk) that wraps data_tools access; downstream should not call `data_tools` directly for identifiers.
- [x] Provide helper `resolve_ticker(symbol)` returning canonical equity record (or error object) for use by OMS/Pricing.
- [x] Add minimal caching to avoid repeated loads of seed data.

## Task 6: Testing (`tests/refmaster/test_refmaster.py`)
- [x] Unit: schema validation, loader behavior (CSV vs JSON fallback), scoring logic for exact ticker/ISIN/CUSIP/CIK, exchange suffix handling, country suffix handling, name fuzzy/partial matches.
- [x] Ambiguity tests: multiple close candidates, low-confidence rejection, tie-break ordering.
- [x] Integration: `NormalizerAgent.normalize` end-to-end with sample inputs from spec (“AAPL US”, “AAPL.OQ”, “Apple Inc NASDAQ”, “US0378331005”).
- [x] Ensure deterministic outputs (stable ordering/confidence) for the implementation agent.

## Documentation
- [x] `src/refmaster/README.md`: overview, schema, data sources, placeholder caveats, usage examples, thresholds, and how other modules should import refmaster.
- [x] Note that underlying data_tool functions remain in `data_tools`, but downstream callers must go through refmaster APIs.
- [x] Add a brief note (in README or existing `refmaster.md`) about synthetic identifiers when API keys are missing.

## Production Readiness
- [x] Logging: inputs, selected candidates, confidence scores, reasons; warn on ambiguity/unknown.
- [x] Configurability: thresholds and data paths via env/config defaults; avoid hard-coded paths.
- [x] Error handling: clear errors for missing data files, malformed rows, and missing fields; keep partial results where possible.

## Optional Enhancements
- [ ] Add name-based fuzzy matching (token sort ratio) behind a flag.
- [ ] Add per-country/exchange weighting.
- [ ] Add batch normalize API.
- [ ] Add CLI: `python -m src.refmaster.normalize "AAPL US"`.
- [ ] Add export of normalized table for auditing (CSV/JSON).
