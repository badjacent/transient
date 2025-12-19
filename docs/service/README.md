# Service Module

FastAPI-based HTTP service that wraps the Desk Agent orchestrator and provides RESTful endpoints for trade validation, pricing validation, and scenario execution.

## Overview

The service module provides a production-ready HTTP API layer on top of the trading desk system. It exposes the desk agent orchestrator, OMS agent, and pricing agent through well-defined REST endpoints with comprehensive logging, monitoring, and error handling.

**Key Features:**
- FastAPI web framework with automatic OpenAPI documentation
- Scenario execution (file-based or inline)
- Trade and pricing validation endpoints
- Request ID tracking for distributed tracing
- Configurable timeouts and request size limits
- Structured logging (JSON or text format)
- Audit logging and performance metrics
- CORS support for cross-origin requests
- Health checks and status endpoints

## Architecture

```
src/service/
├── api.py           # FastAPI app, endpoints, middleware, error handlers
├── config.py        # Configuration loading from YAML/env
├── main.py          # Service entry point (uvicorn launcher)
└── __init__.py
```

### Components

**api.py** (`/Users/localmini/github/transient/src/service/api.py`)
- FastAPI application instance
- HTTP middleware for request tracking and payload validation
- REST endpoint handlers
- Custom error classes and exception handlers
- Logging and metrics collection
- Factory functions for agent instances

**config.py** (`/Users/localmini/github/transient/src/service/config.py`)
- Configuration loader with defaults, YAML file, and environment overrides
- Configuration validation
- Centralized default values

**main.py** (`/Users/localmini/github/transient/src/service/main.py`)
- Service entry point
- Uvicorn server configuration

## Configuration

Configuration is loaded from three sources (in order of precedence):
1. Default values (hardcoded)
2. Optional YAML configuration file
3. Environment variables (highest priority)

### Configuration Options

| Key | Default | Env Variable | Description |
|-----|---------|--------------|-------------|
| `env` | `dev` | `SERVICE_ENV` | Environment name (dev/stage/prod) |
| `logs_path` | `logs` | `SERVICE_LOGS_PATH` | Directory for log files |
| `scenarios_path` | `scenarios` | `SERVICE_SCENARIOS_PATH` | Directory containing scenario files |
| `version` | `dev` | `SERVICE_VERSION` | Service version identifier |
| `log_level` | `INFO` | `SERVICE_LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `log_format` | `json` | `SERVICE_LOG_FORMAT` | Log format (json/text) |
| `host` | `0.0.0.0` | `SERVICE_HOST` | Server bind address |
| `port` | `8000` | `SERVICE_PORT` | Server port |
| `request_timeout_s` | `30` | `SERVICE_REQUEST_TIMEOUT_S` | Request timeout in seconds |
| `max_body_bytes` | `1000000` | `SERVICE_MAX_BODY_BYTES` | Maximum request body size (1MB default) |
| `audit_log_path` | `None` | `SERVICE_AUDIT_LOG_PATH` | Optional audit log file path |
| `feature_flags` | `{}` | - | Feature flags dictionary |

### Example Configuration

**.env file:**
```bash
SERVICE_ENV=prod
SERVICE_LOG_LEVEL=WARNING
SERVICE_PORT=8080
SERVICE_REQUEST_TIMEOUT_S=60
SERVICE_AUDIT_LOG_PATH=logs/audit.log
```

## Running the Service

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with default configuration
python -m src.service.main

# Or using uvicorn directly
uvicorn src.service.api:app --reload
```

### Production

```bash
# Set environment variables
export SERVICE_ENV=prod
export SERVICE_LOG_LEVEL=INFO
export SERVICE_PORT=8080

# Run service
python -m src.service.main
```

The service will be available at `http://localhost:8000` (or configured port).

### Interactive Documentation

Once running, access:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## API Endpoints

### Health & Status

#### `GET /health`
Comprehensive health check including dependency status and configuration.

