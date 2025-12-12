# Refmaster (Week 3)

Deterministic reference master normalizer that maps free-form identifiers to canonical equities. Downstream agents (OMS/Pricing/Desk) should import from `src.refmaster`, not call `data_tools` directly for identifiers.

## Schema
- `Equity`: symbol, isin, cusip, currency, exchange, pricing_source; optional cik/name/country/sector/industry.
- `NormalizationResult`: equity, confidence (0-1), reasons[], ambiguous flag.

## Data loading
- Default data from `refmaster_data.json` in this package. If a CSV is provided, columns should align with `Equity` fields. Use `load_equities(path)` to override.

## API
```python
from src.refmaster import normalize, resolve_ticker, NormalizerAgent

results = normalize("AAPL US", top_k=3)
eq = resolve_ticker("AAPL")
agent = NormalizerAgent()  # custom thresholds/equities optional
```

## Behavior
- Supports inputs: ticker, exchange-suffixed ticker, company name fragments, ISIN, CUSIP, CIK, country suffix like "US".
- Scoring (deterministic): exact IDs > symbol + exchange/country > partial symbol/name > exchange-only.
- Thresholds (overridable): exact=1.0, high>=0.9, ambiguous range=0.6–0.85, reject<0.4. Results below reject are dropped; close scores in ambiguous range flagged.

## Caveats
- Identifiers may be synthetic if upstream APIs/keys are missing (see `refmaster.md` note).
- No LLM involvement; purely heuristic.

## Testing
- See `tests/refmaster/test_refmaster.py` for schema/loader/scoring/ambiguity coverage.
