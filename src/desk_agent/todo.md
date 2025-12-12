# Desk Agent TODO (implementation-ready)
Audience: implementation agent. Treat all referenced sub-agents as existing stubs in their home modules (no internal modifications here). Paths are repo-root-relative.

## Module Structure Setup
- [x] Ensure `src/desk_agent/` exists with `__init__.py`, `orchestrator.py`, and `config.py`; files may start as stubs but must be importable.
- [x] Ensure `tests/desk_agent/` exists with `__init__.py` and `test_orchestrator.py` placeholder.
- [x] Ensure project-root `scenarios/` and `logs/` directories exist; keep write path configurable via `config.py`.
- [x] Create/update `examples/combined_report_example.json` as a template output produced by the orchestrator.

## Task 1: Build the Orchestrator

### 1.1 Orchestrator Class Structure
- [x] Implement `DeskAgentOrchestrator` in `src/desk_agent/orchestrator.py`, initialized with injected stubs: `refmaster.NormalizerAgent`, `oms.oms_agent.OMSAgent`, `pricing.pricing_agent.PricingAgent`, `ticker_agent.ticker_agent.run`, and `data_tools.fd_api` utilities.
- [x] Wire configuration loading through `config.py` (env > file > defaults) and set up logging (level, handlers, log path from config).
- [x] Expose constructor parameters for dependency overrides (for tests/mocks).

### 1.2 Scenario Loading
- [x] Implement `load_scenario(name_or_path: str) -> dict` that reads from `scenarios/` (JSON or YAML), validates schema, and surfaces `FileNotFoundError` with a helpful message.
- [x] Accept already-loaded scenario dicts without reloading.
- [x] Provide schema validation errors that list missing/invalid fields by path.

### 1.3 Workflow Execution
- [x] Implement `run_scenario(scenario: str | dict) -> dict` that executes the ordered workflow and returns the integrated report.
- [x] Execution order (enforce explicitly): load/accept scenario → validate schema → normalize tickers → trade QA → pricing validation → ticker questions → market context fetch → aggregate → narrative + stats.
- [x] Capture per-step timings, inputs, outputs, and exceptions in a structured trace attached to the report.

### 1.4 Reference Master Integration
- [x] Call `refmaster.NormalizerAgent` stub to normalize all identifiers in scenario trades/marks/questions; propagate confidence scores and ambiguity flags.
- [ ] Surface normalization failures without stopping the workflow; include them in `data_quality`.
- [x] Log normalization inputs, resolved identifiers, and confidence.

### 1.5 Trade QA Integration
- [x] Call `oms.oms_agent.OMSAgent` stub for each trade; collect per-trade status/issues and an aggregate summary.
- [x] If no trades are present, skip with a logged no-op entry and mark `trade_issues` as empty.
- [x] On validation errors, continue but record error objects in the report.

### 1.6 Pricing Integration
- [x] Call `pricing.pricing_agent.PricingAgent` stub on marks; gather flags/classifications/deviations.
- [x] Handle empty marks with a logged skip; capture failures without aborting the run.

### 1.7 Ticker Agent Integration
- [x] For each question, call `ticker_agent.ticker_agent.run` stub; collect intent, summary, and metrics per question.
- [x] Skip cleanly when no questions exist; errors are captured and surfaced in the report.

### 1.8 Market Context
- [x] Use `data_tools.fd_api.get_equity_snapshot` (or equivalent) to pull snapshots for key tickers from the scenario; include timestamps and sources.
- [ ] Aggregate market-wide/sector stats only if provided by the stub; otherwise, log unavailability gracefully.

### 1.9 Error Handling
- [ ] Implement per-step try/catch that records failures, keeps prior results, and proceeds unless configuration says otherwise.
- [ ] Add retry policy hooks (config-driven) for external calls; load via `.env` (using `load_dotenv()`): `DESK_AGENT_MAX_RETRIES`, `DESK_AGENT_BACKOFF_MS`, `DESK_AGENT_ABORT_AFTER_RETRY` (bool-ish). Defaults if unset: 2 retries, 500ms backoff, abort on 3rd failure with partial results captured.
- [ ] Detect missing dependencies early with a clear import/setup error.

## Task 2: Define 5 Scenarios