**Response:**
```json
{
  "status": "ok",
  "version": "dev",
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

#### `GET /status`
Lightweight status check for load balancer health checks.

**Response:**
```json
{
  "status": "ok",
  "version": "dev",
  "env": "dev"
}
```

### Desk Agent Orchestration

#### `POST /run-desk-agent`
Execute a scenario through the desk agent orchestrator.

**Request Body:**
```json
{
  "scenario": "scenarios/clean_day.json",
  "config_overrides": {}
}
```

Or with inline data:
```json
{
  "data": {
    "name": "inline_scenario",
    "description": "Custom scenario",
    "trades": [],
    "marks": [],
    "questions": [],
    "metadata": {}
  }
}
```

**Response:**
Returns the orchestrator's execution report including validation results, alerts, and summaries.

**Errors:**
- `400`: Missing scenario/data
- `404`: Scenario file not found
- `503`: Request timeout
- `500`: Execution error

### Scenario Management

#### `GET /scenarios`
List available scenario files in the configured scenarios directory.

**Response:**
```json
{
  "scenarios": ["clean_day.json", "breach_scenario.yaml", "complex_trades.json"]
}
```

#### `GET /scenarios/{name}`
Retrieve the contents of a specific scenario file.

**Response:**
Returns the parsed scenario JSON/YAML content.

**Errors:**
- `404`: Scenario not found

### Validation Endpoints

#### `POST /validate-trade`
Validate a single trade through the OMS agent.

**Request:**
```json
{
  "trade": {
    "ticker": "AAPL",
    "quantity": 100,
    "price": 190.5,
    "currency": "USD",
    "counterparty": "MS",
    "trade_dt": "2024-06-05",
    "settle_dt": "2024-06-07"
  }
}
```

**Response:**
OMS validation results including validation status and any alerts.

#### `POST /validate-pricing`
Validate pricing marks through the pricing agent.

**Request:**
```json
{
  "marks": [
    {
      "ticker": "AAPL",
      "internal_mark": 190.5,
      "as_of": "2024-06-05"
    }
  ]
}
```

**Response:**
```json
{
  "enriched_marks": [...],
  "summary": {...}
}
```

## Error Handling

The service implements structured error handling with custom exception types:

### Error Types

**ServiceError** (500)
- Base error class for service-level errors
- Used for unexpected failures

**ScenarioNotFound** (404)
- Raised when a scenario file cannot be found
- Mapped from `FileNotFoundError`

**DependencyUnavailable** (503)
- Raised for timeout errors
- Used when downstream dependencies fail

### Error Response Format

All errors return JSON with consistent structure:
```json
{
  "error": "error_message",
  "detail": "detailed_information",
  "request_id": "uuid-request-id"
}
```

## Logging & Monitoring

### Request Logging

Every request is logged with:
- Request ID (auto-generated or from `X-Request-ID` header)
- Path and HTTP method
- Duration in milliseconds
- Response status code
- Request body size

**Example log entry (JSON format):**
```json
{
  "ts": "2024-06-05T10:30:45",
  "level": "INFO",
  "logger": "src.service.api",
  "msg": "request_id=abc-123 path=/run-desk-agent method=POST duration_ms=1234.56 content_length=500 status=200"
}
```

### Slow Request Detection

Requests exceeding `SLOW_THRESHOLD_MS` (2000ms) generate warning logs:
```json
{
  "level": "WARNING",
  "msg": "slow_request request_id=abc-123 path=/run-desk-agent duration_ms=3456.78"
}
```

### Audit Logging

When `audit_log_path` is configured, the service writes audit records for each request:
```json
{
  "request_id": "abc-123",
  "path": "/run-desk-agent",
  "method": "POST",
  "duration_ms": 1234.56,
  "status": 200,
  "ts": 1717581045000
}
```

### Metrics

Service metrics are written to `{logs_path}/service_metrics.log` with identical structure to audit logs, suitable for ingestion by monitoring systems.

### Log Files

- `{logs_path}/service.log`: Application logs (JSON or text format)
- `{audit_log_path}`: Audit trail (when configured)
- `{logs_path}/service_metrics.log`: Performance metrics

## Middleware

### Request ID Middleware

Every request gets a unique ID for distributed tracing:
- Auto-generated if not provided
- Can be passed via `X-Request-ID` header
- Returned in response headers
- Included in all logs and error responses

### Payload Size Validation

Requests exceeding `max_body_bytes` (default 1MB) are rejected with HTTP 413:
```json
{
  "error": "payload too large"
}
```

### CORS Middleware

CORS is enabled with permissive defaults:
- All origins allowed (`*`)
- All methods allowed
- Credentials supported

**Production Note:** Tighten CORS configuration for production deployments by modifying `api.py:90-96`.

## Testing

Comprehensive test suite at `tests/service/test_api.py` covering:
- Health and status endpoints
- Scenario execution (success and error paths)
- Trade and pricing validation
- Error handling and exception cases
- Request ID propagation
- CORS configuration
- Payload size limits
- Configuration loading

**Run tests:**
```bash
pytest tests/service/
```

**With coverage:**
```bash
pytest tests/service/ --cov=src.service --cov-report=html
```

## Dependencies

The service integrates with:
- **DeskAgentOrchestrator** (`src.desk_agent.orchestrator`): Main workflow orchestrator
- **OMSAgent** (`src.oms`): Trade validation
- **PricingAgent** (`src.pricing`): Pricing validation

These dependencies are instantiated via factory functions (`_get_orchestrator`, `_get_oms`, `_get_pricing`) which can be mocked for testing.

## Security Considerations

1. **CORS**: Default configuration is permissive; restrict origins in production
2. **Rate Limiting**: Not implemented; add via middleware if needed
3. **Authentication**: Not implemented; add auth middleware as required
4. **Input Validation**: Pydantic models validate request schemas
5. **Size Limits**: Request body size limited to prevent DoS
6. **Timeouts**: Request timeout prevents resource exhaustion

## Performance

### Optimizations

- **Scenario Caching**: Loaded scenarios are cached via `@lru_cache` (maxsize=32)
- **Async Execution**: Scenario execution runs in thread pool to avoid blocking
- **Timeout Protection**: Requests timeout after configured duration (default 30s)

### Monitoring Recommendations

- Track request duration metrics (slow request threshold: 2s)
- Monitor scenario cache hit rate
- Alert on elevated error rates (500, 503 status codes)
- Track timeout occurrences

## Example Usage

### cURL Examples

**Run scenario:**
```bash
curl -X POST http://localhost:8000/run-desk-agent \
  -H "Content-Type: application/json" \
  -H "X-Request-ID: my-trace-id-123" \
  -d '{"scenario": "scenarios/clean_day.json"}'
