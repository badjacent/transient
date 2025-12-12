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

Checks:
- Missing fields
- Identifier via `refmaster.NormalizerAgent` (ambiguous/low confidence flagged)
- Currency mismatch (stub: warns if non-USD)
- Price tolerance vs `data_tools.fd_api.get_price_snapshot` (WARN >2%, ERROR >5% by default)
- Counterparty validity (simple allowlist)
- Settlement date ordering (settle >= trade)

## Config (simple defaults)
- Thresholds: warning 2%, error 5% (override via constructor).
- Counterparties: default allowlist; override via constructor.

## Scenarios
- `scenarios/scenarios.json` placeholder for synthetic trades (valid/invalid cases).