### 2.1 Scenario Schema
- [ ] Define schema in code (used by validator): `{"name": str, "description": str, "trades": list, "marks": list, "questions": list, "metadata": dict}`.
- [ ] Trade schema (align to OMS week spec): `{"trade_id": str, "ticker": str, "quantity": number, "price": number, "currency": str, "counterparty": str, "trade_dt": str (ISO), "settle_dt": str (ISO), "side": "BUY"|"SELL" optional notes}`.
- [ ] Mark schema (align to pricing week spec): `{"ticker": str, "internal_mark": number, "as_of": str (ISO), "source": str optional, "notes": str optional}`.
- [ ] Question schema: `{"question": str, "ticker": str optional, "intent_hint": str optional, "context": dict optional}` for ticker agent input.

### 2.2 Clean Day Scenario
- [x] Create `scenarios/clean_day.json` with multiple tickers/trades/marks, all valid, standard market conditions, no warnings expected.

### 2.3 Bad Mark Scenario
- [x] Create `scenarios/bad_mark.json` where marks have high/low/stale deviations; expect pricing agent to flag OUT_OF_TOLERANCE/REVIEW_NEEDED.

### 2.4 Wrong Ticker Mapping Scenario
- [x] Create `scenarios/wrong_ticker_mapping.json` with ambiguous/incorrect identifiers (e.g., "AAPL US", "AAPL.OQ", "XYZ123", deliberate ambiguity) to exercise normalization edges.

### 2.5 Mis-booked Trade Scenario
- [x] Create `scenarios/mis_booked_trade.json` covering wrong ticker, currency mismatch, price out of tolerance, wrong counterparty, missing fields, and settlement issues.

### 2.6 High-Vol Day Scenario
- [x] Create `scenarios/high_vol_day.json` showing volatile market moves, multiple pricing flags, unusual trade prices, and context data reflecting volatility.

### 2.7 Scenario Validation
- [ ] Add automated schema validation and a smoke execution for each scenario; fail fast with descriptive errors if any scenario is invalid.

## Task 3: Produce an Integrated Report

### 3.1 Report Schema
- [ ] Implement report structure exactly:
  ```json
  {
    "scenario": {"name": "...", "description": "...", "execution_date": "..."},
    "data_quality": {"ticker_normalizations": [...], "normalization_issues": [...], "confidence_scores": {...}},
    "trade_issues": [{"trade_id": "...", "status": "OK|WARNING|ERROR", "issues": [...], "ticker": "...", "counterparty": "..."}],
    "pricing_flags": [{"ticker": "...", "internal_mark": ..., "market_price": ..., "deviation": ..., "classification": "...", "explanation": "..."}],
    "market_context": {"key_tickers": [...], "market_movements": {...}, "sector_performance": {...}, "as_of_date": "..."},
    "ticker_agent_results": [{"question": "...", "intent": "...", "summary": "...", "metrics": {...}}],
    "narrative": "...",
    "summary": {"total_trades": ..., "trades_with_issues": ..., "total_marks": ..., "marks_flagged": ..., "overall_status": "OK|WARNING|ERROR"},
    "execution_metadata": {"execution_time_ms": ..., "timestamp": "...", "agents_executed": [...]}
  }
  ```

### 3.2 Data Quality
- [ ] Aggregate normalization successes, ambiguities, failures, and confidence scores; flag any missing identifiers.

### 3.3 Trade Issues
- [ ] Aggregate per-trade statuses; group issues by type and severity; retain original trade identifiers.

### 3.4 Pricing Flags
- [ ] Aggregate marks with classifications (OK, OUT_OF_TOLERANCE, REVIEW_NEEDED, NO_MARKET_DATA); include deviation calculations and explanations sorted by severity.

### 3.5 Market Context
- [ ] Include ticker snapshots, market-wide stats, sector performance, recent movements, dates, and data sources when available; leave empty structures when unavailable.

### 3.6 Ticker Agent Results
- [ ] List all questions with detected intent, summary, and metrics; include source/trace info if provided by the stub.

### 3.7 Narrative Generation
- [ ] Generate an exec-ready summary with key findings, issues, recommendations, and specific numbers; ensure it references the structured results.

### 3.8 Summary Statistics
- [ ] Compute totals and percentages for trades and marks, plus breakdowns by issue type/severity/ticker/counterparty.

### 3.9 Execution Metadata
- [ ] Record timings, timestamp, scenario name, configuration used, agents executed, and any errors encountered.