```

**List scenarios:**
```bash
curl http://localhost:8000/scenarios
```

**Validate trade:**
```bash
curl -X POST http://localhost:8000/validate-trade \
  -H "Content-Type: application/json" \
  -d '{
    "trade": {
      "ticker": "AAPL",
      "quantity": 100,
      "price": 190.5,
      "currency": "USD",
      "counterparty": "MS",
      "trade_dt": "2024-06-05",
      "settle_dt": "2024-06-07"
    }
  }'
```

**Health check:**
```bash
curl http://localhost:8000/health
```

### Python Client Example

```python
import requests

# Configure endpoint
base_url = "http://localhost:8000"

# Run scenario
response = requests.post(
    f"{base_url}/run-desk-agent",
    json={"scenario": "scenarios/clean_day.json"},
    headers={"X-Request-ID": "my-trace-123"}
)
report = response.json()
print(f"Status: {report['status']}")

# Validate trade
trade_response = requests.post(
    f"{base_url}/validate-trade",
    json={
        "trade": {
            "ticker": "AAPL",
            "quantity": 100,
            "price": 190.5,
            "currency": "USD",
            "counterparty": "MS",
            "trade_dt": "2024-06-05",
            "settle_dt": "2024-06-07"
        }
    }
)
result = trade_response.json()
```

## Related Documentation

- [Desk Agent Orchestrator](../desk_agent/README.md): Core orchestration engine
- [OMS Agent](../../src/oms/README.md): Trade validation logic
- [Pricing Agent](../pricing/README.md): Pricing validation and enrichment
- [Architecture Overview](../ARCHITECTURE.md): System architecture
