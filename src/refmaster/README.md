# Refmaster

Deterministic reference master normalization layer for Week 3. It converts noisy identifiers (“Apple Inc NASDAQ”, `AAPL.OQ`, `US0378331005`, etc.) into canonical equity records so downstream agents (OMS, Pricing, Desk) operate on consistent data even while real reference feeds are unavailable.

## Why it exists
- **Migration pressure**: The original spec describes a mid-migration scenario where reference mismatches block trade flow. Refmaster acts as the stopgap lookup table and normalizer so OMS/Pricing can keep running even with placeholder data.
- **Traceable decisions**: Every normalization result carries confidence scores and “reason” tags so downstream components (and humans) can see why a ticker was chosen and flag ambiguities.
- **Deterministic behavior**: No LLM is required at runtime; results depend entirely on the shipped seed data and heuristics, making regression testing trivial.

## Data & builder
- Seed data ships in `data/refmaster_data.json` (≈50 US equities). Fields align with the `RefMasterEquity` schema.
- `data/refmaster_builder.py` can regenerate that JSON (and optionally enrich with SEC CIK + LLM-provided identifiers when API keys are available). Identifiers remain placeholders when upstream keys are missing—see `src/refmaster/refmaster.md` for caveats.
- `load_equities(path)` reads CSV or JSON. By default it looks for `REFMASTER_DATA_PATH`, otherwise falls back to `data/refmaster_data.json`. CSV columns must match the schema headers.

## Schemas
```text
RefMasterEquity
  symbol: str
  isin: str
  cusip: str
  currency: str
  exchange: str
  pricing_source: str
  cik/name/country/sector/industry: optional

NormalizationResult
  equity: RefMasterEquity
  confidence: float (0–1)
  reasons: List[str]
  ambiguous: bool
```

## Normalization pipeline
1. **Parsing** – `_extract_identifiers()` scans the input for ISIN, CUSIP, CIK, ticker + exchange suffixes, and country clues like “US”.
2. **Scoring** – `_score()` assigns deterministic confidences: exact ISIN (1.0), CUSIP/CIK (0.95), symbol+exchange/country (~0.9), symbol substring (~0.7), exchange-only (~0.3). Reason tags (e.g., `isin_exact`, `symbol_exact`, `exchange_match`) capture which rules fired.
3. **Thresholding** – results below `reject` (default 0.4) are discarded. Ambiguity is flagged when multiple candidates fall in the `ambiguous_low`–`ambiguous_high` band (0.6–0.85).
4. **Tie-breaks** – when confidences tie, candidates with exchange and country matches win; shorter symbols beat longer ones, then alphabetical order.

All thresholds are configurable through the `NormalizerAgent` constructor.

## API snippets
```python
from src.refmaster import NormalizerAgent, normalize, resolve_ticker

# One-off (uses cached global agent)
results = normalize("AAPL US")

# With custom thresholds / data
agent = NormalizerAgent(thresholds={"reject": 0.2})
matches = agent.normalize("Apple Inc NASDAQ", top_k=3)

# Exact lookup
equity = resolve_ticker("AAPL")
```

`NormalizationResult` objects expose `equity`, `confidence`, `reasons`, and `ambiguous`. Downstream agents should warn users when `ambiguous` is `True` or no candidates pass the reject threshold.

## Configuration
- `REFMASTER_DATA_PATH`: overrides the default data file (CSV or JSON).
- `LLM_MODEL`, `OPENAI_MODEL`, etc.: only used by the builder when regenerating data; the runtime normalizer does not call an LLM.

## Production-pressure scenario guidance
Documented in `src/refmaster/refmaster.md`: identifier quality is best-effort. During migration, teams should treat Refmaster as an auditable reference cache and log all normalization decisions (the desk agent already does this). Plan to swap in real feeds once they are available, but until then, Refmaster guarantees a single source of truth for ticker/identifier mapping.

## Testing
`tests/refmaster/test_refmaster.py` covers:
- JSON and CSV loading paths.
- Exact identifier matches (ISIN/CUSIP/CIK), ticker + country, exchange-suffix formats (`AAPL.OQ`), company-name + exchange strings (“Apple Inc NASDAQ”).
- Reject threshold handling, ambiguity/tie-break ordering.
- Ensuring every result includes confidence and reasons across the spec examples (`AAPL US`, `AAPL.OQ`, `Apple Inc NASDAQ`, `US0378331005`).

Run via:
```bash
uv run pytest tests/refmaster/test_refmaster.py -q
```

## Limitations / next steps
- Data quality is limited by the seed JSON. Hooking into real vendor feeds (CUSIP/ISIN services) will improve accuracy.
- No fuzzy string metrics beyond simple substring checks. Token-based name matching could be added behind a feature flag if needed.

Despite those limitations, Refmaster keeps OMS/Pricing/Desk aligned during migration, surfaces ambiguity to the desk, and provides an expandable path once higher-quality data arrives.*** End Patch
