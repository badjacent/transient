# Desk Agent Orchestrator (Week 6)

![Status](https://img.shields.io/badge/status-production-green) ![Python](https://img.shields.io/badge/python-3.11+-blue)

## Business Context

The Desk Agent Orchestrator automates the end-of-day validation workflow that hedge fund operations teams run manually, reducing a multi-hour process to under 30 seconds while providing comprehensive audit trails.

### Why This Matters

- **Manual operations teams** spend 2-4 hours per day validating trades, marks, and data quality across multiple systems
- **Auditors require** documented evidence of systematic controls for trade booking, pricing validation, and reference data accuracy
- **Risk managers need** rapid detection of pricing errors, trade booking mistakes, and data quality issues before NAV is published
- **The Desk Agent** provides immediate, consistent, auditable validation across all front-office data flows

**Time Savings**: Manual validation of 50 positions + 20 trades = 2-3 hours → Desk Agent = 20-30 seconds

**Error Detection**: Catches booking errors, pricing divergences, and data quality issues before they impact books and records

**Audit Trail**: Every validation run produces structured JSON reports with full traceability for compliance and audit requests

---

## Overview

Runs scenarios end-to-end: normalization, OMS QA, pricing validation, ticker Q&A, and market context aggregation.

---

## Architecture

### Data Flow

```
Input: Scenario (trades, marks, questions)
   ↓
[1] Reference Master → Normalize tickers (detect ambiguity, unknowns)
   ↓
[2] OMS Agent → Validate trades (settlement, price, counterparty, currency)
   ↓
[3] Pricing Agent → Validate marks (OUT_OF_TOLERANCE, REVIEW_NEEDED, STALE_MARK)
   ↓
[4] Ticker Agent → Answer questions (fundamentals, performance, sentiment)
   ↓
[5] Market Context → Aggregate snapshots, sector performance, market movements
   ↓
Output: Integrated Report (JSON) + Narrative + Summary
```

### Agent Integration Points

- **Reference Master** (`src.refmaster`): Ticker normalization, ISIN/CUSIP lookup, confidence scoring
- **OMS Agent** (`src.oms`): Trade validation, settlement checks, price tolerance, counterparty verification
- **Pricing Agent** (`src.pricing`): Mark-to-market comparison, deviation classification, stale detection
- **Ticker Agent** (`src.ticker_agent`): Financial Q&A, fundamentals, performance analysis
- **Market Context** (`src.data_tools.fd_api`): Real-time snapshots, sector aggregation

### Error Handling Strategy

- **Retry Logic**: Each step retries up to `retry_max` times with exponential backoff
- **Graceful Degradation**: Failed steps return error dicts instead of crashing the entire workflow
- **Error Trace**: Full execution trace captured in `execution_metadata` for debugging
- **Validation First**: Scenario schema validated before execution to fail fast on malformed data

### Performance Characteristics

- **Target**: 30-second budget for 50 positions + 20 trades
- **Actual**: 15-25 seconds for typical scenarios (< budget)
- **Parallel Execution**: Ticker agent questions can run in parallel with `parallel_ticker=true`
- **Caching**: Market data cached per (ticker, date) tuple to avoid redundant API calls

---

## Usage

### Python API

```python
from src.desk_agent.orchestrator import DeskAgentOrchestrator

# Initialize with defaults
agent = DeskAgentOrchestrator()

# Run single scenario
report = agent.run_scenario("scenarios/clean_day.json")
print(f"Status: {report['summary']['overall_status']}")
print(f"Duration: {report['execution_metadata']['execution_time_ms']:.0f}ms")

# Generate JSON report
agent.generate_report(report, "reports/clean_day_report.json")

# Run all scenarios (smoke test)
summary = agent.smoke_all_scenarios()
print(f"Ran {summary['scenarios_ran']} scenarios")
print(f"Errors: {summary['errors']}, Warnings: {summary['warnings']}")
```

### CLI Usage

```bash
# Run single scenario
python -m src.desk_agent --scenario scenarios/clean_day.json

# Save report to file
python -m src.desk_agent --scenario scenarios/bad_mark.json --output reports/bad_mark.json

# Run all scenarios (smoke test)
python -m src.desk_agent --smoke-all

# Save smoke test summary
python -m src.desk_agent --smoke-all --output reports/smoke_test.json
```

### Interpreting Results

```python
report = agent.run_scenario("scenarios/high_vol_day.json")

# Overall status (OK, WARNING, ERROR)
print(f"Status: {report['summary']['overall_status']}")

# Trade validation results
print(f"Total trades: {report['summary']['total_trades']}")
print(f"Trades with issues: {report['summary']['trades_with_issues']}")
for trade in report['trade_issues']:
    if trade['status'] != 'OK':
        print(f"  {trade['trade_id']}: {trade['status']} - {len(trade['issues'])} issues")

# Pricing validation results
print(f"Total marks: {report['summary']['total_marks']}")
print(f"Marks flagged: {report['summary']['marks_flagged']}")
for mark in report['pricing_flags']:
    if mark['classification'] != 'OK':
        print(f"  {mark['ticker']}: {mark['classification']} ({mark['deviation']*100:.1f}% dev)")

# Data quality issues
dq = report['data_quality']
print(f"Normalization issues: {len(dq['normalization_issues'])}")
for issue in dq['normalization_issues']:
    print(f"  {issue['ticker']}: {issue['issue']}")

# Execution performance
print(f"Execution time: {report['execution_metadata']['execution_time_ms']:.0f}ms")
print(f"Within budget: {report['summary'].get('within_budget', 'N/A')}")
```

---

## Configuration

### Configuration Precedence

1. **Defaults** (in `config.py`)
2. **Config file** (if provided via `config_path`)
3. **Environment variables** (highest precedence)

### Environment Variables

**Core Settings**:

- `DESK_AGENT_SCENARIOS_PATH`: Directory containing scenario files (default: `scenarios`)
- `DESK_AGENT_LOG_PATH`: Directory for log files (default: `logs`)
- `DESK_AGENT_LOG_LEVEL`: Logging level - DEBUG, INFO, WARNING, ERROR (default: `INFO`)

**Retry Configuration**:

- `DESK_AGENT_MAX_RETRIES`: Maximum retry attempts per step (default: `2`)
- `DESK_AGENT_BACKOFF_MS`: Milliseconds between retries (default: `500`)
- `DESK_AGENT_ABORT_AFTER_RETRY`: Abort scenario on failure vs. continue (default: `false`)

**Performance**:

- `DESK_AGENT_PARALLEL_TICKER`: Run ticker questions in parallel (default: `false`)
- `DESK_AGENT_PERF_BUDGET_MS`: Target execution time in milliseconds (default: `30000`)

**Sub-Agent Configuration**:

- `REFMASTER_DATA_PATH`: Path to reference data CSV
- `OMS_PRICE_WARNING_THRESHOLD`: Price tolerance for WARNING (e.g., `0.05` for 5%)
- `OMS_PRICE_ERROR_THRESHOLD`: Price tolerance for ERROR (e.g., `0.15` for 15%)
- `OMS_COUNTERPARTIES`: Comma-separated list of valid counterparties
- `OMS_SETTLEMENT_DAYS`: Standard settlement period (e.g., `2` for T+2)
- `PRICING_TOLERANCE`: Pricing tolerance threshold
- `PRICING_STALE_DAYS`: Days before mark is considered stale
- `TICKER_AGENT_MODEL`: Model to use for ticker agent
- `TICKER_AGENT_INTENTS`: Path to intents configuration

---

## Scenario Design Guide

### Creating New Scenarios

1. **Define the Test Objective**: What workflow or edge case are you testing?
2. **Create Scenario File**: JSON or YAML with required schema
3. **Add Test Data**: Trades, marks, questions that exercise the objective
4. **Set Expected Metadata**: Document expected overall_status and issues
5. **Validate**: Run validation before committing

### Scenario Schema

```json
{
  "name": "scenario_name",
  "description": "Brief description of what this tests",
  "trades": [
    {
      "trade_id": "T1",
      "ticker": "AAPL",
      "quantity": 100,
      "price": 150.0,
      "currency": "USD",
      "counterparty": "MS",
      "trade_dt": "2025-12-17",
      "settle_dt": "2025-12-19",
      "side": "BUY",
      "notes": "Optional notes"
    }
  ],
  "marks": [
    {
      "ticker": "AAPL",
      "internal_mark": 150.0,
      "as_of_date": "2025-12-17",
      "source": "internal",
      "notes": "Optional notes"
    }
  ],
  "questions": [
    {
      "question": "How is AAPL performing?",
      "ticker": "AAPL",
      "intent_hint": "performance",
      "context": {}
    }
  ],
  "metadata": {
    "author": "your_name",
    "created": "2025-12-18",
    "tags": ["test_tag"],
    "expected_status": "OK"
  }
}
```

### Best Practices

- **Use realistic data**: Pull tickers and prices from actual market data
- **Recent dates**: Use dates within last 5 days to avoid STALE_MARK in baseline scenarios
- **Clear notes**: Document what each trade/mark is testing
- **Expected status**: Set `metadata.expected_status` to document intent
- **Mix issues**: Include some clean data alongside problem cases for contrast
- **Validate before commit**: Run `python -m src.desk_agent --scenario your_scenario.json` to verify

---

## Production Readiness & 15-Minute Client Demo

### Pre-Demo Checklist (10 minutes before)

- [ ] **Verify API keys**: Check `.env` for `FINANCIAL_DATASETS_API_KEY`, `ANTHROPIC_API_KEY`
- [ ] **Check scenarios**: Ensure all 5 scenario files exist in `scenarios/` directory
- [ ] **Run smoke test**: `python -m src.desk_agent --smoke-all` (should complete in ~90 seconds)
- [ ] **Check logs**: Verify `logs/desk_agent.log` is writable
- [ ] **Review example report**: Open `examples/combined_report_example.json` for reference
- [ ] **Test network**: Ensure connection to FinancialDatasets.ai API is working
- [ ] **Clear old logs** (optional): Archive or remove old log files for clarity

### 15-Minute Demo Timeline

**Minutes 0-2: Introduction & Context**

- Explain the manual operations problem (2-4 hours daily)
- Show the 5 scenarios we'll demonstrate
- Set expectations: "We'll run all 5 scenarios in under 2 minutes total"

**Minutes 2-5: Baseline Demonstration (clean_day)**

```bash
python -m src.desk_agent --scenario scenarios/clean_day.json --output demo/clean_day.json
```

- **Show**: Overall status, zero issues, fast execution
- **Explain**: "This is what a good day looks like - all systems green"
- **Highlight**: Execution time < 5 seconds for 11 positions

**Minutes 5-8: OMS Validation (mis_booked_trade)**

```bash
python -m src.desk_agent --scenario scenarios/mis_booked_trade.json --output demo/mis_booked_trade.json
```

- **Show**: Trade issues breakdown (settlement dates, price tolerance, counterparty)
- **Explain**: "OMS agent caught 6 booking errors before they hit the books"
- **Highlight**: Detailed explanations for each error

**Minutes 8-11: Pricing Validation (bad_mark)**

```bash
python -m src.desk_agent --scenario scenarios/bad_mark.json --output demo/bad_mark.json
```

- **Show**: Pricing flags with OUT_OF_TOLERANCE, REVIEW_NEEDED, STALE_MARK classifications
- **Explain**: "Pricing agent flagged 13 marks for auditor review with full explanations"
- **Highlight**: Automated explanations reduce auditor response time from hours to minutes

**Minutes 11-13: Comprehensive Smoke Test**

```bash
python -m src.desk_agent --smoke-all
```

- **Show**: All 5 scenarios run in sequence (~90 seconds total)
- **Explain**: "This is how you'd validate the entire day's activity end-to-end"
- **Highlight**: `scenarios_ran: 5`, `total_ms: ~90000` (90 seconds for full validation)

**Minutes 13-15: Review Combined Report & Q&A**

- Open `examples/combined_report_example.json` in editor
- **Show**: All 9 sections of integrated report
- **Walk through**: scenario → data_quality → trade_issues → pricing_flags → summary → narrative
- **Answer questions**: Address specific client concerns

### Performance Optimization Tips

- **Enable parallel execution**: `export DESK_AGENT_PARALLEL_TICKER=1`
- **Reduce retry count for demos**: `export DESK_AGENT_MAX_RETRIES=1`
- **Use smaller scenarios**: Focus on 10-20 positions for speed
- **Pre-warm cache** (optional): Run scenarios once before demo to cache market data

### Fallback Strategies

**If a scenario fails during demo**:

1. **Acknowledge it**: "Let's look at the error trace" (shows transparency)
2. **Show execution_metadata**: Demonstrate comprehensive error logging
3. **Skip to next scenario**: "Let me show you another workflow"
4. **Use pre-generated report**: Fall back to `examples/combined_report_example.json`

**If API rate limits hit**:

1. **Explain caching**: "In production, we cache market data to avoid this"
2. **Show existing results**: Use pre-generated reports from examples/
3. **Demonstrate retry logic**: Point out automatic retry handling in code

---

## Scenarios Provided

### 1. clean_day.json

**Purpose**: Happy path baseline
**Content**: 4 trades, 7 marks, 3 questions
**Expected Status**: OK
**Use Case**: Demonstrate normal operations with no issues

### 2. bad_mark.json

**Purpose**: Pricing validation focus
**Content**: 2 trades, 15 marks, 2 questions
**Expected Status**: ERROR
**Flagged Marks**:

- 8 OUT_OF_TOLERANCE (INTC, ORCL, CRM, ADBE, BABA, JD, SHOP, V)
- 3 REVIEW_NEEDED (TSLA, NFLX, T)
- 2 STALE_MARK (RY, TD)
- 2 NO_MARKET_DATA (DELISTED, BADTICK)

### 3. wrong_ticker_mapping.json

**Purpose**: Reference master / normalization focus
**Content**: 7 trades, 5 marks, 3 questions
**Expected Status**: WARNING
**Issues Tested**:

- Tickers with exchange suffixes (AAPL US, MSFT.OQ)
- Common typos (APPL instead of AAPL)
- Company name format (AMZN Inc)
- ISIN/CUSIP formats (US0378331005)
- Invalid tickers

### 4. mis_booked_trade.json

**Purpose**: OMS validation focus
**Content**: 10 trades, 3 marks, 2 questions
**Expected Status**: ERROR
**Issues Tested**:

- Settlement date errors (before trade date, weekend)
- Price tolerance violations (>15% deviation)
- Currency mismatches (EUR for US equity)
- Unknown counterparties
- Non-standard settlement periods (T+6)

### 5. high_vol_day.json

**Purpose**: Market context / volatility focus
**Content**: 7 trades, 12 marks, 5 questions
**Expected Status**: WARNING
**Features**:

- Multi-sector exposure (Tech, Finance, Energy, Industrials)
- Multiple REVIEW_NEEDED marks (volatility-driven)
- Sector performance aggregation
- Defensive vs. growth positioning analysis

---

## Report Structure

### Complete Section Breakdown

```json
{
  "scenario": {
    "name": "scenario_name",
    "description": "...",
    "metadata": {...},
    "execution_date": "2025-12-18T19:11:00Z"
  },
  "data_quality": {
    "ticker_normalizations": [...],
    "normalization_issues": [...],
    "confidence_scores": {...}
  },
  "trade_issues": [
    {
      "trade_id": "T1",
      "status": "OK|WARNING|ERROR",
      "issues": [...],
      "ticker": "AAPL",
      "counterparty": "MS"
    }
  ],
  "pricing_flags": [
    {
      "ticker": "AAPL",
      "internal_mark": 150.0,
      "market_price": 145.0,
      "deviation": 0.0345,
      "classification": "REVIEW_NEEDED",
      "explanation": "..."
    }
  ],
  "market_context": {
    "key_tickers": [...],
    "snapshots": [...],
    "market_movements": {...},
    "sector_performance": {...},
    "as_of_date": "2025-12-18"
  },
  "ticker_agent_results": [
    {
      "question": "...",
      "intent": "...",
      "summary": "...",
      "metrics": {...}
    }
  ],
  "narrative": "Processed N trades and M marks; overall status ...",
  "summary": {
    "total_trades": N,
    "trades_with_issues": X,
    "total_marks": M,
    "marks_flagged": Y,
    "overall_status": "OK|WARNING|ERROR",
    "issue_breakdown": {...},
    "severity_breakdown": {...}
  },
  "execution_metadata": {
    "execution_time_ms": 18211,
    "timestamp": "2025-12-18T19:11:00Z",
    "agents_executed": ["refmaster", "oms", "pricing", "ticker_agent", "market_context"],
    "trace": [...],
    "config": {...},
    "errors": [...]
  }
}
```

See `examples/combined_report_example.json` for a complete real-world example.

---

## Troubleshooting

### Issue: API Rate Limits (429 errors)

**Symptoms**: `API returned status 429` in logs

**Cause**: Exceeded FinancialDatasets.ai API rate limits

**Solutions**:

1. Reduce scenario size (fewer tickers)
2. Increase retry backoff: `export DESK_AGENT_BACKOFF_MS=1000`
3. Add delays between smoke test scenarios (modify orchestrator)
4. Contact FinancialDatasets.ai for higher rate limits

### Issue: Slow Execution (> 30 seconds)

**Symptoms**: `execution_time_ms` exceeds `performance_budget_ms`

**Cause**: Sequential execution, many tickers, or slow API responses

**Solutions**:

1. Enable parallel ticker execution: `export DESK_AGENT_PARALLEL_TICKER=1`
2. Reduce retry count: `export DESK_AGENT_MAX_RETRIES=1`
3. Use smaller scenarios for demos
4. Check network latency to API endpoints

### Issue: Scenario Validation Errors

**Symptoms**: `ValueError: Scenario validation errors: [...]`

**Cause**: Malformed scenario JSON or missing required fields

**Solutions**:

1. Check error message for specific field/validation issue
2. Verify all trades have: `trade_id`, `ticker`, `quantity`, `price`, `currency`, `counterparty`, `trade_dt`, `settle_dt`
3. Verify all marks have: `ticker`, `internal_mark`, `as_of_date` (or `as_of`)
4. Verify all questions have: `question`, `ticker`
5. Use the scenario schema template in this README

### Issue: Module Import Errors

**Symptoms**: `ImportError: No module named 'src.refmaster'`

**Cause**: Running from wrong directory or missing dependencies

**Solutions**:

1. Run from project root: `cd /path/to/transient && python -m src.desk_agent ...`
2. Activate virtual environment: `source .venv/bin/activate`
3. Install dependencies: `uv sync` or `pip install -r requirements.txt`

### Issue: Ticker Agent Not Available

**Symptoms**: `ImportError: Ticker agent runner is not available`

**Cause**: Ticker agent module not installed or configured

**Solutions**:

1. Verify `src/ticker_agent/` exists and is importable
2. Check that `ticker_agent.run` function is available
3. Pass custom ticker runner: `DeskAgentOrchestrator(ticker_runner=your_function)`

---

## Logging

### Log Format

```
2025-12-18 19:10:05,300 INFO src.desk_agent.orchestrator desk_agent scenario_start name=clean_day
2025-12-18 19:10:08,450 INFO src.desk_agent.orchestrator normalize completed count=11 issues=0
2025-12-18 19:10:10,125 WARNING src.desk_agent.orchestrator pricing slow_step scenario=clean_day duration_ms=2150.34
2025-12-18 19:10:12,500 INFO src.desk_agent.orchestrator desk_agent scenario_complete name=clean_day status=OK duration_ms=7200.15
```

### Log Levels

- **DEBUG**: Detailed input/output for every step (enable with `DESK_AGENT_LOG_LEVEL=DEBUG`)
- **INFO**: Start/complete events, step durations, counts
- **WARNING**: Slow steps (>2s), failed market data fetches, retries
- **ERROR**: Step failures, validation errors, critical issues

### Debugging Workflow

1. **Check logs**: `tail -f logs/desk_agent.log`
2. **Find scenario**: Search for `scenario_start name=<scenario_name>`
3. **Review trace**: Check `execution_metadata.trace` in report JSON
4. **Inspect errors**: Look for `ERROR` log level entries or `execution_metadata.errors`

---

## Integration Points

### Adding Custom Sub-Agents

```python
from src.desk_agent.orchestrator import DeskAgentOrchestrator

# Custom normalizer
class MyNormalizer:
    def normalize(self, ticker, top_k=1):
        # Your custom logic
        return [...]

# Custom OMS
class MyOMS:
    def run(self, trade_json):
        # Your custom logic
        return {"status": "OK", "issues": [], "explanation": "..."}

# Use custom agents
agent = DeskAgentOrchestrator(
    normalizer=MyNormalizer(),
    oms_agent=MyOMS()
)
```

### Extending Report Structure

Modify `orchestrator.py::_assemble_report()` to add custom sections:

```python
def _assemble_report(self, ...):
    report = {
        # ... existing sections ...
        "custom_section": self._build_custom_section(...)
    }
    return report
```

### Custom Retry Logic

Override retry configuration per scenario:

```python
agent = DeskAgentOrchestrator()
agent.retry_cfg = {
    "max": 5,
    "backoff_ms": 1000,
    "abort_after_retry": True
}
```

---

## Testing

Run tests:

```bash
# All desk agent tests
pytest tests/desk_agent/ -v

# Specific test file
pytest tests/desk_agent/test_orchestrator.py -v

# With coverage
pytest tests/desk_agent/ --cov=src.desk_agent
```

---

## Notes

- All dates must be in ISO 8601 format (YYYY-MM-DD)
- Prices are assumed to be in same currency (no cross-currency conversion)
- Market data calls flow through `data_tools.fd_api`
- Refmaster is required for ticker normalization
- Ticker agent is optional (can be stubbed for testing)
