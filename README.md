# Transient.AI - Desk Agent Orchestrator

**AI-Augmented Operations Automation for Hedge Funds**

Transient.AI is a production-grade system that automates end-of-day validation workflows for hedge fund operations teams. Built from the ground up in 7 weeks, this demonstrates domain expertise in financial operations, modern AI engineering, and production system design.

## 🎯 Business Value

**Problem**: Operations teams at hedge funds manually validate 50+ positions and 20+ trades daily, taking 2-4 hours and risking costly errors. Trade booking mistakes and pricing deviations can cost millions in losses and regulatory penalties.

**Solution**: Desk Agent Orchestrator automates the entire workflow in **under 30 seconds** with comprehensive audit trails, catching 80%+ of errors before they impact the books.

**Impact**:
- ⏱️ **Time Savings**: 2-4 hours → 30 seconds (99.7% faster)
- ✅ **Error Reduction**: 80%+ error detection rate
- 📊 **Audit-Ready**: Full execution traces with request IDs
- 🔧 **Extensible**: Modular agents, configurable tolerances
- 💰 **ROI**: Prevents multi-million dollar booking errors

---

## 🏗️ Architecture Overview

The system integrates 5 specialized AI agents through a central orchestrator:

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Service                          │
│                     (Week 7: Service Layer)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Desk Agent Orchestrator                       │
│                   (Week 6: Integration Hub)                     │
└─┬─────────┬──────────┬──────────┬──────────┬────────────────────┘
  │         │          │          │          │
  ▼         ▼          ▼          ▼          ▼
┌───────┐ ┌─────┐  ┌────────┐ ┌────────┐ ┌─────────────┐
│Refmstr│ │ OMS │  │Pricing │ │Ticker  │ │Market Data  │
│ Week3 │ │Week4│  │ Week5  │ │Agent   │ │  (Week 1)   │
│       │ │     │  │        │ │(Week2) │ │             │
└───────┘ └─────┘  └────────┘ └────────┘ └─────────────┘
    │        │          │          │            │
    ▼        ▼          ▼          ▼            ▼
┌─────────────────────────────────────────────────────────┐
│              External Data Sources                      │
│  • FD Market Data API    • Reference Data               │
│  • Internal Marks        • Trade Records                │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 Project Structure

```
transient/
├── src/
│   ├── data_tools/         # Week 1: Financial Datasets API integration
│   ├── ticker_agent/       # Week 2: LLM-powered ticker Q&A agent
│   ├── refmaster/          # Week 3: Ticker normalization & mapping
│   ├── oms/                # Week 4: Trade validation & booking QA
│   ├── pricing/            # Week 5: EOD pricing sanity checks
│   ├── desk_agent/         # Week 6: Multi-agent orchestrator
│   └── service/            # Week 7: FastAPI REST service
├── tests/                  # Comprehensive test suite (50+ tests)
├── scenarios/              # Test scenarios (clean_day, bad_mark, etc.)
├── examples/               # Sample reports and outputs
├── docs/                   # Architecture, install, demo scripts
├── pyproject.toml          # Package config & dependencies
└── .env.example            # Environment configuration template
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- API keys for Financial Datasets (get free key at https://financialdatasets.ai)

### Installation

```bash
# Clone repository
git clone https://github.com/transient-ai/desk-agent.git
cd desk-agent

# Install dependencies
pip install -e .

# Configure API keys
cp .env.example .env
# Edit .env and add your FD_API_KEY
```

### Run the Service

```bash
# Start FastAPI service (default: http://0.0.0.0:8000)
python -m src.service.main

# Or use the entry point
desk-agent-service

# Health check
curl http://localhost:8000/health

# Run a scenario
curl -X POST http://localhost:8000/run-desk-agent \
  -H "Content-Type: application/json" \
  -d '{"scenario": "scenarios/clean_day.json"}'
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run specific module tests
pytest tests/desk_agent/
pytest tests/service/
```

---

## 📚 Module Documentation

### Week 1: Data Tools (`src/data_tools/`)
**Purpose**: Integration with Financial Datasets API for market data

**Features**:
- Equity snapshots (price, volume, fundamentals)
- Real-time market data fetching
- Data normalization and caching
- Error handling and rate limiting

**Usage**:
```python
from src.data_tools.fd_api import get_equity_snapshot

