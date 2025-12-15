# Implementation Strategy: Non-Optional TODOs

## Summary
This document lists all non-optional (unchecked) todos across all modules and provides a strategic implementation plan.

---

## 1. OMS Module (`src/oms/todo.md`)

### Remaining Tasks

#### Task 3.2: Overall Status Rules
- **Line 55**: Implement overall status rules: ERROR if any ERROR issues; WARNING if no ERROR but at least one WARNING; else OK. Collect all issues (no early exit).

#### Task 4: Synthetic Test Cases
- **Lines 71-77**: Create comprehensive test scenarios in `scenarios/scenarios.json`:
  - Valid trades (3–5): normal equity, valid multi-currency if allowed, standard settlement
  - Missing fields (3–4): missing ticker/quantity/price/currency/counterparty/dates
  - Identifier mismatches (2–3): invalid ticker, ambiguous ticker, format issues
  - Currency mismatches (2): wrong currency vs ref, bad currency code format
  - Price tolerance (3–4): >5% high/low, 2–5% high/low, stale price data
  - Counterparty issues (1–2): invalid format, suspicious name
  - Settlement issues (2–3): settle before trade, non-standard T+1/T+3, weekend/holiday settle

#### Testing
- **Lines 80-84**: 
  - Unit: each QA check individually
  - Integration: `OMSAgent.run` with valid trades, each error type, multiple errors in one trade, edge cases (missing data, API failures)
  - Scenario-driven: run all `scenarios.json` cases and assert expected status/issues
  - Error handling: market data API failures, missing ref data, invalid JSON input, network timeouts
  - Performance: batch of trades completes in <30s

#### Documentation
- **Line 88**: Document QA checks and thresholds; provide example trade JSON inputs/outputs; document error codes/messages

#### Integration Points
- **Line 93**: Ensure compatibility with `data_tools.schemas.Trade` or map to OMS schema; handle Pydantic validation errors

#### Production Readiness
- **Lines 96-99**:
  - Logging: validation results, API calls, errors/warnings
  - Metrics/telemetry (optional): validation time, error rates by type, API call success rates
  - Config support: price tolerances, counterparties, settlement rules, API endpoints/keys
  - Audit trail: log all validated trades, store validation results, timestamp validations

#### Evaluation Criteria
- **Line 102**: Catch 80%+ of scripted scenario errors; explanations are clear/actionable; structured output consistent; performs batch validation <30s; works on real-world-like trades if available

---

## 2. Pricing Module (`src/pricing/todo.md`)

### Remaining Tasks

#### Evaluation Criteria
- **Lines 94-96**:
  - Functionality: processes all marks in `data/marks.csv`, classifies correctly, generates actionable explanations, and produces an audit-friendly report
  - Quality: concise explanations, professional report formatting, flexible config, clear errors
  - Performance: completes 50 marks in reasonable time (<30s), respects rate limits, efficient memory use

---

## 3. Desk Agent Module (`src/desk_agent/todo.md`)

### Remaining Tasks

#### Task 1.4: Reference Master Integration
- **Line 29**: Surface normalization failures without stopping the workflow; include them in `data_quality`

#### Task 1.8: Market Context
- **Line 47**: Aggregate market-wide/sector stats only if provided by the stub; otherwise, log unavailability gracefully

#### Task 1.9: Error Handling
- **Lines 50-52**: 
  - Implement per-step try/catch that records failures, keeps prior results, and proceeds unless configuration says otherwise
  - Add retry policy hooks (config-driven) for external calls; load via `.env`: `DESK_AGENT_MAX_RETRIES`, `DESK_AGENT_BACKOFF_MS`, `DESK_AGENT_ABORT_AFTER_RETRY` (defaults: 2 retries, 500ms backoff, abort on 3rd failure)
  - Detect missing dependencies early with a clear import/setup error

#### Task 2.1: Scenario Schema
- **Lines 57-60**: Define schema in code (used by validator):
  - Main schema: `{"name": str, "description": str, "trades": list, "marks": list, "questions": list, "metadata": dict}`
  - Trade schema: `{"trade_id": str, "ticker": str, "quantity": number, "price": number, "currency": str, "counterparty": str, "trade_dt": str (ISO), "settle_dt": str (ISO), "side": "BUY"|"SELL" optional notes}`
  - Mark schema: `{"ticker": str, "internal_mark": number, "as_of": str (ISO), "source": str optional, "notes": str optional}`
  - Question schema: `{"question": str, "ticker": str optional, "intent_hint": str optional, "context": dict optional}`

