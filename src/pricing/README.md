# Pricing Agent (Week 5)

Validates internal EOD marks against market data via `data_tools.fd_api`, classifies deviations, and produces summaries/reports.

## Components
- `schema.py`: `Mark`, `EnrichedMark`, `PricingSummary`.
- `config.py`: tolerance loader (defaults: ok=0.02, review=0.05, stale_days=5).
- `normalizer.py`: `MarketNormalizer` to fetch market prices and enrich marks.
- `pricing_agent.py`: `PricingAgent` orchestrates load → enrich → explain → summarize; `generate_report` builds Markdown.

## Usage
```python
from src.pricing.pricing_agent import PricingAgent, generate_report

agent = PricingAgent()
result = agent.run("data/marks.csv")  # or list[dict]/DataFrame/json path
markdown = generate_report(result)
```

## Classification
- `OK`: within ok_threshold.
- `REVIEW_NEEDED`: between ok_threshold and review_threshold.
- `OUT_OF_TOLERANCE`: above review_threshold.
- `NO_MARKET_DATA`: missing/failed fetch.
- `STALE_MARK`: mark older than stale_days.

## Config
- `config/tolerances.yaml` or env vars `PRICING_OK_THRESHOLD`, `PRICING_REVIEW_THRESHOLD`, `PRICING_STALE_DAYS`.

## Notes
- Refmaster integration can be added for ticker validation.
- Market data calls flow through `data_tools.fd_api`; no direct API keys here.
