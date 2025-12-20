# Ticker Agent

![Status](https://img.shields.io/badge/status-production-green) ![Python](https://img.shields.io/badge/python-3.11+-blue)

Lightweight ticker Q&A helper that classifies a question, resolves a ticker, fetches a snapshot via `data_tools.fd_api.get_equity_snapshot`, and returns structured intent/summary/metrics. LLM classification is optional; heuristics are always available as fallback.

## Supported Intents

The ticker agent supports the following intents (see `src/ticker_agent/intents_data.json` for full definitions):

### 1. `price_performance_summary`

**Purpose**: Summarize recent price performance over short horizons (e.g., 1D/5D/1M/3M/YTD) for a ticker.

**Example Questions**:

- "Summarize 1M, 3M, and YTD returns for this ticker."
- "Give me recent performance for the stock over the last month, quarter, and year to date."
- "How has this equity performed over the last week and year to date?"

**Metrics**: `ticker`, `as_of`, `price`, `return_1d`, `return_5d`, `market_cap`, `sector`, `industry`

### 2. `volatility_comparison_convertible`

**Purpose**: Compare realized equity volatility over a lookback window to implied volatility at issuance of a convertible; allow placeholders when implied data is missing.

**Example Questions**:

- "Compare realized vol over the last 90 days to the implied vol at issuance of this convertible."
- "Check realized equity vol for the past 90 days versus the convert's issuance implied vol; use a placeholder if implied is missing."

**Metrics**: `ticker`, `as_of`, `price`, `return_5d` (as proxy for volatility)

### 3. `income_statement_summary`

**Purpose**: Summaries of multi-year income-statement metrics (revenue, operating income, net income, EPS).

**Example Questions**:

- "Summarize the last 4 years of revenue for NVDA."
- "Show revenue, operating income, and net income for the past four reporting years for this ticker."
- "Give me the income statement for the previous four fiscal years for the company."

**Metrics**: `ticker`, `as_of`, `price`, `income_statements` (list with `fiscal_year`, `total_revenue`, `operating_income`, `net_income`, `diluted_eps`, `currency`)

### 4. `dividend_overview`

**Purpose**: Provide dividend yield, recent payments, and upcoming ex-dividend/payment dates for a ticker.

**Example Questions**:

- "What is the dividend yield, next ex-date, and payout for this ticker?"
- "Give me dividend details: yield, last payment, next ex-dividend date for this company."

**Metrics**: `ticker`, `as_of`, `price`, `dividend_yield` (currently `None` - placeholder until dividend data source is integrated)

**Note**: Current data tools lack dividend feeds, so dividend fields are placeholders.

### 5. `fundamentals_risk_summary`

**Purpose**: Comprehensive analysis of company fundamentals and risk trends including revenue, profitability, liquidity, leverage, and cash flow metrics.

**Example Questions**:

- "Give me a quick explanation of TSLA's fundamentals and risk trends before my investor call in 10 min."
- "What are the key fundamentals and risk factors for this company?"
- "Analyze the financial health and risk trends for this ticker."
- "Summarize fundamentals and risk indicators for this stock."

**Metrics**:

- `ticker`, `as_of`, `price`, `market_cap`, `sector`, `industry`
- `income_statements` (list with revenue, operating income, net income, EPS)
- `balance_sheets` (list with `current_ratio`, `debt_to_equity`, `working_capital`, `cash_and_cash_equivalents`, `total_debt`, `total_equity`)
- `cash_flow_statements` (list with `operating_cash_flow`, `free_cash_flow`, `capital_expenditures`)

**Summary**: Multi-part summary covering:

- Revenue trends (with percentage change and growth status)
- Profitability (net income, operating margin)
- Liquidity risk (current ratio, cash position, trend)
- Leverage risk (debt-to-equity, trend)
- Cash flow (free cash flow status, trend)
- Explicit risk assessment with flagged risk factors

### 6. `generic_unhandled`

**Purpose**: Fallback when no intent fits; preserves details in slots.other.

**Example Questions**: Any unmapped or ambiguous questions.

**Metrics**: `ticker`, `as_of`, `price` (basic snapshot only)

## Usage

### Python API

The ticker agent can be used directly via the `run()` function:

```python
from src.ticker_agent import ticker_agent

# Single question
result = ticker_agent.run("What is the market cap and sector for AAPL?")
print(result["summary"])  # "AAPL price $150.00, sector Technology, market cap $2.5T."
print(result["intent"])   # "fundamentals_risk_summary"
print(result["metrics"])  # {"ticker": "AAPL", "price": 150.00, "market_cap": 2500000000000, ...}

# Batch processing
from src.ticker_agent.ticker_agent import run_many

questions = [
    "How is AAPL performing?",
    "What are TSLA's fundamentals and risk trends?",
    "Summarize the last 4 years of revenue for NVDA."
]
results = run_many(questions)
for result in results:
    print(f"{result['intent']}: {result['summary']}")
```

### Response Structure

All responses follow this structure:

```python
{
    "intent": str,           # Intent classification (e.g., "fundamentals_risk_summary")
    "summary": str,          # Human-readable summary (always present)
    "metrics": dict,         # Structured metrics data (always present, may be empty)
    "source": str,           # Data source identifier (e.g., "financialdatasets.ai")
    "system_prompt": str,    # System prompt used
    "tools_prompt": str      # Tools prompt describing available data sources
}
```

**Required Fields**: Both `summary` (string) and `metrics` (dict) are always present, even in error cases.

### Error Responses

When a question cannot be answered, the response includes an error summary:

```python
{
    "intent": "generic_unhandled",
    "summary": "Unable to answer: <error_type>. <error_message>",
    "metrics": {},
    "source": "financialdatasets.ai",
    "system_prompt": "...",
    "tools_prompt": "..."
}
```

Common error types:

- `invalid_ticker`: No ticker found in question
- `data_unavailable`: Failed to fetch data from API

## Service Layer Integration

The ticker agent is exposed as a **standalone REST endpoint** (`POST /ticker-agent`) and is also integrated into the **Desk Agent Orchestrator** for scenario-based workflows.

### Direct REST Endpoint

The ticker agent can be called directly via the service API:

```bash
curl -X POST http://localhost:8000/ticker-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "What are TSLA'\''s fundamentals and risk trends?"}'
```

**Response**:

```json
{
  "intent": "fundamentals_risk_summary",
  "summary": "TSLA fundamentals and risk analysis...",
  "metrics": {...},
  "source": "financialdatasets.ai"
}
```

### Via Desk Agent Orchestrator

Questions can be included in scenarios and processed as part of the orchestrator workflow:

```bash
# Scenario JSON with questions
{
  "name": "my_scenario",
  "trades": [...],
  "marks": [...],
  "questions": [
    {
      "question": "What are TSLA's fundamentals and risk trends?",
      "ticker": "TSLA"
    }
  ]
}

# Run via service API
curl -X POST http://localhost:8000/run-desk-agent \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "name": "my_scenario",
      "questions": [
        {"question": "What are TSLA's fundamentals?", "ticker": "TSLA"}
      ],
      "trades": [],
      "marks": [],
      "metadata": {}
    }
  }'
```

The orchestrator's response includes a `ticker_agent_results` section:

```json
{
  "ticker_agent_results": [
    {
      "question": "What are TSLA's fundamentals?",
      "intent": "fundamentals_risk_summary",
      "summary": "TSLA fundamentals and risk analysis...",
      "metrics": {...}
    }
  ],
  ...
}
```

### Direct Python Access

For direct access without the orchestrator, use the Python API:

```python
from src.ticker_agent import ticker_agent

result = ticker_agent.run("How is AAPL performing?")
```

## Configuration

- **Environment Variables** (loaded via `load_dotenv()`):
  - `LLM_MODEL` or `OPENAI_MODEL`: Enable LLM classifier; otherwise heuristics are used
  - Market data is always fetched via `data_tools.fd_api.get_equity_snapshot`; no direct API keys configured here

## Invocation by Other Agents

- Desk/OMS/Pricing should import `ticker_agent.run(question)` (or `run_many([...])`) and consume the returned dict
- Do not call market data directly from here; rely on `data_tools`
- The orchestrator uses `ticker_agent.run` as the default `ticker_runner`

## Notes

- **Heuristic ticker parsing**: Handles "AAPL US", "AAPL.OQ", uppercase tokens
- **Snapshots cached**: Via LRU to reduce repeated market data calls
- **Intent classification**: Uses LLM when `LLM_MODEL` is set, otherwise falls back to keyword-based heuristics
- **Financial statements**: For `fundamentals_risk_summary` and `income_statement_summary`, fetches income statements, balance sheets, and cash flow statements from FinancialDatasets.ai API

## Files

- `ticker_agent.py`: Core API and heuristics
- `classifier.py`: Optional LLM classifier (expects `(intent, confidence, slots)`)
- `prompts.py`: System/tools prompt strings
- `intents_data.json`: Intent definitions for classifier
- `intents_loader.py`: Loads intent definitions from JSON
- `intents_builder.py`: Script to regenerate intents (requires `LLM_API_URL` and `LLM_API_KEY`)

## Running the Intent Builder

To regenerate or update intents:

```bash
python -m src.ticker_agent.intents_builder
```

Requires `LLM_API_URL` and `LLM_API_KEY` environment variables.

---

## Testing

See **[TESTING.md](TESTING.md)** for a comprehensive happy path testing guide with example requests and expected responses for each intent.
