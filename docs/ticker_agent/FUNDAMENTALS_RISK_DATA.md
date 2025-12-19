# Fundamentals and Risk Data from SEC Filings

## Overview

To answer questions like _"Give me a quick explanation of TSLA's fundamentals and risk trends before my investor call in 10 min"_, we need comprehensive financial statement data beyond just income statements. This document outlines the additional SEC data we can now extract.

## Available Financial Statements

### 1. Income Statements (Already Available)

**Purpose**: Revenue, profitability, and earnings trends

**Key Metrics**:

- Total revenue (trends over time)
- Operating income (operating leverage)
- Net income (bottom line profitability)
- Diluted EPS (earnings per share)
- Gross profit (margins)

**Use Cases**:

- Revenue growth trends
- Profitability analysis
- Margin compression/expansion

---

### 2. Balance Sheets (NEW)

**Purpose**: Financial health, liquidity, and leverage assessment

**Key Metrics**:

- **Liquidity Indicators**:

  - `current_ratio`: Current assets / Current liabilities (healthy if > 1.0)
  - `working_capital`: Current assets - Current liabilities
  - `cash_and_cash_equivalents`: Cash position

- **Leverage Indicators**:

  - `debt_to_equity`: Total debt / Total equity (lower is generally better)
  - `total_debt`: Long-term + short-term debt
  - `long_term_debt`: Long-term obligations
  - `short_term_debt`: Near-term obligations

- **Financial Structure**:
  - `total_assets`: Company size
  - `total_liabilities`: Total obligations
  - `total_equity`: Shareholders' equity

**Risk Assessment**:

- **High current ratio (>2.0)**: Strong liquidity, but may indicate inefficient capital use
- **Low current ratio (<1.0)**: Liquidity risk, may struggle to meet short-term obligations
- **High debt-to-equity (>1.0)**: High leverage, increased financial risk
- **Negative working capital**: Potential liquidity crisis

**Example for TSLA**:

- Current ratio trend: Is liquidity improving or deteriorating?
- Debt-to-equity: Is the company becoming more or less leveraged?
- Cash position: Can they fund operations and growth?

---

### 3. Cash Flow Statements (NEW)

**Purpose**: Cash generation, liquidity, and capital allocation

**Key Metrics**:

- **`operating_cash_flow`**: Cash generated from core business operations

  - Positive and growing = healthy business
  - Negative = burning cash, sustainability concern

- **`free_cash_flow`**: Operating cash flow - Capital expenditures

  - Available for dividends, buybacks, debt repayment, or growth
  - Negative FCF = consuming cash, may need external financing

- **`capital_expenditures`**: Investments in property, plant, equipment

  - High CapEx = growth mode or capital-intensive business
  - Trend indicates investment strategy

- **`financing_cash_flow`**: Cash from debt/equity issuance or repayments
- **`investing_cash_flow`**: Cash from investments/acquisitions

**Risk Assessment**:

- **Negative operating cash flow**: Business not generating cash, sustainability risk
- **Negative free cash flow**: Consuming cash, may need external financing
- **High CapEx relative to cash flow**: Aggressive growth or capital-intensive
- **Trends**: Is cash generation improving or deteriorating?

**Example for TSLA**:

- Operating cash flow trend: Is the business becoming more cash-generative?
- Free cash flow: Can they self-fund growth or need external capital?
- CapEx levels: Are they investing heavily in growth (factories, R&D)?

---

## Combined Analysis for "Fundamentals and Risk Trends"

### Quick Fundamentals Summary Should Include:

1. **Revenue Trends** (from Income Statements)

   - Growth rate over last 4 years
   - Recent acceleration/deceleration
   - Revenue stability

2. **Profitability Trends** (from Income Statements)

   - Operating margin trends
   - Net margin trends
   - EPS growth

3. **Financial Health** (from Balance Sheets)

   - Current ratio trend (liquidity)
   - Debt-to-equity trend (leverage)
   - Cash position trend

4. **Cash Generation** (from Cash Flow Statements)

   - Operating cash flow trend
   - Free cash flow trend
   - CapEx intensity

5. **Risk Indicators** (calculated from all statements)
   - **Liquidity Risk**: Low current ratio, negative working capital
   - **Leverage Risk**: High debt-to-equity, increasing debt
   - **Cash Flow Risk**: Negative operating cash flow, negative FCF
   - **Profitability Risk**: Declining margins, negative net income

---

## API Functions

### New Functions in `src/data_tools/fd_api.py`:

```python
from src.data_tools.fd_api import (
    get_income_statements,      # Already existed
    get_balance_sheets,          # NEW
    get_cash_flow_statements,    # NEW
)

# Get 4 years of annual balance sheets
balance_sheets = get_balance_sheets("TSLA", years=4, period="annual")

# Get 4 years of annual cash flow statements
cash_flows = get_cash_flow_statements("TSLA", years=4, period="annual")
```

### Schemas in `src/data_tools/schemas.py`:

- `BalanceSheet`: Assets, liabilities, equity, calculated risk metrics
- `CashFlowStatement`: Operating, investing, financing cash flows, free cash flow

---

## Example: TSLA Fundamentals & Risk Analysis

**Question**: "Give me a quick explanation of TSLA's fundamentals and risk trends before my investor call in 10 min."

**Data Needed**:

1. Income statements (4 years) → Revenue growth, profitability trends
2. Balance sheets (4 years) → Liquidity, leverage trends
3. Cash flow statements (4 years) → Cash generation trends
4. Equity snapshot → Current price, market cap, recent returns

**Key Metrics to Report**:

- **Revenue**: Growing at X% CAGR, but slowed to Y% in most recent year
- **Profitability**: Operating margin improved from X% to Y%, net margin at Z%
- **Liquidity**: Current ratio at X (trending up/down), cash position $Y billion
- **Leverage**: Debt-to-equity at X (trending up/down), total debt $Y billion
- **Cash Flow**: Operating cash flow $X billion (trending up/down), FCF $Y billion
- **Risk Factors**:
  - ✅ Strengths: [positive trends]
  - ⚠️ Concerns: [negative trends or risk indicators]

---

## Next Steps for Ticker Agent Integration

1. **Add new intent**: `fundamentals_risk_summary` for questions about fundamentals and risk
2. **Update `TOOLS_PROMPT`**: Include `get_balance_sheets()` and `get_cash_flow_statements()`
3. **Enhance `_build_metrics()`**: Include balance sheet and cash flow data when intent is `fundamentals_risk_summary`
4. **Create summary template**: Generate concise, actionable summary with:
   - Key trends (improving/deteriorating)
   - Risk indicators (highlight concerns)
   - Data sources (cite FinancialDatasets.ai)

---

## Data Source

All financial statement data comes from **FinancialDatasets.ai API**:

- Endpoints: `/financials/balance-sheets`, `/financials/cash-flow-statements`
- Same authentication and error handling as income statements
- Returns normalized Pydantic models for type safety
- Calculates risk metrics automatically (current ratio, debt-to-equity, FCF)

---

## Notes

- **Data Quality**: Same assumptions as income statements - data quality depends on FinancialDatasets.ai API
- **Period Support**: Both annual and quarterly periods supported
- **Trend Analysis**: Compare most recent vs. oldest period to identify trends
- **Risk Metrics**: Automatically calculated from raw data (no manual computation needed)
