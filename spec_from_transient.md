# TRANSIENT.AI – MICHAEL RAMP-UP PROGRAM (7 WEEKS)

This document contains all 7 weekly modules plus daily microtasks.

## Project Structure

The project uses a unified top-level structure with all source code in `src/` and all tests in `tests/`:

```
.
├── src/                      # All source code modules
│   ├── data_tools/          # Week 1: Financial data APIs and Q&A generation
│   ├── ticker_agent/        # Week 2: Ticker agent for financial reasoning
│   ├── refmaster/           # Week 3: Reference master normalization
│   ├── oms/                 # Week 4: OMS & trade capture QA
│   ├── pricing/             # Week 5: EOD pricing agent
│   ├── desk_agent/          # Week 6: Desk agent orchestrator
│   └── service/             # Week 7: FastAPI service wrapper
├── tests/                    # All test files (mirrors src/ structure)
│   ├── data_tools/
│   │   └── test_fd_api.py
│   ├── ticker_agent/
│   │   └── test_ticker_agent.py
│   ├── refmaster/
│   │   └── test_refmaster.py
│   ├── oms/
│   │   └── test_oms_agent.py
│   ├── pricing/
│   │   └── test_pricing_agent.py
│   ├── desk_agent/
│   │   └── test_orchestrator.py
│   └── service/
│       └── test_api.py
├── config/                   # Configuration files
│   └── tolerances.yaml
├── data/                     # Data files (seed data, marks)
│   ├── seed_data.csv
│   └── marks.csv
├── scenarios/                # Scenario files for testing
│   └── scenarios.json
├── examples/                 # Example outputs and reports
│   ├── snapshot_output.json
│   ├── sample_qa.jsonl
│   ├── pricing_report.md
│   └── combined_report_example.json
├── docs/                     # Documentation
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── DEMO_SCRIPT.md
│   └── INSTALL.md
├── logs/                     # Application logs
├── pyproject.toml            # Project configuration and dependencies (uv)
├── .env                      # Environment variables
└── README.md                 # Main project README
```

---

## WEEK 1 – Financial Data Foundations + First Agent Tooling

### Objective

Get fluent with financialdatasets.ai, the financial-datasets library, and build the first production-quality data tools that an AI agent will use later.

### 1. What You Will Learn

- How to pull real financial market data using financialdatasets.ai APIs
- How to work with the `financial-datasets` Python library for Q&A generation
- How to structure a modern Python project
- How to build a deterministic, production-safe data tool for AI agents
- How data tools plug into front-office workflows (OMS, risk, pricing)

### 2. Why This Matters (Business Context)

Agents are only as good as the data tools they can call.

Every Transient.AI client workflow depends on:

- Clean market data
- Consistent fundamentals
- Repeatable transformation logic

If the data layer is wrong, hedge funds lose money, compliance gets angry, and systems break.

This week gives you the stable, trusted data layer everything else will sit on.

### 3. Folder Structure to Create

```
.
├── src/
│   └── data_tools/
│       ├── __init__.py
│       ├── fd_api.py
│       ├── qa_builder.py
│       └── schemas.py
├── tests/
│   └── data_tools/
│       └── test_fd_api.py
├── examples/
│   ├── snapshot_output.json
│   └── sample_qa.jsonl
├── pyproject.toml
├── .env
└── README.md
```

### 4. Step-by-Step Tasks

#### Task 1 — Install Dependencies

```bash
uv add requests pandas pydantic python-dotenv financial-datasets
```

#### Task 2 — Build the Market Snapshot Tool

- Create `fd_api.py` with function `get_equity_snapshot(ticker: str) -> dict`
- Pull: latest close, 1D / 5D returns, market cap, sector/industry
- Output JSON with structure:

```json
{
  "ticker": "...",
  "price": ...,
  "return_1d": ...,
  "return_5d": ...,
  "market_cap": ...,
  "sector": "...",
  "source": "financialdatasets.ai"
}
```

#### Task 3 — Build the Q&A Generator

- Create `qa_builder.py`
- Use the financial-datasets library to extract Q&A from a 10-K PDF or MD&A section
- Output `.jsonl` file: `{"question": "...", "answer": "..."}`

#### Task 4 — CLI Tool

- Script: `python -m src.data_tools.fd_api AAPL`
- Print snapshot summary and save JSON