snapshot = get_equity_snapshot("AAPL")
print(f"Price: {snapshot.price}, Market Cap: {snapshot.market_cap}")
```

**Docs**: `src/data_tools/README.md`

---

### Week 2: Ticker Agent (`src/ticker_agent/`)
**Purpose**: LLM-powered Q&A agent for ticker-specific questions

**Features**:
- Natural language queries about tickers
- Intent classification (price, fundamentals, risk, generic)
- Context-aware responses
- Performance metrics tracking

**Usage**:
```python
from src.ticker_agent import ticker_agent

result = ticker_agent.run("What's the outlook for AAPL?")
print(result["summary"])  # Concise answer
print(result["intent"])   # "fundamentals"
```

**Docs**: `src/ticker_agent/README.md`

---

### Week 3: Reference Master (`src/refmaster/`)
**Purpose**: Ticker normalization for varied input formats

**Features**:
- Handles AAPL US, AAPL.OQ, Apple Inc, US0378331005 (ISIN), etc.
- Confidence scoring and ambiguity detection
- Fuzzy matching with ranked results
- 30-50 equity reference data seed

**Usage**:
```python
from src.refmaster.normalizer_agent import normalize_ticker

results = normalize_ticker("AAPL US")
print(results[0].equity.symbol)    # "AAPL"
print(results[0].confidence)       # 0.95
```

**Docs**: `src/refmaster/README.md`

---

### Week 4: OMS Agent (`src/oms/`)
**Purpose**: Trade validation and booking error detection

**Features**:
- Schema validation (ticker, quantity, price, currency, dates)
- Business rule checks (settlement dates, price tolerance, counterparty)
- Integration with refmaster for ticker validation
- Structured outputs (OK | WARNING | ERROR)

**Usage**:
```python
from src.oms import OMSAgent

agent = OMSAgent()
result = agent.run({
    "ticker": "AAPL",
    "quantity": 100,
    "price": 150.00,
    "currency": "USD",
    "trade_dt": "2024-01-15",
    "settle_dt": "2024-01-17"
})
print(result["status"])       # "OK"
print(result["issues"])       # []
```

**Docs**: `src/oms/README.md`

---

### Week 5: Pricing Agent (`src/pricing/`)
**Purpose**: EOD pricing validation against market data

**Features**:
- Mark-to-market validation with tolerance checks
- Classifications: OK, REVIEW_NEEDED, OUT_OF_TOLERANCE, STALE_MARK, NO_MARKET_DATA
- Deviation percentage calculations
- Batch processing with aggregated summaries

**Usage**:
```python
from src.pricing import PricingAgent

agent = PricingAgent()
result = agent.run([
    {"ticker": "AAPL", "internal_mark": 150.00, "as_of": "2024-01-15"}
])
print(result["enriched_marks"][0]["classification"])  # "OK"
print(result["summary"]["counts"]["OK"])              # 1
```

**Docs**: `src/pricing/README.md`

---

### Week 6: Desk Agent Orchestrator (`src/desk_agent/`)
**Purpose**: Multi-agent integration hub with scenario execution

**Features**:
- Orchestrates all 5 sub-agents in a single workflow
- Scenario-based testing (JSON/YAML scenarios)
- Comprehensive reporting (9 sections: data_quality, trade_issues, pricing_flags, market_context, etc.)
- Retry logic, parallel execution, execution tracing
- Smoke testing across all scenarios

**Usage**:
```python
from src.desk_agent.orchestrator import DeskAgentOrchestrator

orch = DeskAgentOrchestrator()
report = orch.run_scenario("scenarios/clean_day.json")

