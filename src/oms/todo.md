# Week 4 - OMS & Trade Capture QA Implementation TODO

## Overview
Build an AI-augmented OMS (Order Management System) that validates trades using reference master data and market data checks to catch booking errors before they cause financial losses.

## Module Structure Setup

- [ ] Create `src/oms/` directory structure
- [ ] Create `src/oms/__init__.py`
- [ ] Create `src/oms/schema.py` for OMS-specific schemas
- [ ] Create `src/oms/oms_agent.py` for the main QA agent
- [ ] Create `tests/oms/` directory
- [ ] Create `tests/oms/__init__.py`
- [ ] Create `tests/oms/test_oms_agent.py` for tests
- [ ] Create `scenarios/` directory at project root
- [ ] Create `scenarios/scenarios.json` for synthetic test cases

## Task 1: Define Trade Schema

- [ ] Review existing `Trade` schema in `src/data_tools/schemas.py`
- [ ] Decide whether to:
  - Use existing `Trade` schema from `data_tools/schemas.py`, OR
  - Create OMS-specific trade schema in `src/oms/schema.py`
- [ ] Ensure schema includes all required fields:
  - `ticker` (str)
  - `quantity` (float)
  - `price` (float)
  - `currency` (str)
  - `counterparty` (str)
  - `trade_dt` (str, YYYY-MM-DD format)
  - `settle_dt` (str, YYYY-MM-DD format)
- [ ] Add Pydantic validation for:
  - Date format validation
  - Positive quantity/price validation
  - Currency code format (3-letter ISO codes)
  - Required field validation

## Task 2: Build QA Checks

### 2.1 Missing Fields Check
- [ ] Implement check for required fields
- [ ] Return specific error messages for each missing field
- [ ] Handle optional vs required field distinction

### 2.2 Identifier Mismatch Check
- [ ] Integrate `NormalizerAgent` from `refmaster` module
- [ ] Validate ticker against reference master
- [ ] Check for:
  - Unknown/invalid ticker symbols
  - Ticker format issues (e.g., "AAPL" vs "AAPL.OQ")
  - Ambiguous matches (multiple candidates)
- [ ] Return confidence scores and warnings for low-confidence matches

### 2.3 Currency Mismatch Check
- [ ] Load currency from reference master for the ticker
- [ ] Compare trade currency with reference master currency
- [ ] Handle cases where currency is missing in reference master
- [ ] Return appropriate error/warning for mismatches

### 2.4 Price Out of Tolerance Check
- [ ] Integrate `get_price_snapshot()` or `get_equity_snapshot()` from `fd_api`
- [ ] Fetch current/recent market price for the ticker
- [ ] Calculate price deviation percentage
- [ ] Define tolerance thresholds:
  - ERROR: >5% deviation (configurable)
  - WARNING: 2-5% deviation (configurable)
  - OK: <2% deviation
- [ ] Handle cases where:
  - Market data unavailable
  - Trade date is in the future
  - Trade date is too far in the past (stale data)
- [ ] Consider using trade_dt for historical price validation

### 2.5 Wrong Counterparty Check
- [ ] Define list of valid counterparties (or load from config)
- [ ] Validate counterparty format/formatting
- [ ] Check for common typos or formatting issues
- [ ] Return warnings for suspicious counterparty names

### 2.6 Settlement Date Validation
- [ ] Validate settlement date format
- [ ] Check that `settle_dt >= trade_dt`
- [ ] Validate against standard settlement rules:
  - T+2 for most equities (US)
  - T+1 for some instruments
  - Custom settlement for specific instruments
- [ ] Handle weekend/holiday adjustments

## Task 3: Build Trade QA Agent

### 3.1 Core Agent Structure
- [ ] Create `OMSAgent` class in `src/oms/oms_agent.py`
- [ ] Implement `run(trade_json)` method that:
  - Accepts trade as dict or JSON string
  - Returns structured response with status, issues, explanation
- [ ] Define response schema:
  ```python
  {
    "status": "OK" | "WARNING" | "ERROR",
    "issues": [
      {
        "type": "identifier_mismatch" | "currency_mismatch" | "price_tolerance" | "counterparty" | "missing_field" | "settlement_date",
        "severity": "ERROR" | "WARNING",
        "message": "...",
        "field": "ticker" | "currency" | "price" | etc.
      }
    ],
    "explanation": "Human-readable summary of validation results"
  }
  ```

### 3.2 Agent Initialization
- [ ] Initialize `RefMaster` instance
- [ ] Initialize `NormalizerAgent` instance
- [ ] Load configuration for:
  - Price tolerance thresholds
  - Valid counterparties list
  - Settlement rules
- [ ] Handle API key loading for market data

### 3.3 Validation Orchestration
- [ ] Implement validation pipeline:
  1. Parse and validate trade schema
  2. Check for missing required fields
  3. Validate identifier (ticker) against reference master
  4. Validate currency match
  5. Validate price against market data
  6. Validate counterparty
  7. Validate settlement date