### 5. Daily Microtasks (Week 1)

**Day 1**

- Create project folder structure with `src/` and `tests/` directories
- Initialize project with `uv init` (or `uv sync` if pyproject.toml exists)
- Get FinancialDatasets API key into `.env`

**Day 2**

- Implement `fd_api.py::get_equity_snapshot(ticker)`
- Test manually for 3 tickers
- Save outputs in `examples/snapshot_output.json`

**Day 3**

- Install and import financial-datasets
- Pick 1–2 filings; implement `qa_builder.py::generate_qa_from_file(path)`
- Write first `sample_qa.jsonl`

**Day 4**

- Add `schemas.py` (Pydantic models for snapshot + QA entries)
- Add tests in `tests/data_tools/test_fd_api.py` validating schema and basic behavior

**Day 5**

- Write Week 1 README.md (objective, usage, examples)
- Refactor for clarity (function names, docstrings, comments)

### 6. Production Pressure Simulation

**Scenario:**

A convertible bond portfolio manager asks:

> "Give me a quick snapshot of the underlying equity's fundamentals, sentiment, and recent trend."

Deliver a JSON summary plus a 3-sentence overview using your tool.

### 7. Deliverables

- `get_equity_snapshot()`
- `generate_qa()`
- Sample outputs
- README explaining: inputs, outputs, and how it plugs into future agents

### 8. Evaluation Criteria

- Snapshot returns consistent structure
- No silent failures
- Q&A file produced cleanly
- Clear README
- Easy for next week's agent to call

---

## WEEK 2 – First Real Agent: Data-Aware Financial Reasoning

### Objective

Build a small agent that answers financial questions using real data via tools you built in Week 1.

### 1. What You Will Learn

- How to build a minimal agent architecture (prompt + tools + output)
- How to design AI tool interfaces
- How to blend structured data with natural-language reasoning
- How to build error handling and timeouts
- How to answer domain questions cleanly

### 2. Business Context

Front-office users won't tolerate hallucinated details or vague responses.

Agents must:

- Pull real data
- Cite the source
- Produce coherent, business-grade reasoning

This week builds the first "trusted finance agent."

### 3. Folder Structure

```
.
├── src/
│   ├── data_tools/          # (from Week 1)
│   └── ticker_agent/
│       ├── __init__.py
│       ├── ticker_agent.py
│       └── prompts.py
├── tests/
│   └── ticker_agent/
│       └── test_ticker_agent.py
└── examples/
```

### 4. Step-by-Step Tasks

#### Task 1 — Build a Minimal Agent

- API: `answer = ticker_agent.run(question: str, ticker: str)`

Flow:

1. Parse question
2. Call Week 1 data tools
3. Build structured answer
4. Generate natural-language explanation
5. Handle missing/invalid tickers

#### Task 2 — Add Business Logic Questions

Must support questions like:

- Summarize the last 4 years of revenue for NVDA.
- Compare realized vol over the last 90 days to the implied vol at issuance of this convertible.

