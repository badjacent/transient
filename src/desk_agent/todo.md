# Week 6 - Full Front-Office Workflow: Desk Agent MVP Implementation TODO

## Overview
Combine all previous components (Reference Master, Trade QA, Pricing Agent, Ticker Agent, Data Tools) into a unified Desk Agent workflow that can execute scenarios end-to-end and produce integrated reports suitable for front-office use.

## Module Structure Setup

- [ ] Create `src/desk_agent/` directory
- [ ] Create `src/desk_agent/__init__.py`
- [ ] Create `src/desk_agent/orchestrator.py` for main workflow orchestration
- [ ] Create `src/desk_agent/config.py` for configuration management
- [ ] Create `tests/desk_agent/` directory
- [ ] Create `tests/desk_agent/__init__.py`
- [ ] Create `tests/desk_agent/test_orchestrator.py` for orchestrator tests
- [ ] Create `scenarios/` directory at project root (if not exists)
- [ ] Create scenario files in `scenarios/` directory
- [ ] Create `logs/` directory at project root (if not exists)
- [ ] Create `examples/combined_report_example.json` template

## Task 1: Build the Orchestrator

### 1.1 Orchestrator Class Structure
- [ ] Create `DeskAgentOrchestrator` class in `src/desk_agent/orchestrator.py`
- [ ] Initialize with:
  - Reference Master Agent (`refmaster.NormalizerAgent`)
  - Trade QA Agent (`oms.oms_agent.OMSAgent`)
  - Pricing Agent (`pricing.pricing_agent.PricingAgent`)
  - Ticker Agent (`ticker_agent.ticker_agent.run`)
  - Data snapshot tools (`data_tools.fd_api`)
- [ ] Add configuration loading from `config.py`
- [ ] Add logging setup

### 1.2 Scenario Loading
- [ ] Implement `load_scenario(scenario_name)` method:
  - Load scenario from `scenarios/` directory
  - Support JSON/YAML format
  - Validate scenario schema
  - Return scenario data structure
- [ ] Handle scenario not found errors
- [ ] Support custom scenario data (passed directly)

### 1.3 Workflow Execution
- [ ] Implement `run_scenario(scenario_name_or_data)` method:
  - Load scenario (if name provided) or use provided data
  - Execute workflow steps in order
  - Collect results from each sub-agent
  - Aggregate results
  - Generate integrated report
  - Return structured report
- [ ] Define execution order:
  1. Load scenario data
  2. Validate scenario structure
  3. Run Reference Master normalization (if needed)
  4. Run Trade QA validation (if trades present)
  5. Run Pricing validation (if marks present)
  6. Run Ticker Agent queries (if questions present)
  7. Fetch market context data
  8. Aggregate all results
  9. Generate narrative summary

### 1.4 Reference Master Integration
- [ ] Integrate `refmaster.NormalizerAgent`:
  - Normalize ticker identifiers in scenario
  - Validate ticker mappings
  - Handle ambiguous matches
  - Use confidence scores appropriately
- [ ] Handle normalization errors
- [ ] Log normalization results

### 1.5 Trade QA Agent Integration
- [ ] Integrate `oms.oms_agent.OMSAgent`:
  - Validate trades from scenario
  - Run QA checks on each trade
  - Collect trade issues
  - Aggregate trade validation results
- [ ] Handle cases with no trades
- [ ] Handle trade validation errors
- [ ] Log trade validation results

### 1.6 Pricing Agent Integration
- [ ] Integrate `pricing.pricing_agent.PricingAgent`:
  - Validate pricing marks from scenario
  - Run pricing checks
  - Collect pricing flags
  - Aggregate pricing validation results
- [ ] Handle cases with no marks
- [ ] Handle pricing validation errors
- [ ] Log pricing validation results

### 1.7 Ticker Agent Integration
- [ ] Integrate `ticker_agent.ticker_agent.run`:
  - Process ticker questions from scenario
  - Run ticker agent for each question
  - Collect ticker agent responses
  - Aggregate ticker agent results
- [ ] Handle cases with no questions
- [ ] Handle ticker agent errors
- [ ] Log ticker agent results

### 1.8 Market Context Data
- [ ] Fetch market context using `data_tools.fd_api`:
  - Get equity snapshots for key tickers
  - Get market-wide statistics (if available)
  - Get sector/industry data
  - Get recent market movements
