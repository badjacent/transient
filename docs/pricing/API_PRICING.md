# Pricing Agent API (Developer Notes)

## Modules
- `src.pricing.schema`: Mark/EnrichedMark/PricingSummary models.
- `src.pricing.config`: tolerance loader (env overrides: PRICING_OK_THRESHOLD, PRICING_REVIEW_THRESHOLD, PRICING_STALE_DAYS, PRICING_RETRY_COUNT, PRICING_RETRY_BACKOFF_MS).
- `src.pricing.normalizer`: MarketNormalizer(tolerances=None, refmaster=None); methods: `fetch_market_price`, `compare_mark_to_market`, `enrich_marks`.
- `src.pricing.pricing_agent`: PricingAgent(normalizer=None); methods: `run(marks_input) -> {enriched_marks, summary}`, `_audit` (env PRICING_AUDIT_LOG), `generate_report(payload, output_path=None, output_format="md"|"json")`.

## Inputs
- `marks_input`: CSV path, JSON/JSONL path, pandas DataFrame, or list of dicts matching `Mark` schema.
- `Mark` fields: ticker, internal_mark, as_of_date (YYYY-MM-DD), optional notes/source/position_id/portfolio_id/instrument_type/currency.

## Outputs
- `run`: dict with `enriched_marks` (list of EnrichedMark dicts) and `summary` (counts/averages/top tickers).
- `EnrichedMark`: mark + market_price, deviation_absolute/percentage, classification (OK/REVIEW_NEEDED/OUT_OF_TOLERANCE/NO_MARKET_DATA/STALE_MARK), market_data_date, error, explanation.
- Reports: Markdown or JSON via `generate_report`.

## Integration Notes
- Market data via `data_tools.fd_api.get_price_snapshot`.
- Optional refmaster validation (pass NormalizerAgent to MarketNormalizer).
- Audit log: set `PRICING_AUDIT_LOG` to a filepath to append JSONL entries per enriched mark.

## Error Handling
- Market fetch retries (configurable); classification when market data missing; audit failures are warned but non-fatal.