#### Task 2.7: Scenario Validation
- **Line 78**: Add automated schema validation and a smoke execution for each scenario; fail fast with descriptive errors if any scenario is invalid

#### Task 3: Produce an Integrated Report
- **Lines 83-120**: Implement complete report structure:
  - **3.1**: Report schema with all fields (scenario, data_quality, trade_issues, pricing_flags, market_context, ticker_agent_results, narrative, summary, execution_metadata)
  - **3.2**: Data quality aggregation (normalization successes, ambiguities, failures, confidence scores)
  - **3.3**: Trade issues aggregation (per-trade statuses, group by type/severity)
  - **3.4**: Pricing flags aggregation (marks with classifications, deviations, explanations)
  - **3.5**: Market context (ticker snapshots, market-wide stats, sector performance)
  - **3.6**: Ticker agent results (all questions with intent, summary, metrics)
  - **3.7**: Narrative generation (exec-ready summary with key findings, issues, recommendations)
  - **3.8**: Summary statistics (totals, percentages, breakdowns by issue type/severity/ticker/counterparty)
  - **3.9**: Execution metadata (timings, timestamp, scenario name, configuration, agents executed, errors)
  - **3.10**: Report generation method (`generate_report(results: dict) -> dict`)
  - **3.11**: Example report (`examples/combined_report_example.json`)

#### Task 4: Configuration Management
- **Lines 131-137**:
  - **4.1**: Implement `config.py` to load from env vars (via `load_dotenv()`), YAML/JSON file, then defaults; expose getters for sub-agent settings, paths, tolerances, logging levels, API endpoints, timeouts, and retry policy keys
  - **4.2**: Sub-agent configuration (Reference Master, Trade QA, Pricing, Ticker Agent)

#### Task 5: Testing
- **Lines 142-151**:
  - **5.1**: Unit tests (orchestrator init, scenario loading/validation, mocked sub-agent integration, error handling, report generation)
  - **5.2**: Integration tests (full workflow for each scenario using stubs, error recovery, optional concurrent execution)
  - **5.3**: Scenario tests (ensure each scenario loads, executes, produces expected structural output, exercises edge cases)
  - **5.4**: Report validation tests (validate report structure, data types, aggregation correctness, narrative presence, summary stats accuracy, formatting)

#### Task 6: Logging
- **Lines 156-162**:
  - **6.1**: Orchestration logging (scenario start, each sub-agent call, workflow steps, report generation, completion)
  - **6.2**: Performance logging (total execution time, per-agent and per-step timings, flag slow operations)
  - **6.3**: Error logging (errors with scenario name, step, type/message, stack trace, relevant inputs, warnings, recovery actions)

