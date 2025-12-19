# OMS Trade QA (Week 4)

Validates trades against reference master and market data using deterministic checks.

## Schema

- `Trade`: ticker, quantity, price, currency, counterparty, trade_dt, settle_dt (ISO).

## Agent

```python
from src.oms.oms_agent import OMSAgent
agent = OMSAgent()
result = agent.run({"ticker": "AAPL", "quantity": 100, "price": 190, "currency": "USD",
                    "counterparty": "MS", "trade_dt": "2024-06-05", "settle_dt": "2024-06-07"})
# result -> {status, issues, explanation}
```

## QA checks and thresholds

- `missing_field` (ERROR): any required field absent/empty.
- `identifier_mismatch` (ERROR/WARNING): normalization failure, unknown ticker, ambiguity, or low-confidence match.
- `currency_mismatch` (WARNING): trade currency differs from reference map.
- `price_tolerance` (WARNING/ERROR): deviation vs `get_price_snapshot`; default WARN >2%, ERROR >5% (configurable).
- `counterparty` (WARNING): not in approved allowlist.
- `settlement_date` (ERROR/WARNING): settle before trade, weekend settlement, earlier than configured T+N (ERROR), or non-standard long settlement (WARNING).

Responses:

- `status`: `ERROR` if any ERROR issue, `WARNING` if warnings only, else `OK`.
- `issues`: list of `{type, severity, message, field}`; all checks run (no early exit).
- `explanation`: concise summary of issues and recommended fixes.
- `metrics`: per-step timings plus total_ms (useful for performance tracking).
- `audit`: optional JSONL when `OMS_AUDIT_LOG` is set.

## Config (simple defaults)

- Thresholds: warning 2%, error 5% (override via constructor).
- Counterparties: default allowlist; override via constructor or `OMS_COUNTERPARTIES`.
- Ref currency map: defaults to USD; supply per-ticker currencies if needed.
- Settlement: default `OMS_SETTLEMENT_DAYS=2` (T+2); weekend settlement flagged.
- Audit: set `OMS_AUDIT_LOG` to a JSONL path to record each validation (trade + result).
- Performance budget: `OMS_PERF_BUDGET_MS` (default 30000).

### Environment keys

- `OMS_PRICE_WARNING_THRESHOLD`, `OMS_PRICE_ERROR_THRESHOLD`: float tolerances.
- `OMS_COUNTERPARTIES`: comma-separated allowlist.
- `OMS_SETTLEMENT_DAYS`: expected settlement lag (default 2).

## Scenarios

- `scenarios/scenarios.json` contains synthetic trades across valid cases, missing fields, identifier/currency/price/counterparty/settlement issues, and market-data failures.

## Example input/output

Input trade:

```json
{
  "ticker": "AAPL",
  "quantity": 100,
  "price": 190,
  "currency": "USD",
  "counterparty": "MS",
  "trade_dt": "2024-06-05",
  "settle_dt": "2024-06-07"
}
```

Possible output:

```json
{
  "status": "WARNING",
  "issues": [
    {
      "type": "price_tolerance",
      "severity": "WARNING",
      "field": "price",
      "message": "Price deviates 3.00% from market"
    }
  ],
  "explanation": "WARNING: 1 issue(s). WARNING price_tolerance on price: Price deviates 3.00% from market"
}
```
