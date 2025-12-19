# FinancialDatasets.ai API - Production Readiness Assessment

## Overview

This document outlines the issues discovered with the FinancialDatasets.ai API during development and testing that make it less suitable for enterprise, production use.

## Critical Issues


### 1. Unadjusted Prices Only

**Issue**: The API returns unadjusted historical prices, meaning corporate actions (stock splits, dividends, spinoffs) are not accounted for in historical price data.

**Impact**:
- Return calculations across corporate action dates are incorrect
- Historical price comparisons are invalidated by corporate actions
- Requires manual handling of corporate actions in application code
- No option to request adjusted prices

**Example Problem**:
- If a stock splits 2-for-1, historical prices before the split are not adjusted
- A 5D return calculation that spans the split date will be incorrect
- The API provides no indication that a corporate action occurred

**Production Impact**: **HIGH** - Financial calculations require adjusted prices for accuracy.

---

### 2. Lack of Trading Calendar Information

**Issue**: The API does not provide explicit trading calendar information or trading day indicators.

**Impact**:
- Cannot determine if a specific date is a trading day
- Must infer trading days from volume data (volume > 0)
- Difficult to calculate exact N-trading-day returns
- No way to know market holidays or early closures

**Workaround**: Filter by volume > 0 to exclude non-trading days, but this is:
- Inefficient (requires fetching data and filtering)
- Not guaranteed to be accurate (low volume days might be filtered)
- Adds complexity to application code

**Production Impact**: **MEDIUM** - Trading calendar is essential for accurate financial calculations.