- [ ] Collect all issues (don't stop on first error)
- [ ] Determine overall status:
  - ERROR if any ERROR-level issues
  - WARNING if any WARNING-level issues (and no ERROR)
  - OK if no issues

### 3.4 Explanation Generation
- [ ] Generate human-readable explanation summarizing:
  - Overall validation result
  - Number and types of issues found
  - Specific recommendations for fixing issues
- [ ] Make explanations actionable and clear

## Task 4: Build Synthetic Test Cases

### 4.1 Create Scenarios File
- [ ] Create `scenarios/scenarios.json` with ~20 test cases
- [ ] Structure each scenario as:
  ```json
  {
    "name": "Descriptive test case name",
    "trade": {
      "ticker": "...",
      "quantity": ...,
      "price": ...,
      "currency": "...",
      "counterparty": "...",
      "trade_dt": "...",
      "settle_dt": "..."
    },
    "expected_status": "OK" | "WARNING" | "ERROR",
    "expected_issues": [
      {
        "type": "...",
        "severity": "...",
        "field": "..."
      }
    ],
    "description": "What this test case validates"
  }
  ```

### 4.2 Test Case Categories
- [ ] **Valid trades** (3-5 cases):
  - Normal equity trade
  - Trade with different currencies (if valid)
  - Trade with standard settlement
  
- [ ] **Missing field errors** (3-4 cases):
  - Missing ticker
  - Missing quantity
  - Missing price
  - Missing currency
  - Missing counterparty
  - Missing dates

- [ ] **Identifier mismatch** (2-3 cases):
  - Invalid ticker symbol
  - Ambiguous ticker (low confidence match)
  - Ticker format issues

- [ ] **Currency mismatch** (2 cases):
  - Currency doesn't match reference master
  - Currency code format issues

- [ ] **Price tolerance** (3-4 cases):
  - Price way too high (>5% deviation)
  - Price slightly high (2-5% deviation)
  - Price way too low (>5% deviation)
  - Price slightly low (2-5% deviation)
  - Stale price data scenario

- [ ] **Counterparty issues** (1-2 cases):
  - Invalid counterparty format
  - Suspicious counterparty name

- [ ] **Settlement date issues** (2-3 cases):
  - Settlement before trade date
  - Non-standard settlement (T+1, T+3)
  - Weekend/holiday settlement

## Testing

- [ ] Write unit tests for each QA check individually
- [ ] Write integration tests for `OMSAgent.run()`:
  - Test with valid trades
  - Test with each type of error
  - Test with multiple errors in one trade
  - Test with edge cases (missing data, API failures)
- [ ] Test against all scenarios in `scenarios.json`
- [ ] Test error handling:
  - Market data API failures
  - Reference master data missing
  - Invalid JSON input
  - Network timeouts
- [ ] Test performance (should complete in <30 seconds for batch)

## Documentation

- [ ] Create `src/oms/README.md` with:
  - Overview of OMS agent functionality
  - Usage examples
  - Configuration options
  - Response format documentation
  - Integration guide
- [ ] Document all QA checks and their thresholds
- [ ] Include example trade JSON inputs and outputs
- [ ] Document error codes and messages

## Integration Points

- [ ] Verify integration with `refmaster.NormalizerAgent`:
  - Test ticker normalization
  - Handle ambiguous matches
  - Use confidence scores appropriately

- [ ] Verify integration with `data_tools.fd_api`:
  - Test price fetching
  - Handle API errors gracefully
  - Cache prices when appropriate (optional)

- [ ] Verify integration with `data_tools.schemas.Trade`:
  - Ensure schema compatibility
  - Handle Pydantic validation errors

## Production Readiness

- [ ] Add logging for:
  - Validation results
  - API calls
  - Errors and warnings
- [ ] Add metrics/telemetry (optional):
  - Validation time
  - Error rates by type
  - API call success rates
- [ ] Add configuration file support:
  - Price tolerance thresholds
  - Valid counterparties
  - Settlement rules
  - API endpoints and keys
- [ ] Add audit trail:
  - Log all validated trades
  - Store validation results
  - Timestamp all validations

## Evaluation Criteria

- [ ] Verify catches 80%+ of scripted errors in scenarios
- [ ] Ensure explanations are clear and actionable
- [ ] Verify structured output is consistent
- [ ] Test with real-world trade examples (if available)
- [ ] Performance test: validate batch of trades in <30 seconds

## Optional Enhancements

- [ ] Support for options trades (extend schema)
- [ ] Support for bond/CDS trades (extend schema)
- [ ] Multi-currency support with FX rate validation
- [ ] Historical price validation using trade_dt
- [ ] Integration with external counterparty validation service
- [ ] Batch validation endpoint
- [ ] Webhook support for real-time validation
- [ ] Dashboard/UI for viewing validation results

