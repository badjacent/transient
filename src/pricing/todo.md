# Week 5 - EOD Pricing Agent & Market Data Normalizer Implementation TODO

## Overview
Build an End-of-Day (EOD) pricing sanity-check system that integrates FinancialDatasets.ai market data with internal marks to identify pricing errors that could lead to incorrect NAV calculations and audit issues.

## Module Structure Setup

- [ ] Verify `src/pricing/` directory exists
- [ ] Create `src/pricing/__init__.py` (if not exists)
- [ ] Create `src/pricing/pricing_agent.py` for the main pricing validation agent
- [ ] Create `src/pricing/normalizer.py` for market data normalization
- [ ] Create `src/pricing/schema.py` for pricing-related schemas (if needed)
- [ ] Create `tests/pricing/` directory
- [ ] Create `tests/pricing/__init__.py`
- [ ] Create `tests/pricing/test_pricing_agent.py` for tests
- [ ] Create `tests/pricing/test_normalizer.py` for normalizer tests
- [ ] Create `config/` directory at project root
- [ ] Create `config/tolerances.yaml` for tolerance configuration
- [ ] Create `data/` directory at project root
- [ ] Create `data/marks.csv` for synthetic EOD marks
- [ ] Create `examples/pricing_report.md` template

## Task 1: Create Synthetic EOD Mark File

### 1.1 Define Mark Schema
- [ ] Define schema for internal marks with fields:
  - `ticker` (str) - Stock ticker symbol
  - `internal_mark` (float) - Internal pricing mark
  - `as_of_date` (str) - Date of the mark (YYYY-MM-DD format)
  - `notes` (str, optional) - Additional notes about the mark
  - `source` (str, optional) - Source of the internal mark
- [ ] Consider adding:
  - `position_id` or `portfolio_id` (optional)
  - `instrument_type` (optional, for future extension)
  - `currency` (optional, for multi-currency support)

### 1.2 Generate Synthetic Marks CSV
- [ ] Create `data/marks.csv` with ~50 instruments
- [ ] Include diverse tickers from refmaster:
  - Mix of NASDAQ and NYSE stocks
  - Different sectors/industries
  - Various market caps
- [ ] Create realistic internal marks:
  - Some matching market prices exactly
  - Some with small deviations (<2%)
  - Some with moderate deviations (2-5%)
  - Some with large deviations (>5%)
  - Some with stale dates (old as_of_date)
- [ ] Add variety in `as_of_date`:
  - Most recent dates (current/recent)
  - Some older dates (stale marks)
  - Mix of weekdays (avoid weekends)
- [ ] Add meaningful `notes` field:
  - Some with notes explaining deviations
  - Some with empty notes
  - Some with placeholder text

### 1.3 Mark File Format
- [ ] Use CSV format with headers
- [ ] Ensure proper date formatting (YYYY-MM-DD)
- [ ] Handle special characters in notes field
- [ ] Include example with missing optional fields

## Task 2: Build Market Normalizer

### 2.1 Normalizer Class Structure
- [ ] Create `MarketNormalizer` class in `src/pricing/normalizer.py`
- [ ] Implement initialization:
  - Load configuration from `config/tolerances.yaml`
  - Initialize connection to FD API (via `fd_api` module)
  - Optional: Initialize refmaster for ticker validation

### 2.2 Fetch Market Data
- [ ] Implement `fetch_market_price(ticker, as_of_date)` method:
  - Use `get_price_snapshot()` or `get_equity_snapshot()` from `fd_api`
  - Handle date parameter (use as_of_date from mark)
  - Return market close price for the date
- [ ] Handle edge cases:
  - Market data unavailable for date
  - Ticker not found in market data
  - API errors/timeouts
  - Weekend/holiday dates (no trading)
  - Future dates (invalid)
- [ ] Add error handling and logging

### 2.3 Compare Internal Mark vs Market Price
- [ ] Implement `compare_mark_to_market(internal_mark, market_price, tolerance)`:
  - Calculate absolute deviation: `abs(internal_mark - market_price)`
  - Calculate percentage deviation: `abs((internal_mark - market_price) / market_price) * 100`
  - Compare against tolerance thresholds
- [ ] Return comparison result with:
  - Deviation amount (absolute and percentage)
  - Classification: `OK`, `OUT_OF_TOLERANCE`, `REVIEW_NEEDED`
  - Flag for missing market data

### 2.4 Classification Logic
- [ ] Define classification rules:
  - `OK`: Deviation within tolerance (e.g., <2%)
  - `OUT_OF_TOLERANCE`: Deviation exceeds tolerance (e.g., >5%)
  - `REVIEW_NEEDED`: Deviation in middle range (e.g., 2-5%)
  - `NO_MARKET_DATA`: Market data unavailable
  - `STALE_MARK`: Mark date is too old (configurable threshold)