print(report["summary"]["overall_status"])    # "OK"
print(report["summary"]["total_trades"])      # 4
print(report["summary"]["marks_flagged"])     # 0
```

**Docs**: `src/desk_agent/README.md`

---

### Week 7: Service Layer (`src/service/`)
**Purpose**: FastAPI REST wrapper for production deployment

**Features**:
- RESTful API with 7 endpoints
- Structured JSON logging with request IDs
- Configuration management (env vars, file, defaults)
- Error handling with HTTP status codes
- Request timeouts and validation
- OpenAPI documentation at `/docs`

**Endpoints**:
- `GET /health` - Service health and dependency checks
- `POST /run-desk-agent` - Execute orchestrator for scenario
- `GET /scenarios` - List available scenarios
- `GET /scenarios/{name}` - Get scenario details
- `POST /validate-trade` - Validate single trade via OMS
- `POST /validate-pricing` - Validate marks via pricing agent
- `GET /status` - Service status

**Docs**: `docs/README.md`, `docs/ARCHITECTURE.md`, `docs/INSTALL.md`

---

## 🎬 Demo Scenarios

We provide 5 production-ready test scenarios:

1. **`clean_day.json`** - Happy path: all trades and marks clean
2. **`bad_mark.json`** - Pricing issues: OUT_OF_TOLERANCE, STALE_MARK, NO_MARKET_DATA
3. **`mis_booked_trade.json`** - OMS issues: settlement errors, price tolerance violations
4. **`wrong_ticker_mapping.json`** - Refmaster issues: ambiguous tickers, invalid formats
5. **`high_vol_day.json`** - Market volatility: sector analysis, multiple flags

**Run Demo**:
```bash
# Clean baseline (should complete with status: OK)
curl -X POST http://localhost:8000/run-desk-agent \
  -H "Content-Type: application/json" \
  -d '{"scenario": "scenarios/clean_day.json"}'

# Mis-booked trades (should detect 4 ERROR trades)
curl -X POST http://localhost:8000/run-desk-agent \
  -H "Content-Type: application/json" \
  -d '{"scenario": "scenarios/mis_booked_trade.json"}'
```

See **`docs/DEMO_SCRIPT.md`** for full CTO-ready presentation flow.

---

## 🧪 Testing

Comprehensive test suite with 50+ tests across all modules:

```bash
# Run all tests
pytest

# Run specific module
pytest tests/desk_agent/test_orchestrator.py
pytest tests/service/test_api.py

# Run with coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

**Test Coverage**:
- `tests/data_tools/` - API integration tests
- `tests/ticker_agent/` - Agent response tests
- `tests/refmaster/` - Normalization tests
- `tests/oms/` - Trade validation tests
- `tests/pricing/` - Mark validation tests
- `tests/desk_agent/` - Orchestrator + scenario tests (18 tests)
- `tests/service/` - API endpoint tests (14 tests)

---

## ⚙️ Configuration

Configure via environment variables or `.env` file:

```bash
# API Keys
FD_API_KEY=your_financial_datasets_api_key

# Service Configuration
SERVICE_ENV=dev                    # dev|stage|prod
SERVICE_PORT=8000
SERVICE_HOST=0.0.0.0
SERVICE_LOG_LEVEL=INFO             # DEBUG|INFO|WARNING|ERROR
SERVICE_LOG_FORMAT=json            # json|text

# Paths
SERVICE_SCENARIOS_PATH=scenarios
SERVICE_LOGS_PATH=logs
SERVICE_AUDIT_LOG_PATH=logs/audit.log

# Performance
SERVICE_REQUEST_TIMEOUT_S=30
SERVICE_MAX_BODY_BYTES=1000000

# Desk Agent Configuration
DESK_AGENT_MAX_RETRIES=3
DESK_AGENT_BACKOFF_MS=500
```

See **`docs/INSTALL.md`** for full configuration reference.

---

## 📖 Documentation

- **[INSTALL.md](docs/INSTALL.md)** - Installation, setup, deployment
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System design, data flow, extension points
- **[DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)** - CTO-ready demo presentation
- **[API_SERVICE.md](docs/API_SERVICE.md)** - API endpoint reference
- **Module READMEs** - In each `src/*/README.md` file

---

## 🔍 Troubleshooting

