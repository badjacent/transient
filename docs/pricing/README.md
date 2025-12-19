# Pricing Agent (Week 5)

## Business Context

The Pricing Agent validates internal End-of-Day (EOD) marks against external market data to:

1. **Detect pricing errors** before they impact NAV calculations
2. **Satisfy auditor requirements** for mark-to-market validation
3. **Flag data quality issues** (stale marks, missing market data)
4. **Provide audit trail** of pricing divergences

### Why This Matters

- Incorrect EOD pricing → wrong NAV → investor issues → regulatory risk
- Auditors require documented explanations for marks diverging >2-5% from market
- Manual validation of 100+ positions takes hours; agent completes in seconds
- Automated explanations reduce auditor response time from hours to minutes

---

## Components

- **`schema.py`**: `Mark`, `EnrichedMark`, `PricingSummary` data models
- **`config.py`**: Tolerance loader with defaults and environment variable overrides
- **`normalizer.py`**: `MarketNormalizer` fetches market prices and enriches marks
- **`pricing_agent.py`**: `PricingAgent` orchestrates load → enrich → explain → summarize; `generate_report` builds Markdown/JSON reports

---

## Data Schemas

### Input: Mark (CSV/JSON/DataFrame)

| Field           | Type   | Required | Description                                         |
| --------------- | ------ | -------- | --------------------------------------------------- |
| ticker          | string | Yes      | Market ticker symbol (e.g., "AAPL")                 |
| internal_mark   | float  | Yes      | Internal pricing mark                               |
| as_of_date      | string | Yes      | Mark date (YYYY-MM-DD format)                       |
| notes           | string | No       | Optional notes (trader override, model-based, etc.) |
| source          | string | No       | Mark source (e.g., "internal", "model")             |
| position_id     | string | No       | Internal position ID                                |
| portfolio_id    | string | No       | Portfolio ID                                        |
| instrument_type | string | No       | Instrument type (e.g., "equity")                    |
| currency        | string | No       | Currency code (e.g., "USD")                         |

### Output: EnrichedMark

All input fields plus:

| Field                      | Type   | Description                                                             |
| -------------------------- | ------ | ----------------------------------------------------------------------- |
| market_price               | float  | External benchmark price from FinancialDatasets.ai                      |
| deviation_absolute         | float  | internal_mark - market_price                                            |
| deviation_percentage       | float  | abs(deviation) / market_price                                           |
| classification             | string | OK \| REVIEW_NEEDED \| OUT_OF_TOLERANCE \| STALE_MARK \| NO_MARKET_DATA |
| market_data_date           | string | Date of market price (YYYY-MM-DD)                                       |
| market_data_source         | string | Always "financialdatasets.ai"                                           |
| fetch_timestamp            | string | ISO8601 timestamp of fetch                                              |
| tolerance_override_applied | bool   | True if per-instrument override was used                                |
| error                      | string | Error message if fetch failed                                           |
| explanation                | string | Human-readable explanation for auditors                                 |

---

## Classification States

- **OK**: Deviation ≤ ok_threshold (default: 2%)
- **REVIEW_NEEDED**: ok_threshold < deviation ≤ review_threshold (default: 2-5%)
- **OUT_OF_TOLERANCE**: Deviation > review_threshold (default: >5%)
- **STALE_MARK**: Mark as_of_date older than stale_days (default: >5 days)
- **NO_MARKET_DATA**: Market fetch failed or ticker invalid

**Classification Precedence** (highest to lowest):

1. NO_MARKET_DATA
2. STALE_MARK
3. OUT_OF_TOLERANCE / REVIEW_NEEDED / OK

---

## Configuration Reference

Configuration is loaded from `config/tolerances.yaml` with environment variable overrides.

### Global Thresholds

- `ok_threshold` (default: 0.02): Deviations ≤ this are classified as OK
- `review_threshold` (default: 0.05): Deviations between ok and review trigger REVIEW_NEEDED
- Deviations > review_threshold → OUT_OF_TOLERANCE

### Stale Detection

- `stale_days` (default: 5): Marks older than this many days are flagged as STALE_MARK

### Performance Configuration

- `perf_budget_ms` (default: 30000): Target completion time for entire run
- `max_workers` (default: 1): Number of parallel threads for market data fetching
- `retry_count` (default: 0): Number of retries for failed market data fetches
- `retry_backoff_ms` (default: 200): Milliseconds to wait between retries