- [ ] Make thresholds configurable via `config/tolerances.yaml`
- [ ] Support different tolerances by:
  - Instrument type (if extended)
  - Market cap category (if extended)
  - Custom per-ticker rules (if needed)

### 2.5 Enrich Marks with Market Data
- [ ] Implement `enrich_marks(marks_df)` method:
  - Accept DataFrame or list of mark dictionaries
  - For each mark:
    - Fetch market price for ticker and as_of_date
    - Compare internal mark to market price
    - Add enrichment fields:
      - `market_price` (float or None)
      - `deviation_absolute` (float)
      - `deviation_percentage` (float)
      - `classification` (str: OK/OUT_OF_TOLERANCE/REVIEW_NEEDED/NO_MARKET_DATA/STALE_MARK)
      - `market_data_date` (str, date of market data used)
  - Return enriched marks
- [ ] Handle batch processing efficiently
- [ ] Add progress logging for large batches

## Task 3: Build Pricing Agent

### 3.1 Agent Class Structure
- [ ] Create `PricingAgent` class in `src/pricing/pricing_agent.py`
- [ ] Initialize with:
  - `MarketNormalizer` instance
  - Configuration from `config/tolerances.yaml`
  - Optional: LLM client for explanation generation (if using AI)

### 3.2 Main Run Method
- [ ] Implement `run(marks)` method that:
  - Accepts marks as CSV file path, DataFrame, or list of dicts
  - Loads and parses marks
  - Enriches marks with market data via normalizer
  - Generates explanations for discrepancies
  - Aggregates results
  - Returns structured report

### 3.3 Explanation Generation
- [ ] Generate human-readable explanations for each discrepancy:
  - For `OUT_OF_TOLERANCE`:
    - Explain the deviation magnitude
    - Suggest possible causes (stale data, corporate action, error)
    - Recommend action (review, update mark, investigate)
  - For `REVIEW_NEEDED`:
    - Note the moderate deviation
    - Suggest verification
  - For `NO_MARKET_DATA`:
    - Explain why market data is unavailable
    - Suggest alternative data sources or manual review
  - For `STALE_MARK`:
    - Note the age of the mark
    - Recommend updating to current date
- [ ] Make explanations:
  - Concise but informative
  - Actionable
  - Audit-friendly (professional language)
  - Include specific numbers (deviations, dates)

### 3.4 Result Aggregation
- [ ] Aggregate results by classification:
  - Count of OK marks
  - Count of OUT_OF_TOLERANCE marks
  - Count of REVIEW_NEEDED marks
  - Count of NO_MARKET_DATA marks
  - Count of STALE_MARK marks
- [ ] Calculate summary statistics:
  - Total marks processed
  - Average deviation (for marks with market data)
  - Largest deviation
  - Tickers with most issues
- [ ] Generate summary section for report

### 3.5 Report Generation
- [ ] Implement `generate_report(enriched_marks, output_path=None)`:
  - Format: Markdown report (for `pricing_report.md`)
  - Structure:
    - Executive summary
    - Summary statistics
    - Detailed findings by classification
    - Per-ticker details with explanations
    - Recommendations
  - Optional: Also generate JSON/CSV output
- [ ] Make report:
  - Well-formatted and readable
  - Suitable for auditors
  - Include timestamps
  - Include configuration used (tolerances)

## Configuration

### 4.1 Tolerance Configuration
- [ ] Create `config/tolerances.yaml` with:
  - `ok_threshold`: Maximum deviation for OK status (e.g., 2%)
  - `review_threshold`: Maximum deviation before OUT_OF_TOLERANCE (e.g., 5%)
  - `stale_days`: Number of days before mark is considered stale (e.g., 5)
  - Optional: Per-instrument-type tolerances
  - Optional: Per-ticker custom tolerances
- [ ] Add configuration loader
- [ ] Validate configuration on load
- [ ] Provide default values if config missing

## Testing

### 5.1 Unit Tests
- [ ] Test `MarketNormalizer`:
  - Test market price fetching
  - Test comparison logic with various deviations
  - Test classification logic
  - Test edge cases (missing data, API errors)
  - Test tolerance configuration loading

### 5.2 Integration Tests
- [ ] Test `PricingAgent.run()`:
  - Test with valid marks CSV
  - Test with marks having various classifications
  - Test with missing market data scenarios
  - Test with stale marks
  - Test batch processing
  - Test report generation