- [ ] Aggregate market context
- [ ] Include in final report

### 1.9 Error Handling
- [ ] Handle sub-agent failures gracefully:
  - Continue execution if one agent fails
  - Log errors appropriately
  - Include error information in report
- [ ] Handle API failures:
  - Retry logic (if appropriate)
  - Fallback behavior
  - Error reporting
- [ ] Handle invalid scenario data
- [ ] Handle missing dependencies

## Task 2: Define 5 Scenarios

### 2.1 Scenario Schema
- [ ] Define scenario data structure:
  ```json
  {
    "name": "scenario_name",
    "description": "...",
    "trades": [...],
    "marks": [...],
    "questions": [...],
    "metadata": {...}
  }
  ```
- [ ] Define trade schema (matching `oms` Trade schema)
- [ ] Define mark schema (matching `pricing` mark schema)
- [ ] Define question schema (for ticker agent)

### 2.2 Clean Day Scenario
- [ ] Create `scenarios/clean_day.json`:
  - All trades are valid
  - All marks are within tolerance
  - No errors or warnings
  - Standard market conditions
- [ ] Use realistic data
- [ ] Include multiple tickers
- [ ] Include multiple trades
- [ ] Include multiple marks

### 2.3 Bad Mark Scenario
- [ ] Create `scenarios/bad_mark.json`:
  - One or more marks significantly deviate from market
  - Marks flagged as OUT_OF_TOLERANCE
  - Pricing agent should catch issues
- [ ] Include various deviation types:
  - Price too high
  - Price too low
  - Stale marks
- [ ] Include realistic mark data

### 2.4 Wrong Ticker Mapping Scenario
- [ ] Create `scenarios/wrong_ticker_mapping.json`:
  - Ambiguous or incorrect ticker identifiers
  - Reference Master should flag issues
  - Low confidence matches
  - Invalid ticker formats
- [ ] Include various ticker formats:
  - "AAPL US" (should work)
  - "AAPL.OQ" (should work)
  - "XYZ123" (invalid)
  - Ambiguous matches
- [ ] Test normalization edge cases

### 2.5 Mis-booked Trade Scenario
- [ ] Create `scenarios/mis_booked_trade.json`:
  - Trades with validation errors:
    - Wrong ticker/identifier
    - Currency mismatch
    - Price out of tolerance
    - Wrong counterparty
    - Missing fields
    - Settlement date issues
- [ ] Include multiple error types
- [ ] Include realistic trade data

### 2.6 High-Vol Day Scenario
- [ ] Create `scenarios/high_vol_day.json`:
  - Market volatility conditions
  - Large price movements
  - Multiple pricing flags
  - Trades with unusual prices
  - Market context showing volatility
- [ ] Include volatile market data
- [ ] Test tolerance handling under volatility
- [ ] Include market context data

### 2.7 Scenario Validation
- [ ] Validate all scenarios load correctly
- [ ] Validate scenario schemas
- [ ] Test scenario execution
- [ ] Verify expected outcomes

## Task 3: Produce an Integrated Report

### 3.1 Report Schema
- [ ] Define integrated report structure:
  ```json
  {
    "scenario": {
      "name": "...",
      "description": "...",
      "execution_date": "..."
    },
    "data_quality": {
      "ticker_normalizations": [...],
      "normalization_issues": [...],
      "confidence_scores": {...}
    },
    "trade_issues": [
      {
        "trade_id": "...",
        "status": "OK" | "WARNING" | "ERROR",
        "issues": [...],
        "ticker": "...",
        "counterparty": "..."
      }
    ],
    "pricing_flags": [
      {
        "ticker": "...",
        "internal_mark": ...,
        "market_price": ...,
        "deviation": ...,
        "classification": "...",
        "explanation": "..."
      }
    ],
    "market_context": {
      "key_tickers": [...],
      "market_movements": {...},
      "sector_performance": {...},
      "as_of_date": "..."
    },
    "ticker_agent_results": [
      {
        "question": "...",
        "intent": "...",
        "summary": "...",
        "metrics": {...}
      }
    ],
    "narrative": "...",
    "summary": {
      "total_trades": ...,
      "trades_with_issues": ...,
      "total_marks": ...,
      "marks_flagged": ...,
      "overall_status": "OK" | "WARNING" | "ERROR"
    },
    "execution_metadata": {
      "execution_time_ms": ...,
      "timestamp": "...",
      "agents_executed": [...]
    }
  }
  ```