### Per-Instrument Tolerance Overrides

Override thresholds for specific tickers (volatile stocks, crypto exposure, etc.):

```yaml
instrument_overrides:
  TSLA:
    ok_threshold: 0.05 # 5% tolerance instead of global 2%
    review_threshold: 0.10 # 10% review threshold instead of 5%
    reason: "high volatility stock"
```

### Environment Variable Overrides

- `PRICING_OK_THRESHOLD`: Override global ok_threshold
- `PRICING_REVIEW_THRESHOLD`: Override global review_threshold
- `PRICING_STALE_DAYS`: Override stale_days
- `PRICING_RETRY_COUNT`: Override retry_count
- `PRICING_RETRY_BACKOFF_MS`: Override retry_backoff_ms
- `PRICING_MAX_WORKERS`: Override max_workers
- `PRICING_PERF_BUDGET_MS`: Override perf_budget_ms
- `PRICING_AUDIT_LOG`: Path for audit log (JSONL format)
- `PRICING_METRICS_LOG`: Path for metrics log (JSONL format)

---

## Usage

### Python API

```python
from src.pricing.pricing_agent import PricingAgent, generate_report

# Initialize agent (uses config/tolerances.yaml)
agent = PricingAgent()

# Run validation on CSV file
result = agent.run("src/pricing/marks.csv")

# Or pass list of dicts
marks = [
    {"ticker": "AAPL", "internal_mark": 271.50, "as_of_date": "2025-12-17"},
    {"ticker": "MSFT", "internal_mark": 475.00, "as_of_date": "2025-12-17"},
]
result = agent.run(marks)

# Access results
summary = result["summary"]
print(f"Total marks: {summary['total_marks']}")
print(f"Flagged marks: {summary['flagged_count']}")
print(f"Pass rate: {summary['pass_rate']:.1%}")

# Generate Markdown report
report_md = generate_report(result, output_path="reports/eod_pricing.md")

# Generate JSON report
report_json = generate_report(result, output_format="json", output_path="reports/eod_pricing.json")
```

### CLI Usage

```bash
# Run from project root
python -m src.pricing.pricing_agent src/pricing/marks.csv

# With custom config
PRICING_OK_THRESHOLD=0.03 python -m src.pricing.pricing_agent src/pricing/marks.csv

# Generate report
python -m src.pricing.pricing_agent src/pricing/marks.csv --report examples/pricing_report.md
```

### Interpreting Results

```python
result = agent.run("src/pricing/marks.csv")

# Summary statistics
print(f"Total marks: {result['summary']['total_marks']}")
print(f"Pass rate: {result['summary']['pass_rate']:.1%}")
print(f"Flagged marks: {result['summary']['flagged_count']}")
print(f"Critical marks: {result['summary']['critical_count']}")
print(f"Data quality issues: {result['summary']['data_quality_issues']}")

# Classification breakdown
for cls, count in result['summary']['counts'].items():
    print(f"{cls}: {count}")

# Detailed marks
for mark in result['enriched_marks']:
    if mark['classification'] != 'OK':
        print(f"{mark['ticker']}: {mark['classification']}")
        print(f"  {mark['explanation']}")
```

---

## Responding to Auditor Requests

### Scenario: Auditor flags multiple marks diverging from market

**Timeline Expectation**: Complete response within 30 minutes

#### Step 1: Immediate Response (<2 minutes)

```bash
# Re-run pricing agent on current marks
python -m src.pricing.pricing_agent src/pricing/marks.csv --report audit_response.md
```

1. Send generated report to auditor as initial documentation
2. Explain tolerance framework (2% OK, 5% review threshold)
3. Highlight that automated validation has already flagged these marks

#### Step 2: Detailed Investigation (<30 minutes)

For each flagged mark, follow the explanation guidance:

**OUT_OF_TOLERANCE** (Critical - immediate action required):

- Verify internal mark source (trade capture, pricing model, trader override)
- Check for corporate actions (splits, dividends, spinoffs)
- Review pricing model assumptions if model-based
- Cross-check with alternative data sources if available
- Document findings and corrective action

**REVIEW_NEEDED** (Moderate - justification required):

- Document position-specific factors (illiquid security, pending corporate action)
- Verify mark is current and pricing source is reliable
- If justified, document rationale; if not justified, update mark