### Issue: API rate limits (429 errors)
**Solution**: Reduce scenario size or increase `DESK_AGENT_BACKOFF_MS` to 1000+

### Issue: Missing scenarios path
**Solution**: Ensure `scenarios/` exists or set `SERVICE_SCENARIOS_PATH` to correct location

### Issue: Tests failing with API errors
**Solution**: Check `.env` has valid `FD_API_KEY` or mock external calls in tests

### Issue: Service won't start
**Solution**: Check port 8000 is available or set `SERVICE_PORT` to different port

### Issue: Slow orchestrator execution
**Solution**: Enable parallel ticker execution or reduce scenario size

See **`docs/INSTALL.md#troubleshooting`** for more solutions.

---

## 🚢 Deployment

### Docker (Recommended)

```bash
# Build image
docker build -t desk-agent-service .

# Run container
docker run -p 8000:8000 \
  -e FD_API_KEY=your_key \
  -e SERVICE_ENV=prod \
  desk-agent-service
```

### Production Deployment

```bash
# Install in production environment
pip install dist/transient-*.whl

# Run with production config
export SERVICE_ENV=prod
export SERVICE_LOG_LEVEL=WARNING
export SERVICE_AUDIT_LOG_PATH=/var/log/desk-agent/audit.log

desk-agent-service
```

See **`docs/INSTALL.md#deployment`** for Kubernetes, systemd, and other options.

---

## 🛠️ Development

### Setup Development Environment

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run service in reload mode
uvicorn src.service.api:app --reload

# Run tests in watch mode
pytest-watch
```

### Adding New Agents

1. Create module in `src/your_agent/`
2. Implement agent interface with `run()` method
3. Add tests in `tests/your_agent/`
4. Integrate into `src/desk_agent/orchestrator.py`
5. Update scenarios to exercise new agent
6. Document in module README

See **`docs/ARCHITECTURE.md#extension-points`** for details.

---

## 📊 Performance

**Benchmarks** (50 positions + 20 trades):
- Manual operations team: **2-4 hours**
- Desk Agent Orchestrator: **20-30 seconds**
- **99.7% time reduction**

**Latency Targets**:
- `/health`: <100ms
- `/run-desk-agent`: <30s (configurable timeout)
- `/validate-trade`: <2s
- `/validate-pricing`: <5s

---

## 🤝 Contributing

This is a demonstration project built during the Transient.AI ramp-up program. For questions or feedback:

1. Review existing issues
2. Open new issue with clear description
3. Follow code style (Black formatter, type hints)
4. Add tests for new functionality
5. Update documentation

---

## 📄 License

Proprietary - Transient.AI

---

## 🎓 Learning Journey

This project was built in **7 weeks** as part of the Transient.AI ramp-up program:

- **Week 1**: Financial data integration (FD API)
- **Week 2**: LLM-powered ticker agent (Claude API)
- **Week 3**: Reference master normalization
- **Week 4**: OMS trade validation
- **Week 5**: Pricing agent with market data
- **Week 6**: Multi-agent orchestrator integration
- **Week 7**: Production service wrapper + demo prep

**Skills Demonstrated**:
- Financial domain expertise (hedge fund operations, trade lifecycles, pricing)
- AI engineering (LLM integration, agent design, prompt engineering)
- Python best practices (async/await, type hints, Pydantic, pytest)
- API design (FastAPI, REST, OpenAPI)
- Production systems (logging, config, error handling, monitoring)
- Documentation and client presentation

---

## 🌟 Key Differentiators

1. **AI-Augmented Validation**: LLMs assist with ambiguity resolution and context-aware checks
2. **Integrated Workflow**: Single orchestrator manages 5 specialized agents
3. **Real-Time Processing**: 30-second validation vs 2-4 hour manual process
4. **Audit-Ready**: Full execution traces, request IDs, structured logs
5. **Extensible Architecture**: Plugin new agents, configurable rules, scenario-based testing
6. **Production-Grade**: Retry logic, timeouts, error handling, comprehensive tests

---

**Built with ❤️ by Transient.AI**

For demo requests or questions: [Contact Us](https://transient.ai)