### 3.2 Data Quality Section
- [ ] Aggregate ticker normalization results:
  - Successful normalizations
  - Ambiguous matches
  - Failed normalizations
  - Confidence scores
- [ ] Include normalization details
- [ ] Flag data quality issues

### 3.3 Trade Issues Section
- [ ] Aggregate trade validation results:
  - All trades processed
  - Trades with errors
  - Trades with warnings
  - Trades that are OK
- [ ] Include detailed issue information
- [ ] Group by issue type
- [ ] Include trade identifiers

### 3.4 Pricing Flags Section
- [ ] Aggregate pricing validation results:
  - All marks processed
  - Marks flagged (OUT_OF_TOLERANCE, REVIEW_NEEDED)
  - Marks that are OK
  - Marks with no market data
- [ ] Include deviation details
- [ ] Include explanations
- [ ] Sort by severity

### 3.5 Market Context Section
- [ ] Aggregate market data:
  - Key ticker snapshots
  - Market-wide statistics
  - Sector/industry performance
  - Recent market movements
- [ ] Include relevant dates
- [ ] Include data sources

### 3.6 Ticker Agent Results Section
- [ ] Aggregate ticker agent responses:
  - Questions asked
  - Intents identified
  - Summaries generated
  - Metrics extracted
- [ ] Include source information
- [ ] Format for readability

### 3.7 Narrative Generation
- [ ] Generate human-readable narrative:
  - Executive summary
  - Key findings
  - Issues discovered
  - Recommendations
  - Overall assessment
- [ ] Use natural language
- [ ] Make it business-friendly
- [ ] Include specific numbers and details
- [ ] Highlight critical issues
- [ ] Provide actionable insights

### 3.8 Summary Statistics
- [ ] Calculate summary statistics:
  - Total trades processed
  - Trades with issues (count and percentage)
  - Total marks processed
  - Marks flagged (count and percentage)
  - Overall status (OK/WARNING/ERROR)
- [ ] Include breakdowns by:
  - Issue type
  - Severity
  - Ticker
  - Counterparty

### 3.9 Execution Metadata
- [ ] Include execution details:
  - Execution time (milliseconds)
  - Timestamp
  - Agents executed
  - Scenario name
  - Configuration used
- [ ] Include performance metrics
- [ ] Include error information (if any)

### 3.10 Report Generation
- [ ] Implement `generate_report(results)` method:
  - Aggregate all sub-agent results
  - Generate narrative
  - Calculate summary statistics
  - Format as structured JSON
  - Return complete report
- [ ] Support JSON output format
- [ ] Support pretty-printing (indented JSON)
- [ ] Save to file (optional)

### 3.11 Example Report
- [ ] Generate `examples/combined_report_example.json`:
  - Use one of the scenarios
  - Include all sections
  - Show complete structure
  - Use realistic data
  - Format nicely for readability

## Configuration Management

### 4.1 Configuration File
- [ ] Create `src/desk_agent/config.py`
- [ ] Load configuration from:
  - Environment variables
  - Config file (YAML/JSON)
  - Default values
- [ ] Support configuration for:
  - Sub-agent settings
  - Scenario paths
  - Tolerance thresholds
  - Logging levels
  - API endpoints
  - Timeout values

### 4.2 Sub-Agent Configuration
- [ ] Configure Reference Master:
  - Data path
  - Normalization settings
- [ ] Configure Trade QA Agent:
  - Tolerance thresholds
  - Valid counterparties
  - Settlement rules
- [ ] Configure Pricing Agent:
  - Tolerance thresholds
  - Stale mark thresholds
- [ ] Configure Ticker Agent:
  - LLM model settings
  - Intent definitions path

## Testing

### 5.1 Unit Tests
- [ ] Test orchestrator initialization
- [ ] Test scenario loading
- [ ] Test scenario validation
- [ ] Test sub-agent integration (mocked)
- [ ] Test error handling
- [ ] Test report generation

### 5.2 Integration Tests
- [ ] Test full workflow with each scenario:
  - Clean day scenario
  - Bad mark scenario
  - Wrong ticker mapping scenario
  - Mis-booked trade scenario
  - High-vol day scenario
