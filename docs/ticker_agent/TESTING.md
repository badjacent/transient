# Ticker Agent - Happy Path Testing Guide

## Prerequisites

1. **Service Running**: Ensure the service is running on `http://localhost:8000`

   ```bash
   python3 -m src.service.main
   # Or: uvicorn src.service.api:app --reload --port 8000
   ```

2. **API Keys Configured**: Check your `.env` file has:

   ```bash
   FD_API_KEY=your_financial_datasets_api_key
   # Optional (for LLM classification):
   ANTHROPIC_API_KEY=your_anthropic_api_key
   # Or: LLM_MODEL=claude-3-5-sonnet-20241022
   ```

3. **Verify Service Health**:
   ```bash
   curl http://localhost:8000/health | jq
   ```

## Happy Path Test Cases

### Test 1: Basic Price & Fundamentals Query

**Request**:

```bash
curl -X POST http://localhost:8000/ticker-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the market cap and sector for AAPL?"}'
```

**Expected**:

- `intent`: `fundamentals_risk_summary` or `price_performance_summary`
- `summary`: Contains price, market cap, sector
- `metrics`: Has `ticker`, `price`, `market_cap`, `sector`, `as_of`
- `source`: `"financialdatasets.ai"`

**Verify**:

- Response has both `summary` (string) and `metrics` (dict)
- Price is a reasonable number (e.g., 150-200 for AAPL)
- Market cap is a large number
- Sector is a valid string

---

### Test 2: Income Statement Summary

**Request**:

```bash
curl -X POST http://localhost:8000/ticker-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "Summarize the last 4 years of revenue for NVDA"}'
```

**Expected**:

- `intent`: `income_statement_summary`
- `summary`: Mentions revenue, fiscal years, change over time
- `metrics`: Has `income_statements` array with:
  - `fiscal_year` (or `fiscal_period`)
  - `total_revenue`
  - `net_income`
  - `diluted_eps`
  - `currency`

**Verify**:

- At least 1 income statement in the array
- Revenue values are positive numbers
- Currency is present (e.g., "USD")

---

### Test 3: Fundamentals & Risk Analysis

**Request**:

```bash
curl -X POST http://localhost:8000/ticker-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "Give me a quick explanation of TSLA'\''s fundamentals and risk trends"}'
```

**Expected**:

- `intent`: `fundamentals_risk_summary`
- `summary`: Multi-part summary covering:
  - Revenue trends
  - Profitability (net income, operating margin)
  - Liquidity risk (current ratio, cash)
  - Leverage risk (debt-to-equity)
  - Cash flow (free cash flow)
  - Risk assessment section
- `metrics`: Has:
  - `income_statements` array
  - `balance_sheets` array (with `current_ratio`, `debt_to_equity`, `working_capital`, `cash_and_cash_equivalents`)
  - `cash_flow_statements` array (with `operating_cash_flow`, `free_cash_flow`)

**Verify**:

- Summary mentions "Risk Assessment"
- Balance sheets have calculated ratios (current_ratio, debt_to_equity)
- Cash flow statements have free_cash_flow
- Risk factors are flagged if present (e.g., "⚠️ Key Risk Factors")

---

### Test 4: Price Performance

**Request**:

```bash
curl -X POST http://localhost:8000/ticker-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "How has MSFT performed over the last 5 days?"}'
```

**Expected**:

- `intent`: `price_performance_summary`
- `summary`: Mentions price and returns (1D/5D)
- `metrics`: Has `return_1d`, `return_5d`, `price`

**Verify**:

- Returns are percentages (e.g., 0.02 for 2%)
- Price is current market price
- Summary mentions performance trend

---

### Test 5: Ticker Extraction (Various Formats)

**Test Cases**:

```bash
# Standard ticker
curl -X POST http://localhost:8000/ticker-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "What is AAPL price?"}'

# Ticker with exchange suffix
curl -X POST http://localhost:8000/ticker-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "Show me fundamentals for AAPL US"}'

# Ticker after preposition
curl -X POST http://localhost:8000/ticker-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "Summarize revenue for NVDA"}'
```

**Expected**: All should extract the ticker correctly and return valid responses.

---

### Test 6: Error Handling

**Invalid Ticker**:

```bash
curl -X POST http://localhost:8000/ticker-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the price?"}'
```

**Expected**:

- `intent`: `generic_unhandled`
- `summary`: Contains "Unable to answer: invalid_ticker"
- `metrics`: Empty dict `{}`

**No Ticker in Question**:

```bash
curl -X POST http://localhost:8000/ticker-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the weather today?"}'
```

**Expected**: Similar error response with `invalid_ticker` or `generic_unhandled`.

---

## Quick Test Script

Save this as `test_ticker_agent.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:8000"

echo "=== Test 1: Basic Fundamentals ==="
curl -X POST $BASE_URL/ticker-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the market cap and sector for AAPL?"}' | jq '.intent, .summary'

echo -e "\n=== Test 2: Income Statement ==="
curl -X POST $BASE_URL/ticker-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "Summarize the last 4 years of revenue for NVDA"}' | jq '.intent, .summary'

echo -e "\n=== Test 3: Fundamentals & Risk ==="
curl -X POST $BASE_URL/ticker-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "Give me a quick explanation of TSLA'\''s fundamentals and risk trends"}' | jq '.intent, .summary'

echo -e "\n=== Test 4: Performance ==="
curl -X POST $BASE_URL/ticker-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "How has MSFT performed?"}' | jq '.intent, .summary'
```

Make it executable and run:

```bash
chmod +x test_ticker_agent.sh
./test_ticker_agent.sh
```

---

## Using jq for Better Output

Install `jq` for pretty JSON output:

```bash
# macOS
brew install jq

# Then use:
curl -X POST http://localhost:8000/ticker-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "What are TSLA'\''s fundamentals?"}' | jq
```

---

## What to Check

For each successful response, verify:

1. **Structure**:

   - ✅ `summary` is a non-empty string
   - ✅ `metrics` is a dict (may be empty for errors)
   - ✅ `intent` is a valid intent name
   - ✅ `source` is "financialdatasets.ai"

2. **Content Quality**:

   - ✅ Summary is readable and informative
   - ✅ Metrics contain expected fields for the intent
   - ✅ Ticker is correctly extracted
   - ✅ Financial data is reasonable (not null/zero unless expected)

3. **Error Handling**:
   - ✅ Invalid questions return error summaries
   - ✅ Missing tickers are detected
   - ✅ API failures are handled gracefully

---

## Common Issues

### Issue: All fields are null

**Cause**: Missing or invalid `FD_API_KEY`
**Solution**: Check `.env` file has valid `FD_API_KEY`

### Issue: Intent classification wrong

**Cause**: LLM not configured or heuristics not matching
**Solution**:

- Check `ANTHROPIC_API_KEY` is set for LLM classification
- Or verify heuristic keywords match your question

### Issue: Financial statements missing

**Cause**: API doesn't have data for that ticker/period
**Solution**: Try a different ticker (AAPL, MSFT, NVDA, TSLA are good test cases)

### Issue: Slow responses (>5s)

**Cause**: External API rate limits or network issues
**Solution**:

- Check API key rate limits
- Try again after a few seconds
- Use simpler questions (fewer financial statements)

---

## Next Steps

After happy path testing:

1. Test edge cases (invalid tickers, missing data)
2. Test different intents systematically
3. Test batch processing (if implementing)
4. Load test with multiple concurrent requests
5. Test error recovery and retry logic
