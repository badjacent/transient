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

**Purpose**: Validate a single trade via OMS agent (without full orchestrator)

**Request**:

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

**Response** (200 OK):

```json
{
  "status": "OK",
  "issues": [],
  "explanation": "All validation checks passed",
  "trade": {...}
}
```

**Use Cases**:

- Real-time trade validation in trading platform
- Pre-flight checks before booking
- Compliance validation

---

### POST /validate-pricing

**Purpose**: Validate pricing marks via pricing agent (without full orchestrator)

**Request**:

```bash
curl -X POST http://localhost:8000/validate-pricing \
  -H "Content-Type: application/json" \
  -d '{
    "marks": [
      {
        "ticker": "AAPL",
        "internal_mark": 150.00,
        "as_of": "2025-12-17"
      },
      {
        "ticker": "MSFT",
        "internal_mark": 370.00,
        "as_of": "2025-12-17"
      }
    ]
  }'
```

**Response** (200 OK):

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
      "OK": 2
    }
  }
}
```

**Use Cases**:

- EOD pricing review
- Risk management checks
- P&L validation

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

**Supported Intents**: See [ticker_agent documentation](ticker_agent/README.md) for full list of supported intents and question formats.

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
- **[service/API_SERVICE.md](service/API_SERVICE.md)** - Additional API examples

**Repository**: https://github.com/transient-ai/desk-agent
**Support**: support@transient.ai

---

**Maintained By**: Transient.AI Engineering
**Version**: 1.0 - Production-Ready