(Even if implied vol isn't available, create a placeholder logic layer.)

#### Task 3 — Error Modes

- Network errors
- Missing fields
- Empty results
- Timeout

Return: `{"status":"error","reason":"..."}`.

### 5. Daily Microtasks (Week 2)

**Day 1**

- Add `src/ticker_agent/` module structure
- Draft `prompts.py` with system + tool description prompt strings

**Day 2**

- Implement `ticker_agent.run(question, ticker)` integrating Week 1 tools
- Hard-code 2–3 question patterns and answer templates

**Day 3**

- Expand questions supported (fundamentals, recent performance, risk)
- Ensure outputs include both "summary" and "metrics" fields

**Day 4**

- Implement error modes (invalid ticker, empty response, timeouts)
- Add tests in `tests/ticker_agent/test_ticker_agent.py`

**Day 5**

- Write Week 2 README.md with example inputs/outputs
- Sanity-check responses for 3–5 tickers

### 6. Production Pressure Simulation

**Scenario:**

PM sends an urgent message:

> "Give me a quick explanation of TSLA's fundamentals and risk trends before my investor call in 10 min."

Agent output must be fast, clear, free of hallucinations, and cite data sources.

### 7. Deliverables

- `ticker_agent.py`
- Tool logic
- Example responses
- README

### 8. Evaluation Criteria

- Answers grounded in data
- Structured + natural language output
- Good error handling
- Clean agent interface

---

## WEEK 3 – Reference Master AI: Identifier Normalization

### Objective

Use LLMs + your data tools to build a Reference Master Normalization Agent, echoing the system you owned for 10+ years.

### 1. What You Will Learn

- How to design entity normalization logic
- How to use LLMs to resolve ambiguous instrument descriptions
- How to build structured match/confidence scoring
- How to tie external FD datasets to internal schemas

### 2. Business Context

Every OMS, pricing, risk, and compliance system depends on accurate identifiers.

Bad mapping = bad pricing → bad P&L → broken books → regulatory trouble.

This week is high-stakes finance infrastructure.

### 3. Folder Structure

```
.
├── src/
│   ├── data_tools/          # (from Week 1)
│   ├── ticker_agent/        # (from Week 2)
│   └── refmaster/
│       ├── __init__.py
│       ├── schema.py
│       └── normalizer_agent.py
├── tests/
│   └── refmaster/
│       └── test_refmaster.py
├── data/
│   └── seed_data.csv
└── examples/
```

### 4. Step-by-Step Tasks

#### Task 1 — Define Schema

Fields:

- symbol
- isin
- cusip
- currency
- exchange
- pricing_source

#### Task 2 — Build Seed Data

Use 30–50 equities pulled from Week 1's FD API.

#### Task 3 — Build Normalization Agent

Input variations like: "AAPL US", "AAPL.OQ", "Apple Inc NASDAQ", "US0378331005"

Agent must:

1. Query the table
2. Apply matching logic
3. Return ranked matches
4. Include a confidence score

#### Task 4 — Add Ambiguity Handling

Handle multiple possible matches, low-confidence results, and unknowns.

### 5. Daily Microtasks (Week 3)

**Day 1**

- Add `src/refmaster/` module structure
- Design schema in `schema.py`

**Day 2**

- Populate `data/seed_data.csv` from FD API for 30–50 instruments
- Write loader that converts CSV into in-memory structures

**Day 3**

- Implement `normalizer_agent.normalize(description_or_id)` with matching logic

**Day 4**

- Add confidence scoring and ranked list of candidates
- Add tests with ambiguous cases

**Day 5**

- Write Week 3 README.md including narrative: how this sits between OMS and market data

### 6. Production Pressure Simulation

**Scenario:**

You are mid-migration from old OMS to new system.

Reference mismatches are blocking trade flow. Agent must help fix mappings fast.

### 7. Deliverables

- Schema file
- Normalization agent
- Test cases
- README

### 8. Evaluation Criteria

- High accuracy
- Strong ambiguity handling
- Scored results
- Clear mapping explanation

---

## WEEK 4 – AI-Augmented OMS & Trade Capture QA

### Objective

Integrate LLMs with your reference master to validate trades the way front-office systems require.

### 1. What You Will Learn

- How to define trade schemas
- How to write trade QA logic
- How to build a Trade QA Agent that catches booking errors
- How to design audit-friendly outputs

### 2. Business Context

Trade errors cost millions.

Systems you wrote historically guarded against this — now AI will assist.

### 3. Folder Structure

```
.
├── src/
│   ├── data_tools/          # (from Week 1)
│   ├── ticker_agent/        # (from Week 2)
│   ├── refmaster/           # (from Week 3)
│   └── oms/
│       ├── __init__.py
│       ├── schema.py
│       └── oms_agent.py
├── tests/
│   └── oms/
│       └── test_oms_agent.py
├── scenarios/
│   └── scenarios.json
└── examples/
```

### 4. Step-by-Step Tasks

#### Task 1 — Define Trade Schema

For equities, options, and simple credit (bond/CDS).

Fields:

- ticker
- quantity
- price
- currency
- counterparty
- trade_dt
- settle_dt

#### Task 2 — Build QA Checks

- Identifier mismatch
- Currency mismatch
- Price out of tolerance
- Wrong counterparty
- Missing fields

#### Task 3 — Build Trade QA Agent

Return structure:

- `status`: OK | WARNING | ERROR
- `issues`: [...]
- `explanation`: "..."

#### Task 4 — Build Synthetic Test Cases

Create `scenarios/scenarios.json` with ~20 synthetic trades and expected outcomes.

### 5. Daily Microtasks (Week 4)

**Day 1**

- Add `src/oms/` module structure
- Define trade schema in `src/oms/schema.py`

**Day 2**

- Implement base QA checks for required fields and currencies

**Day 3**

- Integrate Reference Master agent for identifier validation
- Integrate FD tools for price sanity checks

**Day 4**

- Implement `oms_agent.run(trade_json)` returning status + issues
- Create `scenarios/scenarios.json` with synthetic trades

**Day 5**

- Add tests in `tests/oms/test_oms_agent.py`
- Write Week 4 README.md with examples

### 6. Production Pressure Simulation

**Scenario:**

Operations flags several mis-booked trades after a volatile day.

Use your agent to QA them in under 30 seconds.

### 7. Deliverables

- OMS schema
- QA logic
- QA agent script
- Example outputs

### 8. Evaluation Criteria

- Catches 80%+ of scripted errors
- Clear explanations
- Structured output

---

## WEEK 5 – EOD Pricing Agent & Market Data Normalizer

### Objective

Build an EOD pricing sanity-check system integrating FD market data with internal marks.

### 1. What You Will Learn

- How to normalize market data
- How to cross-check internal marks with external benchmarks
- How to use agents to produce explanations for auditors
- How to design a config-driven pricing validation system

### 2. Business Context

EOD pricing errors → incorrect NAV → investor issues → audit risk.

Hedge funds want tooling that finds errors fast.

### 3. Folder Structure

```
.
├── src/
│   ├── data_tools/          # (from Week 1)
│   ├── ticker_agent/        # (from Week 2)
│   ├── refmaster/           # (from Week 3)
│   ├── oms/                 # (from Week 4)
│   └── pricing/
│       ├── __init__.py
│       └── pricing_agent.py
├── tests/
│   └── pricing/
│       └── test_pricing_agent.py
├── config/
│   └── tolerances.yaml
├── data/
│   └── marks.csv
└── examples/
    └── pricing_report.md
```

### 4. Step-by-Step Tasks

#### Task 1 — Create Synthetic EOD Mark File

50 instruments with:

- internal mark
- as-of date
- notes

#### Task 2 — Build Market Normalizer

- Pull FD close price
- Compare to internal mark
- Tag as: OK, OUT_OF_TOLERANCE, REVIEW_NEEDED

#### Task 3 — Build Pricing Agent

Explain discrepancies in plain English and aggregate results.

### 5. Daily Microtasks (Week 5)

**Day 1**

- Add `src/pricing/` module structure
- Draft `data/marks.csv` with internal marks

**Day 2**

- Implement loader to enrich marks with FD close prices

**Day 3**

- Define tolerance configuration in `config/tolerances.yaml`
- Implement classification logic

**Day 4**

- Implement `pricing_agent.run(marks)` to produce flags + explanations

**Day 5**

- Generate `examples/pricing_report.md`
- Add tests in `tests/pricing/test_pricing_agent.py`
- Write Week 5 README.md

### 6. Production Pressure Simulation

**Scenario:**

Auditor requests explanation for 12 marks that diverged significantly from market data.

Your agent must produce an audit-friendly report.

### 7. Deliverables

- Pricing agent
- Normalizer
- Example pricing report

### 8. Evaluation Criteria

- Clean output
- Configurable tolerances
- Concise explanations

---

## WEEK 6 – Full Front-Office Workflow: Desk Agent MVP

### Objective

Combine all previous parts into a full Desk Agent workflow that can run a scenario end-to-end.

### 1. What You Will Learn

- Workflow orchestration
- How to chain multiple agents into a unified workflow
- How to design for predictable latency
- How to communicate results to front-office users

### 2. Business Context

This is the first version of a client-facing agent you would show a hedge fund CTO, PM, or COO.

### 3. Folder Structure

```
.
├── src/
│   ├── data_tools/          # (from Week 1)
│   ├── ticker_agent/        # (from Week 2)
│   ├── refmaster/           # (from Week 3)
│   ├── oms/                 # (from Week 4)
│   ├── pricing/             # (from Week 5)
│   └── desk_agent/
│       ├── __init__.py
│       ├── orchestrator.py
│       └── config.py
├── tests/
│   └── desk_agent/
│       └── test_orchestrator.py
├── scenarios/
│   └── (scenario files)
├── logs/
└── examples/
    └── combined_report_example.json
```

### 4. Step-by-Step Tasks

#### Task 1 — Build the Orchestrator

Should call:

- Reference Master Agent
- Trade QA Agent
- Pricing Agent
- Data snapshot tools

#### Task 2 — Define 5 Scenarios

Examples:

- Clean day
- Bad mark
- Wrong ticker mapping
- Mis-booked trade
- High-vol day

#### Task 3 — Produce an Integrated Report

Combine outputs into structured summary:

```json
{
  "data_quality": {...},
  "trade_issues": [...],
  "pricing_flags": [...],
  "market_context": {...},
  "narrative": "..."
}
```

### 5. Daily Microtasks (Week 6)

**Day 1**

- Add `src/desk_agent/` module structure
- Write `src/desk_agent/config.py` (or `config.yaml`) referencing sub-agents

**Day 2**

- Implement `orchestrator.py` skeleton to call sub-agents

**Day 3**

- Implement scenario runner using files in `scenarios/`

**Day 4**

- Implement aggregated report structure in `orchestrator.py`
- Save example report in `examples/combined_report_example.json`

**Day 5**

- Add tests in `tests/desk_agent/test_orchestrator.py`
- Write Week 6 README.md
- Review latency and logging basics

### 6. Production Pressure Simulation

**Scenario:**

You have 15 minutes before a client demo.

System must run end-to-end and produce a readable summary.

### 7. Deliverables

- Complete orchestrator
- Scenario library
- Logs
- Combined report

### 8. Evaluation Criteria

- Runs reliably
- Outputs business-grade summaries
- Integrated reasoning

---

## WEEK 7 – Hardening, Packaging, and Client Demo Prep

### Objective

Turn the Desk Agent MVP into a presentable, client-facing artifact.

### 1. What You Will Learn

- Packaging into a pip-installable module
- Adding a FastAPI wrapper
- Writing clean engineering documentation
- Building a client demo storyline
- Presenting at CTO-grade level

### 2. Business Context

This is what you'd actually show a live hedge fund client considering Transient.AI.

You are demonstrating reliability, business understanding, technical depth, and domain fluency.

### 3. Folder Structure

```
.
├── src/
│   ├── data_tools/          # (from Week 1)
│   ├── ticker_agent/        # (from Week 2)
│   ├── refmaster/           # (from Week 3)
│   ├── oms/                 # (from Week 4)
│   ├── pricing/             # (from Week 5)
│   ├── desk_agent/          # (from Week 6)
│   └── service/
│       ├── __init__.py
│       ├── api.py
│       ├── main.py
│       └── config.py
├── tests/
│   └── service/
│       └── test_api.py
├── docs/
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── DEMO_SCRIPT.md
│   └── INSTALL.md
├── setup.py
├── pyproject.toml
└── README.md
```

### 4. Step-by-Step Tasks

#### Task 1 — Wrap Desk Agent in FastAPI

- Expose `POST /run-desk-agent`
- Input = scenario or custom data
- Output = structured JSON

#### Task 2 — Add Logging

- JSON logs
- Timings
- Error tracing

#### Task 3 — Write Architecture Doc

- Diagram
- Workflow steps
- Data flow
- Extension points

#### Task 4 — Write Demo Script

Explain to a CTO:

- The problem
- The workflow
- The value
- The differentiator

### 5. Daily Microtasks (Week 7)

**Day 1**

- Add `src/service/` module structure
- Implement FastAPI `/health` endpoint in `src/service/api.py`

**Day 2**

- Wrap Desk Agent: implement `POST /run-desk-agent` in `src/service/api.py` calling orchestrator

**Day 3**

- Add config handling and basic JSON logging
- Add tests in `tests/service/test_api.py`

**Day 4**

- Write `docs/ARCHITECTURE.md` and `docs/INSTALL.md`

**Day 5**

- Write `docs/DEMO_SCRIPT.md`
- Final polish on README.md and service behavior

### 6. Production Pressure Simulation

**Scenario:**

You must deliver a working agent plus a polished narrative for a real institutional client demo.

### 7. Deliverables

- Working FastAPI service
- Documentation
- Demo script
- Installation instructions

### 8. Evaluation Criteria

- Runs cleanly
- Clear docs
- Demonstrates domain + engineering mastery
- Ready for real-world demo

