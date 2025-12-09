# Equity Snapshot Output

This document describes how `snapshot_output.json` was generated using the FinancialDatasets.ai API.

## Overview

The snapshot output contains equity market data for three companies: Microsoft (MSFT), Apple (AAPL), and IBM. The data includes current prices, returns, market capitalization, sector, and industry information.

## Code Used to Generate Snapshots

The following Python script was used to generate the snapshot data:

```python
"""Generate equity snapshots for MSFT, AAPL, and IBM."""

import json
from pathlib import Path
from src.data_tools.fd_api import get_equity_snapshot

# Run get_equity_snapshot for each ticker
tickers = ["MSFT", "AAPL", "IBM"]
results = {}

for ticker in tickers:
    print(f"Fetching data for {ticker}...")
    try:
        snapshot = get_equity_snapshot(ticker, None)
        # Convert Pydantic model to dict for JSON serialization
        results[ticker] = snapshot.model_dump()
        print(f"  Success: {ticker}")
    except Exception as e:
        print(f"  Error for {ticker}: {e}")
        results[ticker] = {"error": str(e)}

# Write to JSON file
output_file = "examples/data_tools/snapshot_output.json"
output_path = Path(output_file)
output_path.parent.mkdir(parents=True, exist_ok=True)

with open(output_path, "w") as f:
    json.dump(results, f, indent=2)

print(f"\nResults written to {output_file}")
print(f"Total tickers processed: {len(tickers)}")
```

## Execution

The script was run using:

```bash
uv run python3 generate_snapshot_output.py
```

## Function Details

The `get_equity_snapshot()` function:

- **Parameters**:
  - `ticker`: Stock ticker symbol (e.g., "MSFT", "AAPL", "IBM")
  - `end_date`: Optional date object. If `None`, uses the previous weekday (most recent Monday-Friday)

- **Returns**: A dictionary containing:
  - `ticker`: Stock ticker symbol
  - `price`: Current stock price
  - `return_1d`: 1-day return multiplier (vs previous trading day)
  - `return_5d`: 5-day return multiplier (vs 5 trading days ago)
  - `market_cap`: Market capitalization
  - `sector`: Company sector
  - `industry`: Company industry (optional)
  - `date`: Date of the price data (YYYY-MM-DD format)
  - `source`: Data source ("financialdatasets.ai")

## Output Format

The `snapshot_output.json` file contains a JSON object keyed by ticker symbol. Each ticker entry includes:

- **Success case**: All fields listed above
- **Error case**: An `error` field containing the error message

## Data Source

- **API**: FinancialDatasets.ai
- **Endpoints used**:
  - `/prices` - Historical price data
  - `/company/facts` - Company information (market cap, sector, industry)

## Notes

- The function automatically uses the previous weekday if no date is specified
- Only trading days (volume > 0) are included in return calculations
- Prices are unadjusted (no corporate action adjustments)
- Returns are expressed as multipliers (e.g., 1.01 = up 1%, 0.99 = down 1%)
- If API credits are exhausted or data is unavailable, an error will be included in the output

## Example Output Structure

The output is a JSON object keyed by ticker symbol. Each entry contains:

- **Success case**: All equity snapshot fields
- **Error case**: An `error` field with the error message

Example (from actual run):

```json
{
  "MSFT": {
    "ticker": "MSFT",
    "price": 490.37,
    "return_1d": 0.9986762250010184,
    "return_5d": 1.0007551020408163,
    "market_cap": 3649446076158.1,
    "sector": "Information Technology",
    "industry": "Software",
    "date": "2025-12-09",
    "source": "financialdatasets.ai"
  },
  "AAPL": {
    "ticker": "AAPL",
    "price": 278.42,
    "return_1d": 1.0019072294792906,
    "return_5d": 0.972850204409658,
    "market_cap": 4106200735170.0,
    "sector": "Information Technology",
    "industry": "Technology Hardware, Storage & Peripherals",
    "date": "2025-12-09",
    "source": "financialdatasets.ai"
  },
  "IBM": {
    "ticker": "IBM",
    "price": 311.38,
    "return_1d": 1.0071155960928908,
    "return_5d": 1.0318112532308306,
    "market_cap": 289001430991.08,
    "sector": "Information Technology",
    "industry": "IT Services",
    "date": "2025-12-09",
    "source": "financialdatasets.ai"
  }
}
```

## Results

All three tickers were successfully processed:
- **MSFT**: Successfully retrieved snapshot data
- **AAPL**: Successfully retrieved snapshot data
- **IBM**: Successfully retrieved snapshot data (previously failed due to API credits, now working)

