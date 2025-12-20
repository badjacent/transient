# Desk Agent Service - API Documentation

**Version**: 1.0.0
**Status**: Production-Ready
**Protocol**: REST/HTTP
**Format**: JSON

---

## Overview

The Desk Agent Service is a FastAPI-based REST API that exposes the multi-agent desk orchestrator for hedge fund operations automation. It provides production-grade endpoints for trade validation, pricing checks, scenario execution, and operational workflow management.

**Key Features**:

- **RESTful API**: 7 endpoints for complete workflow coverage
- **OpenAPI Documentation**: Interactive docs at `/docs`
- **Request/Response Validation**: Pydantic schemas
- **Structured Logging**: JSON logs with request IDs
- **Error Handling**: HTTP status codes with detailed messages
- **Timeout Protection**: Configurable per-endpoint timeouts
- **Audit Trail**: Optional request/response logging

---

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
  - [GET /health](#get-health)
  - [POST /run-desk-agent](#post-run-desk-agent)
  - [GET /scenarios](#get-scenarios)
  - [GET /scenarios/{name}](#get-scenariosname)
  - [POST /validate-trade](#post-validate-trade)
  - [POST /validate-pricing](#post-validate-pricing)
  - [POST /ticker-agent](#post-ticker-agent)
  - [POST /normalize](#post-normalize)
  - [GET /status](#get-status)
  - [GET /config](#get-config)
  - [GET /desk-agent/config](#get-desk-agentconfig)
  - [GET /run-desk-agent/verbose](#get-run-desk-agentverbose)
  - [GET /endpoints](#get-endpoints)
- [Error Handling](#error-handling)
- [Configuration](#configuration)
- [Performance Characteristics](#performance-characteristics)
- [Monitoring & Logging](#monitoring--logging)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)
- [OpenAPI Documentation](#openapi-documentation)
- [Security Considerations](#security-considerations)
- [Additional Resources](#additional-resources)

---

## Quick Start

### 1. Installation

```bash
# Clone and install
git clone https://github.com/transient-ai/desk-agent.git
cd desk-agent
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env and add FD_API_KEY
```

### 2. Start Service

```bash
# Default: http://0.0.0.0:8000
python -m src.service.main

# Or use entry point
desk-agent-service

# Or with uvicorn directly
uvicorn src.service.api:app --reload --port 8000
```

### 3. Verify Health

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "env": "dev",
  "dependencies": {
    "refmaster": "stub",
    "oms": "stub",
    "pricing": "stub",
    "ticker_agent": "stub",
    "scenarios_path": "scenarios",
    "scenarios_path_exists": true
  }
}
```

[↑ Back to Top](#table-of-contents)

---

## API Endpoints

### GET /health

**Purpose**: Service health check and dependency status

**Request**:

```bash
curl http://localhost:8000/health
```

**Response** (200 OK):

```json
{
  "status": "ok",
  "version": "1.0.0",
  "env": "dev",
  "dependencies": {
    "refmaster": "stub",
    "oms": "stub",
    "pricing": "stub",
    "ticker_agent": "stub",
    "scenarios_path": "scenarios",
    "scenarios_path_exists": true
  }
}
```

**Use Cases**:

- Kubernetes liveness/readiness probes
- Load balancer health checks
- Deployment verification
- Monitoring/alerting

---

### POST /run-desk-agent

**Purpose**: Execute desk agent orchestrator for a scenario

**Request Schema**:

```json
{
  "scenario": "scenarios/clean_day.json",  // OR
  "data": {...},                          // Inline scenario JSON
  "config_overrides": {                   // Optional
    "max_retries": 5
  }
}
```

**Example 1** - Run named scenario:

```bash
curl -X POST http://localhost:8000/run-desk-agent \
  -H "Content-Type: application/json" \
  -d '{
    "scenario": "scenarios/clean_day.json"
  }'
```

**Example 2** - Run inline scenario:

```bash
curl -X POST http://localhost:8000/run-desk-agent \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "name": "adhoc_check",
      "trades": [{
        "trade_id": "T001",
        "ticker": "AAPL",
        "quantity": 100,
        "price": 150.00,
        "currency": "USD",
        "counterparty": "MS",
        "trade_dt": "2025-12-17",
        "settle_dt": "2025-12-19"
      }],
      "marks": [],
      "questions": [],
      "metadata": {}
    }
  }'
```

**Response** (200 OK):

```json
{
  "scenario": {
    "name": "clean_day",
    "description": "Happy path scenario..."
  },
  "data_quality": {
    "ticker_normalizations": [...],
    "normalization_issues": []
  },
  "trade_issues": [],
  "pricing_flags": [],
  "market_context": {...},
  "ticker_agent_results": [...],
  "narrative": "Processed 4 trades and 7 marks...",
  "summary": {
    "overall_status": "OK",
    "total_trades": 4,
    "trades_with_issues": 0,
    "percent_trades_with_issues": 0.0,
    "total_marks": 7,
    "marks_flagged": 0,
    "percent_marks_flagged": 0.0,
    "execution_time_ms": 4523
  },
  "execution_metadata": {
    "execution_time_ms": 4523,
    "timestamp": 1703001234567,
    "trace": [...]
  }
}
```

**Error Responses**:

- **400**: Missing scenario/data, invalid JSON
- **404**: Scenario file not found
- **503**: Request timeout (default: 30s)
- **500**: Internal error (agent failure)

---

### GET /scenarios

**Purpose**: List available scenario files

**Request**:

```bash
curl http://localhost:8000/scenarios
```

**Response** (200 OK):

```json
{
  "scenarios": [
    "clean_day.json",
    "bad_mark.json",
    "mis_booked_trade.json",
    "wrong_ticker_mapping.json",
    "high_vol_day.json"
  ]
}
```

**Error Responses**:

- **404**: Scenarios directory not found

---

### GET /scenarios/{name}

**Purpose**: Get scenario file contents

**Request**:

```bash
curl http://localhost:8000/scenarios/clean_day.json
```

**Response** (200 OK):

```json
{
  "name": "clean_day",
  "description": "Happy path scenario...",
  "trades": [...],
  "marks": [...],
  "questions": [...],
  "metadata": {...}
}
```

**Error Responses**:

- **404**: Scenario not found
- **500**: Invalid JSON in scenario file

---

### POST /validate-trade

**Purpose**: Validate a single trade via OMS agent (without full orchestrator). Supports interactive verbose mode for step-by-step validation details.

**Request** (Standard):

```bash
curl -X POST http://localhost:8000/validate-trade \
  -H "Content-Type: application/json" \
  -d '{
    "trade": {
      "trade_id": "T001",
      "ticker": "AAPL",
      "quantity": 100,
      "price": 150.00,
      "currency": "USD",
      "counterparty": "MS",
      "trade_dt": "2025-12-17",
      "settle_dt": "2025-12-19"
    }
  }'
```

**Request** (Verbose/Interactive Mode):

```bash
curl -X POST http://localhost:8000/validate-trade \
  -H "Content-Type: application/json" \
  -d '{
    "trade": {
      "trade_id": "T001",
      "ticker": "AAPL",
      "quantity": 100,
      "price": 150.00,
      "currency": "USD",
      "counterparty": "MS",
      "trade_dt": "2025-12-17",
      "settle_dt": "2025-12-19"
    },
    "verbose": true
  }'
```

**Response** (200 OK, Standard):

```json
{
  "status": "OK",
  "issues": [],
  "explanation": "All checks passed.",
  "metrics": {
    "total_ms": 245.3,
    "identifier_ms": 12.5,
    "price_ms": 180.2
  }
}
```

**Response** (200 OK, Verbose Mode):

```json
{
  "status": "OK",
  "issues": [],
  "explanation": "All checks passed.",
  "metrics": {...},
  "verbose": {
    "steps": [
      {
        "step": "required_fields",
        "description": "Check all required fields are present",
        "status": "ok",
        "checked_fields": ["ticker", "quantity", "price", ...]
      },
      {
        "step": "identifier_normalization",
        "description": "Normalize ticker identifier via refmaster",
        "status": "ok",
        "input_ticker": "AAPL",
        "normalization_results": [
          {
            "symbol": "AAPL",
            "confidence": 0.92,
            "ambiguous": false,
            "reasons": ["symbol_exact", "country_match"]
          }
        ]
      },
      {
        "step": "price_validation",
        "description": "Validate trade price against market data",
        "status": "ok",
        "trade_price": 150.00,
        "market_data": {
          "market_price": 151.50,
          "as_of_date": "2025-12-17",
          "source": "financialdatasets.ai"
        },
        "thresholds": {
          "warning_pct": 2.0,
          "error_pct": 5.0
        }
      },
      {
        "step": "settlement_validation",
        "description": "Validate settlement date rules",
        "status": "ok",
        "settlement_days": 2,
        "expected_settlement_days": 2,
        "is_weekend": false
      }
    ]
  }
}
```

**Verbose Mode Features**:

- **Step-by-step validation**: See each check performed (required fields, schema, identifier, currency, price, counterparty, settlement)
- **Intermediate data**: View normalization results, market price fetched, thresholds used
- **Detailed context**: See what was checked vs what was found for each validation step
- **Interactive debugging**: Understand why a trade passed or failed each check

**Use Cases**:

- Real-time trade validation in trading platform
- Pre-flight checks before booking
- Compliance validation
- **Interactive debugging**: Understand validation failures step-by-step
- **Training/Education**: Learn how OMS validation works
- **Integration testing**: Verify each validation step behaves correctly

---

### POST /validate-pricing

**Purpose**: Validate pricing marks via pricing agent (without full orchestrator). Supports interactive verbose mode for step-by-step validation details.

**Request** (Standard):

```bash
curl -X POST http://localhost:8000/validate-pricing \
  -H "Content-Type: application/json" \
  -d '{
    "marks": [
      {
        "ticker": "AAPL",
        "internal_mark": 150.00,
        "as_of_date": "2025-12-17"
      },
      {
        "ticker": "MSFT",
        "internal_mark": 370.00,
        "as_of_date": "2025-12-17"
      }
    ]
  }'
```

**Request** (Verbose/Interactive Mode):

```bash
curl -X POST http://localhost:8000/validate-pricing \
  -H "Content-Type: application/json" \
  -d '{
    "marks": [
      {
        "ticker": "AAPL",
        "internal_mark": 150.00,
        "as_of_date": "2025-12-17"
      }
    ],
    "verbose": true
  }'
```

**Response** (200 OK, Standard):

```json
{
  "enriched_marks": [
    {
      "ticker": "AAPL",
      "internal_mark": 150.0,
      "market_price": 151.5,
      "classification": "OK",
      "deviation_percentage": 1.0,
      "explanation": "Mark within tolerance"
    }
  ],
  "summary": {
    "counts": {
      "OK": 1
    },
    "duration_ms": 245.3,
    "within_budget": true
  }
}
```

**Response** (200 OK, Verbose Mode):

```json
{
  "enriched_marks": [...],
  "summary": {...},
  "verbose": {
    "steps": [
      {
        "step": "load_marks",
        "description": "Load and parse mark records",
        "status": "ok",
        "total_marks": 1,
        "parsed_successfully": 1
      },
      {
        "step": "ticker_normalization",
        "description": "Normalize ticker identifiers via refmaster",
        "normalizations": [
          {
            "ticker": "AAPL",
            "normalization_results": [
              {
                "symbol": "AAPL",
                "confidence": 0.92,
                "ambiguous": false
              }
            ]
          }
        ]
      },
      {
        "step": "market_data_enrichment",
        "description": "Fetch market prices and calculate deviations",
        "enrichments": [
          {
            "ticker": "AAPL",
            "internal_mark": 150.00,
            "market_data": {
              "market_price": 151.50,
              "as_of_date": "2025-12-17",
              "source": "financialdatasets.ai"
            },
            "deviation_percentage": 0.99,
            "classification": "OK",
            "is_stale": false,
            "thresholds": {
              "ok_threshold_pct": 2.0,
              "review_threshold_pct": 5.0,
              "stale_days": 2
            }
          }
        ]
      },
      {
        "step": "classification_summary",
        "description": "Aggregate classification counts",
        "classifications": {
          "OK": 1
        },
        "total_marks": 1
      }
    ]
  }
}
```

**Verbose Mode Features**:

- **Step-by-step validation**: See each check performed (load marks, ticker normalization, market data enrichment, classification)
- **Intermediate data**: View normalization results, market prices fetched, deviation calculations
- **Detailed context**: See thresholds used, stale mark detection, classification logic
- **Interactive debugging**: Understand why marks are classified as OK, REVIEW_NEEDED, OUT_OF_TOLERANCE, STALE_MARK, or NO_MARKET_DATA

**Use Cases**:

- EOD pricing review
- Risk management checks
- P&L validation
- **Interactive debugging**: Understand pricing validation failures step-by-step
- **Training/Education**: Learn how pricing validation works
- **Integration testing**: Verify each validation step behaves correctly

---

### POST /ticker-agent

**Purpose**: Answer a question about a ticker using the ticker agent (without full orchestrator)

**Request**:

```bash
curl -X POST http://localhost:8000/ticker-agent \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are TSLA'\''s fundamentals and risk trends?"
  }'
```

**Response** (200 OK):

```json
{
  "intent": "fundamentals_risk_summary",
  "summary": "TSLA fundamentals and risk analysis ($477.57, Consumer Discretionary): Revenue: 97,690,000,000 USD (most recent), +81.5% change over 4 periods. Net income: 7,091,000,000 USD (most recent). Risk Assessment: Liquidity: Current ratio 1.85 (strong) (improving trend); Leverage: Debt-to-equity 0.12 (low) (stable trend); Free cash flow: 7,558,000,000 USD (positive) (improving trend).",
  "metrics": {
    "ticker": "TSLA",
    "as_of": "2025-12-15",
    "price": 477.57,
    "market_cap": 758000000000,
    "sector": "Consumer Discretionary",
    "industry": "Auto Manufacturers",
    "income_statements": [...],
    "balance_sheets": [...],
    "cash_flow_statements": [...]
  },
  "source": "financialdatasets.ai",
  "system_prompt": "...",
  "tools_prompt": "..."
}
```

**Use Cases**:

- Quick ticker Q&A without running full orchestrator
- Fundamentals and risk analysis
- Performance summaries
- Income statement queries

**Supported Intents**: See [ticker_agent documentation](../src/ticker_agent/README.md) for full list of supported intents and question formats.

---

### POST /normalize

**Purpose**: Normalize a ticker identifier to canonical equity records with confidence scores and ambiguity flags

**Request**:

```bash
curl -X POST http://localhost:8000/normalize \
  -H "Content-Type: application/json" \
  -d '{
    "identifier": "AAPL US",
    "top_k": 3
  }'
```

**Response** (200 OK):

```json
{
  "identifier": "AAPL US",
  "count": 1,
  "results": [
    {
      "equity": {
        "symbol": "AAPL",
        "isin": "US0378331005",
        "cusip": "037833100",
        "cik": "0000320193",
        "currency": "USD",
        "exchange": "NASDAQ",
        "pricing_source": "llm"
      },
      "confidence": 0.92,
      "reasons": ["symbol_exact", "country_match"],
      "ambiguous": false
    }
  ]
}
```

**Request Parameters**:

- `identifier` (required): Ticker identifier to normalize. Supports:
  - Ticker with country: `"AAPL US"`
  - Ticker with exchange suffix: `"AAPL.OQ"`
  - ISIN: `"US0378331005"`
  - CUSIP: `"037833100"`
  - CIK: `"0000320193"`
  - Company name with exchange: `"Apple Inc NASDAQ"`
- `top_k` (optional, default=5): Maximum number of results to return (1-20)

**Response Fields**:

- `identifier`: The input identifier
- `count`: Number of results returned
- `results`: Array of normalization results, each containing:
  - `equity`: Canonical equity record (symbol, ISIN, CUSIP, CIK, exchange, etc.)
  - `confidence`: Match confidence score (0.0-1.0)
  - `reasons`: List of match reasons (e.g., `["symbol_exact", "country_match"]`)
  - `ambiguous`: Boolean flag indicating if the match is ambiguous

**Use Cases**:

- Normalize ticker identifiers from various sources
- Resolve ambiguous ticker mappings
- Get canonical equity records for downstream processing
- Validate ticker identifiers before trade processing

**Ambiguity Handling**: When `ambiguous: true`, multiple candidates have similar confidence scores. Downstream systems should warn users. See [refmaster ambiguity documentation](refmaster/AMBIGUITY_DEMO.md) for details.

**Example: Ambiguous Match**:

```bash
curl -X POST http://localhost:8000/normalize \
  -H "Content-Type: application/json" \
  -d '{"identifier": "ABC", "top_k": 3}'
```

Response may include multiple results with `ambiguous: true` if "ABC" matches both "ABC" and "ABCD" equities.

---

### GET /status

**Purpose**: Service status (minimal health check)

**Request**:

```bash
curl http://localhost:8000/status
```

**Response** (200 OK):

```json
{
  "status": "ok",
  "version": "1.0.0",
  "env": "dev"
}
```

---

### GET /config

**Purpose**: Return current service configuration (sanitized, no secrets)

**Request**:

```bash
curl http://localhost:8000/config
```

**Response** (200 OK):

```json
{
  "env": "dev",
  "version": "1.0.0",
  "host": "0.0.0.0",
  "port": 8000,
  "log_level": "INFO",
  "log_format": "json",
  "request_timeout_s": 30,
  "max_body_bytes": 1000000,
  "scenarios_path": "scenarios",
  "logs_path": "logs",
  "audit_log_path": null,
  "feature_flags": {}
}
```

**Use Cases**:

- Verify configuration without accessing config files
- Debug configuration issues
- Understand service settings

---

### GET /desk-agent/config

**Purpose**: Return desk agent orchestrator configuration

**Request**:

```bash
curl http://localhost:8000/desk-agent/config
```

**Response** (200 OK):

```json
{
  "scenarios_path": "scenarios",
  "logs_path": "logs",
  "log_level": "INFO",
  "retry_config": {
    "max_retries": 2,
    "backoff_ms": 500,
    "abort_after_retry": false
  },
  "parallel_ticker": false,
  "performance_budget_ms": 30000,
  "refmaster_data_path": null,
  "oms_config": {
    "price_warning_threshold": null,
    "price_error_threshold": null,
    "settlement_days": null
  },
  "pricing_config": {
    "stale_days": null
  }
}
```

**Use Cases**:

- Understand desk agent retry behavior
- Verify performance budgets
- Check parallel execution settings

---

### GET /run-desk-agent/verbose

**Purpose**: Return detailed information about desk agent execution structure

**Request**:

```bash
curl http://localhost:8000/run-desk-agent/verbose
```

**Response** (200 OK):

```json
{
  "execution_steps": [
    {
      "step": "normalize",
      "description": "Normalize ticker identifiers via refmaster",
      "agent": "refmaster",
      "inputs": ["trades", "marks", "questions"],
      "outputs": ["ticker_normalizations", "normalization_issues"]
    },
    ...
  ],
  "report_structure": {
    "scenario": "Scenario metadata",
    "data_quality": "Ticker normalization results",
    "trade_issues": "Trade validation results",
    "pricing_flags": "Pricing validation results",
    "market_context": "Market snapshots and sector aggregation",
    "ticker_agent_results": "Q&A responses",
    "narrative": "Human-readable summary",
    "summary": "Aggregated statistics",
    "execution_metadata": {
      "execution_time_ms": "Total execution time",
      "timestamp": "Execution timestamp",
      "agents_executed": "List of agents that ran",
      "trace": "Step-by-step execution trace",
      "config": "Configuration used",
      "errors": "List of errors encountered"
    }
  },
  "configuration": {
    "retry_max": 2,
    "retry_backoff_ms": 500,
    "parallel_ticker": false
  }
}
```

**Use Cases**:

- Understand desk agent workflow
- Learn report structure before running scenarios
- Debug execution flow

---

### GET /endpoints

**Purpose**: List all available API endpoints with descriptions

**Request**:

```bash
curl http://localhost:8000/endpoints
```

**Response** (200 OK):

```json
{
  "endpoints": [
    {
      "path": "/config",
      "methods": ["GET"],
      "name": "get_config",
      "summary": "Return current service configuration (sanitized, no secrets)."
    },
    ...
  ],
  "total": 14
}
```

**Use Cases**:

- Discover available endpoints
- Understand API surface
- API documentation generation

[↑ Back to Top](#table-of-contents)

---

## Error Handling

### HTTP Status Codes

| Code | Meaning               | Example                              |
| ---- | --------------------- | ------------------------------------ |
| 200  | Success               | Request completed successfully       |
| 400  | Bad Request           | Missing required field, invalid JSON |
| 404  | Not Found             | Scenario file not found              |
| 413  | Payload Too Large     | Request body > 1MB                   |
| 500  | Internal Server Error | Agent failure, unexpected exception  |
| 503  | Service Unavailable   | Timeout, external dependency down    |

### Error Response Format

```json
{
  "error": "scenario_not_found",
  "detail": "Scenario file 'missing.json' not found",
  "request_id": "a1b2c3d4-..."
}
```

**Error Fields**:

- `error`: Machine-readable error type
- `detail`: Human-readable explanation
- `request_id`: Correlation ID for debugging (also in `X-Request-ID` header)

---

## Configuration

### Environment Variables

```bash
# Service
SERVICE_ENV=dev                    # dev|stage|prod
SERVICE_VERSION=1.0.0
SERVICE_HOST=0.0.0.0
SERVICE_PORT=8000
SERVICE_LOG_LEVEL=INFO             # DEBUG|INFO|WARNING|ERROR
SERVICE_LOG_FORMAT=json            # json|text

# Paths
SERVICE_SCENARIOS_PATH=scenarios
SERVICE_LOGS_PATH=logs
SERVICE_AUDIT_LOG_PATH=logs/audit.log

# Performance
SERVICE_REQUEST_TIMEOUT_S=30
SERVICE_MAX_BODY_BYTES=1000000

# API Keys (required for market data)
FD_API_KEY=your_financial_datasets_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key  # For ticker agent
```

### YAML Config (Optional)

Create `config/service.yaml`:

```yaml
env: prod
version: 1.0.0
log_level: WARNING
request_timeout_s: 60
scenarios_path: /opt/scenarios
```

**Precedence**: Defaults → YAML → Env Vars (highest)

---

## Performance Characteristics

### Latency Targets

| Endpoint               | Target | Typical    |
| ---------------------- | ------ | ---------- |
| GET /health            | <100ms | 10-50ms    |
| GET /status            | <100ms | 10-50ms    |
| GET /scenarios         | <200ms | 50-150ms   |
| GET /scenarios/{name}  | <500ms | 100-300ms  |
| POST /validate-trade   | <2s    | 500ms-1.5s |
| POST /validate-pricing | <5s    | 1-3s       |
| POST /ticker-agent     | <5s    | 1-3s       |
| POST /normalize        | <500ms | 50-200ms   |
| POST /run-desk-agent   | <30s   | 5-25s      |

**Factors Affecting Latency**:

- Scenario size (trades + marks count)
- External API availability (FD, Claude)
- Network latency
- Cold start (first request)

### Throughput

- **Concurrent Requests**: 10-50 (depends on external API rate limits)
- **Requests per Second**: 5-20 (with typical scenarios)
- **Max Payload Size**: 1MB (configurable)

---

## Monitoring & Logging

### Structured Logs

All requests logged in JSON format:

```json
{
  "ts": "2025-12-18T10:30:45.123Z",
  "level": "INFO",
  "logger": "src.service.api",
  "msg": "request_id=a1b2c3d4 path=/run-desk-agent method=POST duration_ms=4523 status=200"
}
```

**Log Locations**:

- Console: stdout (always)
- File: `logs/service.log` (configurable)
- Audit: `logs/audit.log` (if `SERVICE_AUDIT_LOG_PATH` set)

### Request ID Propagation

Every request gets a unique ID:

- Auto-generated if not provided
- Returned in `X-Request-ID` header
- Logged in all operations
- Included in error responses

**Usage**:

```bash
# Provide custom request ID
curl -H "X-Request-ID: my-trace-123" \
  http://localhost:8000/health

# Response includes it back
# X-Request-ID: my-trace-123
```

### Slow Request Warnings

Requests exceeding 2000ms trigger warnings:

```json
{
  "level": "WARNING",
  "msg": "slow_request request_id=a1b2c3d4 path=/run-desk-agent duration_ms=4523"
}
```

[↑ Back to Top](#table-of-contents)

---

## Deployment

### Local Development

```bash
# With auto-reload
uvicorn src.service.api:app --reload --port 8000

# Or via entry point
desk-agent-service
```

### Docker

```bash
# Build
docker build -t desk-agent-service .

# Run
docker run -p 8000:8000 \
  -e FD_API_KEY=xxx \
  -e SERVICE_ENV=prod \
  desk-agent-service
```

### Production (systemd)

Create `/etc/systemd/system/desk-agent.service`:

```ini
[Unit]
Description=Desk Agent Service
After=network.target

[Service]
Type=simple
User=desk-agent
WorkingDirectory=/opt/desk-agent
Environment=SERVICE_ENV=prod
Environment=SERVICE_PORT=8000
EnvironmentFile=/opt/desk-agent/.env
ExecStart=/opt/desk-agent/.venv/bin/desk-agent-service
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable desk-agent
sudo systemctl start desk-agent
sudo systemctl status desk-agent
```

---

## Troubleshooting

### Issue: Service won't start

**Symptoms**: `Address already in use` or `Permission denied`

**Solutions**:

1. Check if port 8000 is in use: `lsof -i :8000`
2. Change port: `export SERVICE_PORT=8080`
3. Check file permissions on `logs/` directory

---

### Issue: Scenario not found (404)

**Symptoms**: `GET /scenarios` returns empty list

**Solutions**:

1. Verify `scenarios/` directory exists
2. Check `SERVICE_SCENARIOS_PATH` environment variable
3. Ensure scenario files are `.json` or `.yaml` format

---

### Issue: Slow responses or timeouts

**Symptoms**: Requests taking >30s, 503 errors

**Solutions**:

1. Increase timeout: `export SERVICE_REQUEST_TIMEOUT_S=60`
2. Reduce scenario size (fewer trades/marks)
3. Check external API availability (FD_API_KEY valid?)
4. Enable parallel ticker execution in orchestrator

---

### Issue: Missing market data errors

**Symptoms**: `NO_MARKET_DATA` classifications

**Solutions**:

1. Verify `FD_API_KEY` is set and valid
2. Check ticker symbols are correct
3. Check FD API rate limits (60 req/min)
4. Try again with backoff

---

### Issue: High memory usage

**Symptoms**: Service using >500MB RAM

**Solutions**:

1. Clear scenario cache (restart service)
2. Reduce concurrent requests
3. Optimize scenario file sizes
4. Consider horizontal scaling

---

## OpenAPI Documentation

Interactive API documentation available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

**Features**:

- Try out endpoints interactively
- View request/response schemas
- Copy curl commands
- See error code descriptions

**Quick Start**: Just open http://localhost:8000/docs in your browser - no installation needed! Click "Try it out" on any endpoint to test it.

For more testing tools and options, see **[API_TESTING_TOOLS.md](API_TESTING_TOOLS.md)**.

---

## Security Considerations

### Input Validation

- Pydantic schemas enforce type safety
- Max payload size: 1MB
- Request timeout: 30s

### Data Protection

- Sensitive fields redacted in logs
- No PII logged
- TLS/HTTPS recommended for production

### CORS Configuration

- Default: Allow all origins (development)
- Production: Configure `CORS_ORIGINS` to specific domains

### Authentication

- Optional API key via `X-API-Key` header
- OAuth2/JWT support for enterprise deployments

---

## Additional Resources

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design & technical details
- **[DEMO_SCRIPT.md](DEMO_SCRIPT.md)** - CTO-ready demo presentation
- **[INSTALL.md](INSTALL.md)** - Installation & deployment guide
- **[service/API_SERVICE.md](../src/service/API_SERVICE.md)** - Additional API examples

**Repository**: https://github.com/transient-ai/desk-agent
**Support**: support@transient.ai

---

**Maintained By**: Transient.AI Engineering
**Version**: 1.0 - Production-Ready