### 5.3 Scenario Tests
- [ ] Test with synthetic `data/marks.csv`:
  - Verify all marks are processed
  - Verify correct classifications
  - Verify explanations are generated
  - Verify report is created

### 5.4 Error Handling Tests
- [ ] Test API failures:
  - Network timeouts
  - Invalid API keys
  - Rate limiting
  - Invalid tickers
- [ ] Test invalid input:
  - Malformed CSV
  - Missing required fields
  - Invalid dates
  - Invalid prices (negative, zero, etc.)

## Documentation

### 6.1 Module Documentation
- [ ] Create `src/pricing/README.md` with:
  - Overview of pricing agent functionality
  - Usage examples
  - Configuration guide
  - Report format documentation
  - Integration guide

### 6.2 Example Report
- [ ] Generate `examples/pricing_report.md` with:
  - Sample output from pricing agent
  - All classification types represented
  - Example explanations
  - Format that auditors would expect

### 6.3 API Documentation
- [ ] Document all public methods
- [ ] Document configuration schema
- [ ] Document return formats
- [ ] Include code examples

## Integration Points

### 7.1 FinancialDatasets.ai Integration
- [ ] Verify integration with `data_tools.fd_api`:
  - Test `get_price_snapshot()` for historical prices
  - Test `get_equity_snapshot()` for current prices
  - Handle API errors gracefully
  - Cache prices when appropriate (optional, for performance)

### 7.2 Refmaster Integration (Optional)
- [ ] Integrate with `refmaster.NormalizerAgent`:
  - Validate tickers before fetching prices
  - Handle ambiguous ticker matches
  - Use confidence scores appropriately

### 7.3 Data Loading
- [ ] Support multiple input formats:
  - CSV file path
  - pandas DataFrame
  - List of dictionaries
  - JSON file
- [ ] Validate input schema
- [ ] Provide clear error messages for invalid input

## Production Readiness

### 8.1 Logging
- [ ] Add comprehensive logging:
  - Mark processing progress
  - API calls and responses
  - Classification decisions
  - Errors and warnings
  - Performance metrics (processing time)

### 8.2 Performance
- [ ] Optimize batch processing:
  - Parallel API calls (if rate limits allow)
  - Caching of market data
  - Efficient DataFrame operations
- [ ] Target: Process 50 marks in <30 seconds
- [ ] Add performance monitoring

### 8.3 Error Recovery
- [ ] Implement retry logic for API calls
- [ ] Handle partial failures gracefully
- [ ] Continue processing even if some marks fail
- [ ] Report which marks failed and why

### 8.4 Audit Trail
- [ ] Log all processing:
  - Input marks
  - Market data fetched
  - Classifications made
  - Explanations generated
  - Timestamps for all operations
- [ ] Store audit log (optional: to file or database)

## Evaluation Criteria

### 9.1 Functionality
- [ ] Successfully processes all marks in `data/marks.csv`
- [ ] Correctly classifies all marks
- [ ] Generates clear, actionable explanations
- [ ] Produces audit-friendly report

### 9.2 Quality
- [ ] Explanations are concise but informative
- [ ] Report is well-formatted and professional
- [ ] Configuration is flexible and well-documented
- [ ] Error messages are clear and helpful

### 9.3 Performance
- [ ] Processes 50 marks in reasonable time (<30 seconds)
- [ ] Handles API rate limits appropriately
- [ ] Efficient memory usage

## Optional Enhancements

### 10.1 Advanced Features
- [ ] Support for options pricing validation
- [ ] Support for bond/CDS pricing validation
- [ ] Multi-currency support with FX rate validation
- [ ] Historical trend analysis (compare to previous marks)
- [ ] Automated mark update suggestions
- [ ] Integration with portfolio management systems

### 10.2 Reporting Enhancements
- [ ] Generate multiple output formats:
  - Markdown (current)
  - HTML report
  - PDF report
  - JSON for programmatic access
  - Excel/CSV export
- [ ] Add charts/visualizations:
  - Deviation distribution histogram
  - Time series of marks vs market
  - Heatmap by ticker/date

### 10.3 AI/LLM Integration
- [ ] Use LLM to generate more sophisticated explanations
- [ ] Analyze patterns across multiple marks
- [ ] Suggest root causes for systematic issues
- [ ] Generate natural language summaries

### 10.4 Configuration Enhancements
- [ ] Per-portfolio tolerance settings
- [ ] Per-instrument-type tolerances
- [ ] Custom rules engine
- [ ] Alert thresholds and notifications

### 10.5 Data Quality
- [ ] Validate mark data quality:
  - Check for duplicate marks
  - Check for missing required fields
  - Check for data type issues
  - Check for outliers before comparison

