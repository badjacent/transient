# Week 2 Desk Agent

## What this agent does
- Classifies simple equity questions into hard-coded intents (fundamentals, performance, dividends placeholder, risk placeholder).
- Fetches a price/fundamentals snapshot via `get_equity_snapshot`.
- Returns both a short `summary` string and a `metrics` dict for downstream use.
- Handles common errors (invalid ticker, data unavailable) with clear summaries.

## Example
Input:
```json
{"question": "What is the market cap and sector?", "ticker": "AAPL"}
```
Output (shape):
```json
{
  "intent": "financials_revenue_summary",
  "summary": "AAPL price $<price>, sector <sector>, market cap $<cap>.",
  "metrics": {
    "ticker": "AAPL",
    "as_of": "<YYYY-MM-DD>",
    "price": <float>,
    "market_cap": <float>,
    "sector": "<string>",
    "industry": "<string|null>"
  },
  "source": "financialdatasets.ai"
}
```

## Running the builder
`python -m src.desk_agent.intents_builder` (requires `LLM_API_URL` and `LLM_API_KEY`).
