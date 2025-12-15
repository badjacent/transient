# Ticker Agent Intents

The ticker agent currently routes questions into lightweight intent buckets. Each intent maps to a fixed metrics payload and summary template, ensuring downstream agents can rely on consistent structure even when some data is missing.

## Supported Intents

1. **price_performance_summary**

   - **Purpose:** Questions about recent performance, returns, or price moves (e.g., “How has AAPL performed YTD?”).
   - **Metrics:** `ticker`, `as_of`, `price`, `return_1d`, `return_5d`.
   - **Summary Template:** Mentions price plus 1D/5D return multipliers.

2. **financials_revenue_summary**

   - **Purpose:** Fundamentals and high-level financial questions (market cap, sector, revenue trends).
   - **Metrics:** `ticker`, `as_of`, `price`, `market_cap`, `sector`, `industry`.
   - **Summary Template:** Price, sector, market cap sentence.

3. **dividend_overview**

   - **Purpose:** Dividend/yield/ex-div inquiries. Current data tools lack dividend feeds, so fields are placeholders.
   - **Metrics:** `ticker`, `as_of`, `price`, `dividend_yield=None`, `next_ex_date=None`.
   - **Summary Template:** Explicitly states dividend data unavailable from current source.

4. **volatility_comparison_convertible**

   - **Purpose:** Risk/volatility questions, especially for convertible issuance. Uses 5D returns as a proxy until implied vol data is wired.
   - **Metrics:** `ticker`, `as_of`, `price`, `return_5d`.
   - **Summary Template:** Highlights recent 5D return multiplier as the provisional metric.

5. **income_statement_summary**

   - **Purpose:** Multi-year income statement questions (e.g., "Summarize the last 4 years of revenue/EPS").
   - **Metrics:** `ticker`, `as_of`, `price`, `income_statements` (list of recent periods with revenue, operating income, net income, EPS, currency).
   - **Summary Template:** Calls out how many periods were retrieved and the most recent revenue figure (plus change vs. the oldest period when available).

6. **fundamentals_risk_summary**

   - **Purpose:** Comprehensive analysis of company fundamentals and risk trends (e.g., "Give me a quick explanation of TSLA's fundamentals and risk trends").
   - **Metrics:** `ticker`, `as_of`, `price`, `market_cap`, `sector`, `industry`, `income_statements`, `balance_sheets` (with current_ratio, debt_to_equity, working_capital, cash position), `cash_flow_statements` (with operating_cash_flow, free_cash_flow, capital_expenditures).
   - **Summary Template:** Multi-part summary covering revenue trends, profitability, liquidity (current ratio, cash), leverage (debt-to-equity), cash flow (FCF), and identified risk factors.

7. **news_sentiment_stub**

   - **Purpose:** Requests about news or sentiment. Acts as a stub until a news feed/LLM is integrated.
   - **Metrics:** `ticker`, `as_of`, `price`, `sentiment=None`, `headline_sample=None`.
   - **Summary Template:** Notes that sentiment isn’t available yet.

8. **generic_unhandled**
   - **Purpose:** Fallback when no heuristic or classifier intent matches. Still returns price snapshot metrics.
   - **Metrics:** `ticker`, `as_of`, `price`.
   - **Summary Template:** Default “ticker snapshot” sentence.

## Intent Structure

- **Intent ID:** `lower_snake_case` string identifying the handling block (matches `intents_data.json` entries).
- **Metrics Schema:** Deterministic dict keyed by `metrics` section in responses; downstream systems should avoid relying on absent keys.
- **Summary Template:** Short natural-language string tied to each intent to keep responses consistent.
- **Fallback Behavior:** When the classifier fails or no keywords match, `generic_unhandled` ensures we still return useful snapshot data without hallucinating unsupported analytics.

## Adding New Intents

1. Update `intents_data.json` with patterns/examples and re-run `intents_builder.py` if needed.
2. Extend `_classify_intent` in `ticker_agent.py` to recognize the new intent heuristically (and via classifier slots).
3. Add metric construction logic in `_build_metrics` and a summary template in `_summary`.
4. Update `tests/ticker_agent/test_ticker_agent.py` to assert the new intent’s structure.