### 3.10 Report Generation Method
- [ ] Implement `generate_report(results: dict) -> dict` that assembles all sections, pretty-prints on demand, and can optionally write to a file.

### 3.11 Example Report
- [ ] Populate `examples/combined_report_example.json` with realistic data from one scenario, fully shaped per schema, and human-readable indentation.

## Configuration Management

### 4.1 Configuration File
- [ ] Implement `config.py` to load from env vars (via `load_dotenv()`), YAML/JSON file, then defaults; expose getters for sub-agent settings, paths, tolerances, logging levels, API endpoints, timeouts, and retry policy keys (`DESK_AGENT_MAX_RETRIES`, `DESK_AGENT_BACKOFF_MS`, `DESK_AGENT_ABORT_AFTER_RETRY` with defaults: 2 retries, 500ms backoff, abort on 3rd failure capturing partial results).

### 4.2 Sub-Agent Configuration
- [ ] Reference Master: data path and normalization settings.
- [ ] Trade QA: tolerance thresholds, valid counterparties list, settlement rules.
- [ ] Pricing: tolerance thresholds and stale mark thresholds.
- [ ] Ticker Agent: LLM model/config stub and intent definitions path.

## Testing

### 5.1 Unit Tests
- [ ] Cover orchestrator init, scenario loading/validation, mocked sub-agent integration, error handling, and report generation.

### 5.2 Integration Tests
- [ ] Run full workflow for each scenario (clean day, bad mark, wrong ticker mapping, mis-booked trade, high-vol day) using stubs; include error recovery and optional concurrent execution if supported.

### 5.3 Scenario Tests
- [ ] Ensure each scenario loads, executes, produces expected structural output, and exercises edge cases.

### 5.4 Report Validation Tests
- [ ] Validate report structure, data types, aggregation correctness, narrative presence, summary stats accuracy, and formatting.

## Logging

### 6.1 Orchestration Logging
- [ ] Log scenario start, each sub-agent call (name, input refs, execution time, result summary, errors), workflow steps, report generation, and completion.

### 6.2 Performance Logging
- [ ] Log total execution time plus per-agent and per-step timings; flag slow operations.

### 6.3 Error Logging
- [ ] Log errors with scenario name, step, type/message, stack trace, and relevant inputs; log warnings and recovery actions.

## Documentation

### 7.1 Module Documentation
- [ ] Create `src/desk_agent/README.md` with orchestrator overview, usage, configuration guide, scenario/report format, and integration notes.

### 7.2 Scenario Documentation
- [ ] Document schema, each scenario’s purpose/expected outcome/use case, and how to add new scenarios.

### 7.3 Report Documentation
- [ ] Document report structure, section meanings, examples, and interpretation guidelines.

## Performance and Reliability

### 8.1 Performance Optimization
- [ ] Optimize sub-agent execution (parallel where safe, caching if helpful, efficient data structures); target <30s end-to-end per scenario; profile hot paths.

### 8.2 Reliability
- [ ] Implement retries/timeouts (config-driven), keep partial results, and validate data at each step.

### 8.3 Error Recovery
- [ ] Continue on non-critical errors with meaningful messages and contextual logs; include error context in the report.

## Evaluation Criteria

### 9.1 Functionality
- [ ] Orchestrator runs reliably; all scenarios execute; all sub-agents integrate correctly; reports are produced per schema.

### 9.2 Output Quality
- [ ] Reports are business-grade with clear narrative and actionable insights; show integrated reasoning across issues/context.

### 9.3 Performance
- [ ] Scenarios complete in acceptable time; system handles load without memory leaks and uses resources efficiently.

## Optional Enhancements

### 10.1 Advanced Features
- [ ] Add support for custom workflow steps, conditional execution, branching, loops/iterations, and parallel sub-agent execution (config-toggle).

### 10.2 Reporting Enhancements
- [ ] Support additional report formats (Markdown, HTML, PDF), interactive views, charts/visualizations, and export options alongside JSON.

### 10.3 Scenario Management
- [ ] Add scenario versioning, templates, validation tools, comparison tools, and execution history tracking.

### 10.4 Integration Enhancements
- [ ] Add webhook support, event-driven execution, real-time updates, orchestrator API endpoints, and a CLI wrapper.