**STALE_MARK** (Data quality issue):

- Refresh marks with current EOD pricing
- Re-run agent validation
- Update auditor with refreshed results

**NO_MARKET_DATA** (System issue):

- Verify ticker mapping in reference master
- Check market data vendor connectivity
- If ticker is delisted/invalid, document and handle separately

#### Step 3: Tolerance Adjustment (if needed)

If auditor challenges tolerance thresholds:

1. **Update** `config/tolerances.yaml`:

```yaml
# Auditor requested tighter thresholds
ok_threshold: 0.015 # Was 0.02
review_threshold: 0.04 # Was 0.05
```

2. **Or add per-instrument overrides** for volatile names:

```yaml
instrument_overrides:
  TSLA:
    ok_threshold: 0.05
    review_threshold: 0.10
    reason: "high volatility name approved by auditor"
```

3. **Re-run validation**:

```bash
python -m src.pricing.pricing_agent src/pricing/marks.csv --report audit_response_revised.md
```

4. **Provide updated report** to auditor within 10 minutes

#### Step 4: Escalation Path

- **Critical marks** (OUT_OF_TOLERANCE): Escalate to PM and Head Trader immediately
- **Unexplained variances**: Escalate to Head of Operations if explanation cannot be documented within 30 minutes
- **Systemic issues** (multiple NO_MARKET_DATA): Escalate to technology team

---

## Troubleshooting

### Issue: "ticker_not_found" errors

**Cause**: Ticker not recognized by market data vendor

**Solution**:

1. Verify ticker mapping in reference master (`src/refmaster`)
2. Check if ticker is delisted or invalid
3. Update internal instrument database with correct ticker

### Issue: High rate of STALE_MARK classifications

**Cause**: Marks file not being refreshed daily

**Solution**:

1. Verify EOD pricing job is running successfully
2. Check marks file generation timestamp
3. Adjust `stale_days` threshold if weekend/holiday gaps are expected

### Issue: Processing exceeds performance budget

**Cause**: Too many sequential market data fetches

**Solution**:

1. Increase `max_workers` in config (e.g., 4-8 threads)
2. Reduce `retry_count` if network is stable
3. Consider caching strategy for frequently-accessed tickers

### Issue: All marks classified as OUT_OF_TOLERANCE

**Cause**: Currency mismatch or scale error

**Solution**:

1. Verify marks are in same currency as market data
2. Check for scale errors (cents vs dollars)
3. Verify marks file format matches schema

### Issue: Auditor disputes tolerance thresholds

**Cause**: Tolerance configuration doesn't match audit standards

**Solution**:

1. Document auditor requirements
2. Update `config/tolerances.yaml` to match
3. Re-run validation and provide updated report

---

## Testing

Run tests with pytest:

```bash
# All pricing tests
pytest tests/pricing/

# Specific test file
pytest tests/pricing/test_pricing_agent.py

# With coverage
pytest tests/pricing/ --cov=src/pricing
```

---

## Architecture Notes

### Data Flow

1. **Load**: Marks loaded from CSV/JSON/DataFrame/list
2. **Enrich**: For each mark:
   - Fetch market price via FinancialDatasets.ai API
   - Calculate deviation
   - Apply tolerance thresholds (with per-instrument overrides)
   - Classify mark
   - Check for stale dates
3. **Explain**: Generate human-readable explanations
4. **Aggregate**: Compute summary statistics
5. **Report**: Output structured results and/or Markdown report

### Performance Considerations

- **Parallel fetching**: Use `max_workers > 1` to fetch market data in parallel
- **Caching**: Market prices are cached per (ticker, date) tuple
- **Retries**: Failed fetches are retried with exponential backoff
- **Budget**: Target 30-second completion for 50-100 marks

### Integration Points

- **Data source**: `src.data_tools.fd_api.get_price_snapshot`
- **Reference master** (optional): `src.refmaster.normalize` for ticker validation
- **Audit logs**: JSONL files for compliance
- **Metrics logs**: JSONL files for monitoring

---

## Notes

- Market data calls flow through `data_tools.fd_api`; no direct API keys needed in pricing module
- Refmaster integration is optional; enable by passing `refmaster` to `MarketNormalizer`
- All dates must be in YYYY-MM-DD format (ISO 8601)
- Prices are assumed to be in same currency (no cross-currency conversion)