#### Task 7: Documentation
- **Lines 167-173**:
  - **7.1**: Module documentation (`src/desk_agent/README.md`)
  - **7.2**: Scenario documentation (schema, each scenario's purpose/expected outcome/use case, how to add new scenarios)
  - **7.3**: Report documentation (report structure, section meanings, examples, interpretation guidelines)

#### Task 8: Performance and Reliability
- **Lines 178-184**:
  - **8.1**: Performance optimization (optimize sub-agent execution, target <30s end-to-end per scenario, profile hot paths)
  - **8.2**: Reliability (implement retries/timeouts, keep partial results, validate data at each step)
  - **8.3**: Error recovery (continue on non-critical errors with meaningful messages and contextual logs, include error context in report)

#### Task 9: Evaluation Criteria
- **Lines 189-195**:
  - **9.1**: Functionality (orchestrator runs reliably, all scenarios execute, all sub-agents integrate correctly, reports produced per schema)
  - **9.2**: Output quality (reports are business-grade with clear narrative and actionable insights, show integrated reasoning)
  - **9.3**: Performance (scenarios complete in acceptable time, system handles load without memory leaks, efficient resource use)

---

## 4. Service Module (`src/service/todo.md`)

### Remaining Tasks

#### Task 1.5: Error Handling
- **Line 27**: Define custom exceptions and global handlers; map to HTTP codes (200, 400 validation, 404 scenario missing, 500 internal, 503 dependency down); include error details and logging

#### Task 2: Logging
- **Lines 30-34**:
  - Structured JSON logging with levels; console for dev, file for prod (rotation optional)
  - Request/response logging (endpoint/method, request ID (UUID), timestamp, sanitized payload, response status/time/size, request ID in headers)
  - Timing/perf logging (per-endpoint duration, per-sub-agent timings, total orchestrator time, flag slow requests)
  - Error tracing (full stack traces with context, correlation IDs, external API failures, validation errors)
  - Audit logging (record scenario runs, trade validations, pricing validations with timestamps and request IDs)

#### Task 3: Architecture Docs
- **Lines 37-42**: Create `docs/ARCHITECTURE.md`:
  - Executive summary
  - High-level architecture
  - Component roles
  - Diagram (ASCII/Mermaid/image) showing service layer, orchestrator, sub-agents, data sources, data flow, interactions
  - End-to-end workflow steps (request → parse → orchestrator → sub-agents → aggregate → response) with decision/error paths
  - Data flow (input/output schemas, transformations, caching, external API deps)
  - Extension points (adding agents/scenarios, config options, plugin/versioning strategy)
  - Technical details (stack, dependencies, deployment architecture, scaling, security considerations)

#### Task 4: Demo Script
- **Lines 45-50**: Create `docs/DEMO_SCRIPT.md`:
  - CTO-ready structure with timing and talking points
  - Problem statement (booking/pricing errors, manual pain, regulatory pressure) with concrete examples/impact
  - Workflow demo (end-to-end run, show components, scenarios, real-time results, automation benefits)
  - Value props (time/error/cost savings, compliance, scalability, ROI if available)
  - Differentiators (AI-augmented validation, integrated workflow, real-time processing, reporting, extensibility, competitive positioning)
  - Demo scenarios (2–3: clean day, mis-booked trade, complex multi-issue) with expected outputs and backups for API issues

#### Configuration Management
- **Lines 53-55**: Implement `src/service/config.py`:
  - Load config from env vars (via `load_dotenv()`), then file (YAML/JSON), then defaults
  - Support: API keys, endpoints, timeouts, logging levels, feature flags, scenario paths, tolerance thresholds, environment selection (dev/stage/prod)
  - Document required env vars; validate on startup

#### Packaging and Installation
- **Lines 58-60**:
  - Review/update `pyproject.toml` for metadata, deps, entry points, version
  - Create `docs/INSTALL.md`: prerequisites (Python, system reqs, external deps), install steps (clone, deps, env vars, run service), Docker/deployment options
  - Build/distribution: create wheel/sdist, test install, document package install

#### Testing
- **Lines 63-65**:
  - API tests (health, main endpoint with valid/invalid scenario, custom data, errors, request validation, response format, error responses)
  - Integration (full workflow with real scenarios, optional mocks for external APIs, error recovery, concurrent requests if applicable)
  - Performance (response times, load if applicable, timing logs accuracy, timeout handling)

#### Documentation
- **Lines 68-70**:
  - Main `README.md`: overview, quick start, features, architecture summary, install link, usage examples, contributing, license
  - API docs: ensure OpenAPI generation, endpoint docstrings, request/response examples, error codes, auth (if any)
  - Code docs: docstrings, type hints, complex logic notes, minimal inline comments where needed

#### Production Readiness
- **Lines 73-76**:
  - Error handling (graceful degradation, retries for transient failures, circuit breakers optional, timeouts, resource cleanup)
  - Security (input validation, output sanitization, sensitive data redaction in logs, secure defaults, document considerations)
  - Monitoring (health monitoring, metrics: request/error rates, response times, success rate, alerts if applicable)
  - Performance (optimize slow paths, caching where appropriate, profile hot paths)

#### Demo Preparation
- **Lines 79-81**:
  - Demo environment (clean setup, preload test data, verify scenarios, backups for API failures, end-to-end rehearsal)
  - Materials (slides if needed, demo script, example outputs, Q&A prep, technical deep-dive materials)
  - Practice (run through script, time it, identify/presolve risks, refine talking points)

#### Evaluation Criteria
- **Lines 84-87**:
  - Functionality (service runs cleanly, endpoints correct, robust error handling, comprehensive logging)
  - Documentation (architecture clear, install accurate, demo script compelling, README professional)
  - Client readiness (shows domain and engineering competence, polished presentation, demo-ready)
  - Code quality (clean, tested, documented, best practices)

---

## Implementation Strategy

### Phase 1: Core Functionality (Foundation)
**Priority: HIGH | Estimated Time: 2-3 days**

1. **OMS Module - Status Rules & Test Scenarios**
   - Implement overall status rules in `oms_agent.py` (line 55)
   - Create comprehensive test scenarios in `scenarios/scenarios.json` (lines 71-77)
   - This enables proper validation and testing

2. **Desk Agent - Core Orchestration**
   - Implement scenario schema definition (lines 57-60)
   - Implement report structure and generation (Task 3, lines 83-120)
   - Add error handling and retry policy (lines 50-52)
   - This is the central orchestrator that ties everything together

3. **Desk Agent - Configuration**
   - Implement `config.py` with env/file/defaults loading (lines 131-137)
   - This enables proper configuration management

### Phase 2: Integration & Testing (Quality Assurance)
**Priority: HIGH | Estimated Time: 2-3 days**

1. **OMS Module - Testing**
   - Unit tests for each QA check (line 80)
   - Integration tests for `OMSAgent.run` (line 81)
   - Scenario-driven tests (line 82)
   - Error handling tests (line 83)
   - Performance tests (line 84)

2. **Desk Agent - Testing**
   - Unit tests (lines 142-143)
   - Integration tests for all scenarios (lines 145-146)
   - Scenario validation tests (lines 148-149)
   - Report validation tests (lines 151-152)

3. **Service Module - Testing**
   - API tests (line 63)
   - Integration tests (line 64)
   - Performance tests (line 65)

### Phase 3: Production Readiness (Reliability)
**Priority: MEDIUM | Estimated Time: 2-3 days**

1. **OMS Module - Production Features**
   - Logging implementation (line 96)
   - Config support (line 98)
   - Audit trail (line 99)
   - Documentation updates (line 88)
   - Integration with `data_tools.schemas.Trade` (line 93)

2. **Desk Agent - Production Features**
   - Logging (Task 6, lines 156-162)
   - Performance optimization (lines 178-184)
   - Error recovery (lines 184-185)
   - Documentation (Task 7, lines 167-173)

3. **Service Module - Production Features**
   - Error handling (line 27)
   - Logging (Task 2, lines 30-34)
   - Production readiness (lines 73-76)
   - Configuration management (lines 53-55)

### Phase 4: Documentation & Demo (Presentation)
**Priority: MEDIUM | Estimated Time: 2-3 days**

1. **Service Module - Documentation**
   - Architecture docs (`docs/ARCHITECTURE.md`, lines 37-42)
   - Demo script (`docs/DEMO_SCRIPT.md`, lines 45-50)
   - Installation guide (`docs/INSTALL.md`, lines 58-60)
   - Main README updates (lines 68-70)

2. **Service Module - Demo Preparation**
   - Demo environment setup (line 79)
   - Materials preparation (line 80)
   - Practice runs (line 81)

3. **Evaluation & Final Polish**
   - Run evaluation criteria checks for all modules
   - Final testing and bug fixes
   - Code review and cleanup

### Phase 5: Remaining Items (Polish)
**Priority: LOW | Estimated Time: 1-2 days**

1. **Desk Agent - Remaining Features**
   - Surface normalization failures (line 29)
   - Market-wide/sector stats aggregation (line 47)
   - Scenario validation automation (line 78)

2. **Pricing Module - Evaluation**
   - Evaluation criteria verification (lines 94-96)

3. **Final Integration Testing**
   - End-to-end testing across all modules
   - Performance benchmarking
   - Documentation review

---

## Dependencies & Ordering

### Critical Path
1. **OMS status rules** → **OMS test scenarios** → **Desk Agent report structure** → **Desk Agent config** → **Service API**
2. **Testing** can be done in parallel once core functionality is complete
3. **Documentation** should be done alongside implementation but finalized in Phase 4

### Blocking Relationships
- Desk Agent report structure blocks Service API endpoint implementation
- OMS test scenarios block comprehensive testing
- Configuration management blocks production readiness features
- Documentation blocks demo preparation

### Parallel Work Opportunities
- OMS testing and Desk Agent testing can be done in parallel
- Service logging and Desk Agent logging can be implemented simultaneously
- Documentation can be written alongside code implementation

---

## Risk Mitigation

1. **Complex Report Structure**: Break down Task 3 of Desk Agent into smaller sub-tasks, implement incrementally
2. **Integration Testing**: Start with simple scenarios, gradually add complexity
3. **Performance Targets**: Profile early, optimize hot paths, consider caching strategies
4. **Demo Preparation**: Create backup scenarios and mock data for API failures
5. **Configuration Complexity**: Use a simple, extensible config structure, validate early

---

## Success Criteria

- All non-optional todos completed and checked
- All tests passing (unit, integration, scenario-driven)
- Performance targets met (<30s for scenarios, <30s for batch validation)
- Documentation complete and professional
- Demo-ready with backup plans
- Production-ready error handling and logging
- Clean, maintainable code following best practices