- [ ] Test with real sub-agents (if possible)
- [ ] Test error recovery
- [ ] Test concurrent scenario execution (if applicable)

### 5.3 Scenario Tests
- [ ] Test each scenario:
  - Scenario loads correctly
  - Scenario executes successfully
  - Expected results are produced
  - Report structure is correct
- [ ] Verify expected outcomes match actual outcomes
- [ ] Test edge cases in scenarios

### 5.4 Report Validation Tests
- [ ] Test report structure:
  - All required sections present
  - Data types are correct
  - No missing required fields
- [ ] Test report content:
  - Data is aggregated correctly
  - Narrative is generated
  - Summary statistics are accurate
- [ ] Test report formatting

## Logging

### 6.1 Orchestration Logging
- [ ] Log scenario execution start
- [ ] Log each sub-agent execution:
  - Agent name
  - Input data
  - Execution time
  - Results summary
  - Errors (if any)
- [ ] Log workflow steps
- [ ] Log report generation
- [ ] Log execution completion

### 6.2 Performance Logging
- [ ] Log execution times:
  - Total execution time
  - Per-agent execution times
  - Per-scenario step times
- [ ] Log slow operations
- [ ] Track performance metrics

### 6.3 Error Logging
- [ ] Log all errors with context:
  - Scenario name
  - Step where error occurred
  - Error type and message
  - Stack trace
  - Input data
- [ ] Log warnings
- [ ] Log recovery actions

## Documentation

### 7.1 Module Documentation
- [ ] Create `src/desk_agent/README.md`:
  - Overview of orchestrator
  - Usage examples
  - Configuration guide
  - Scenario format documentation
  - Report format documentation
  - Integration guide

### 7.2 Scenario Documentation
- [ ] Document scenario format
- [ ] Document each scenario:
  - Purpose
  - Expected outcomes
  - Use cases
- [ ] Provide scenario examples
- [ ] Document how to create new scenarios

### 7.3 Report Documentation
- [ ] Document report structure
- [ ] Document each section
- [ ] Provide report examples
- [ ] Document interpretation guidelines

## Performance and Reliability

### 8.1 Performance Optimization
- [ ] Optimize sub-agent execution:
  - Parallel execution where possible
  - Caching where appropriate
  - Efficient data structures
- [ ] Target: Complete scenario in <30 seconds
- [ ] Profile and optimize hot paths

### 8.2 Reliability
- [ ] Handle sub-agent failures gracefully
- [ ] Implement retry logic (if appropriate)
- [ ] Implement timeout handling
- [ ] Ensure partial results are returned
- [ ] Validate data at each step

### 8.3 Error Recovery
- [ ] Continue execution on non-critical errors
- [ ] Provide meaningful error messages
- [ ] Include error context in report
- [ ] Log all errors for debugging

## Evaluation Criteria

### 9.1 Functionality
- [ ] Orchestrator runs reliably
- [ ] All scenarios execute successfully
- [ ] All sub-agents are integrated correctly
- [ ] Reports are generated correctly

### 9.2 Output Quality
- [ ] Reports are business-grade:
  - Professional formatting
  - Clear narrative
  - Actionable insights
  - Complete information
- [ ] Reports demonstrate integrated reasoning:
  - Connections between issues
  - Context-aware analysis
  - Comprehensive view

### 9.3 Performance
- [ ] Scenarios complete in reasonable time
- [ ] System handles load appropriately
- [ ] No memory leaks
- [ ] Efficient resource usage

## Optional Enhancements

### 10.1 Advanced Features
- [ ] Support for custom workflow steps
- [ ] Support for conditional execution
- [ ] Support for workflow branching
- [ ] Support for workflow loops/iterations
- [ ] Support for parallel sub-agent execution

### 10.2 Reporting Enhancements
- [ ] Multiple report formats:
  - JSON (current)
  - Markdown
  - HTML
  - PDF
- [ ] Interactive reports
- [ ] Charts and visualizations
- [ ] Export capabilities

### 10.3 Scenario Management
- [ ] Scenario versioning
- [ ] Scenario templates
- [ ] Scenario validation tools
- [ ] Scenario comparison tools
- [ ] Scenario execution history

### 10.4 Integration Enhancements
- [ ] Webhook support
- [ ] Event-driven execution
- [ ] Real-time updates
- [ ] API endpoints for orchestrator
- [ ] CLI interface

