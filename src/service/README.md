# Service Module

![Status](https://img.shields.io/badge/status-production-green) ![Python](https://img.shields.io/badge/python-3.11+-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-teal)

**For API usage, endpoints, and configuration, see [docs/README.md](../../docs/README.md)**

FastAPI-based HTTP service that wraps the Desk Agent orchestrator and provides RESTful endpoints for trade validation, pricing validation, and scenario execution.

## Overview

The service module provides a production-ready HTTP API layer on top of the trading desk system. It exposes the desk agent orchestrator, OMS agent, and pricing agent through well-defined REST endpoints with comprehensive logging, monitoring, and error handling.

**Key Implementation Features:**
- FastAPI web framework with automatic OpenAPI documentation
- Request ID tracking for distributed tracing
- Structured logging (JSON or text format)
- CORS support and custom middleware
- Pydantic request/response validation
- Custom exception handlers

**For API documentation**: See [docs/README.md](../README.md)
**For testing tools**: See [docs/API_TESTING_TOOLS.md](../API_TESTING_TOOLS.md)

---

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

---

## Error Handling Implementation

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

Error handlers are registered in `api.py` using FastAPI's exception handler decorators.

---

## Logging & Monitoring Implementation

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

**Implementation**: Logging is configured in `api.py` using Python's `logging` module with custom formatters.

---

## Middleware

### Request ID Middleware

Every request gets a unique ID for distributed tracing:
- Auto-generated if not provided
- Can be passed via `X-Request-ID` header
- Returned in response headers
- Included in all logs and error responses

**Implementation location**: `api.py` middleware stack

### Payload Size Validation

Requests exceeding `max_body_bytes` (default 1MB) are rejected with HTTP 413:
```json
{
  "error": "payload too large"
}
```

**Implementation**: Custom middleware in `api.py` that reads the request body stream.

### CORS Middleware

CORS is enabled with permissive defaults:
- All origins allowed (`*`)
- All methods allowed
- Credentials supported

**Production Note:** Tighten CORS configuration for production deployments by modifying `api.py:90-96`.

**Implementation**: Using FastAPI's `CORSMiddleware` from `fastapi.middleware.cors`.

---

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

---

## Dependencies

The service integrates with:
- **DeskAgentOrchestrator** (`src.desk_agent.orchestrator`): Main workflow orchestrator
- **OMSAgent** (`src.oms`): Trade validation
- **PricingAgent** (`src.pricing`): Pricing validation

These dependencies are instantiated via factory functions (`_get_orchestrator`, `_get_oms`, `_get_pricing`) which can be mocked for testing.

**Factory Pattern**: Factory functions in `api.py` allow for dependency injection during tests without requiring full agent initialization.

---

## Performance

### Optimizations

- **Scenario Caching**: Loaded scenarios are cached via `@lru_cache` (maxsize=32)
- **Async Execution**: Scenario execution runs in thread pool to avoid blocking
- **Timeout Protection**: Requests timeout after configured duration (default 30s)

**Implementation notes**:
- Caching is implemented using `functools.lru_cache` decorator on scenario loading functions
- Async execution uses `asyncio.to_thread()` for CPU-bound operations
- Timeout uses `asyncio.wait_for()` wrapper

### Monitoring Recommendations

- Track request duration metrics (slow request threshold: 2s)
- Monitor scenario cache hit rate
- Alert on elevated error rates (500, 503 status codes)
- Track timeout occurrences

---

## Code Organization

### Endpoint Handlers

All endpoint handlers follow this pattern:
1. Request validation (Pydantic model)
2. Factory function to get agent instance
3. Agent execution with timeout
4. Response formatting
5. Error handling with appropriate HTTP status

**Example**:
```python
@app.post("/validate-trade")
async def validate_trade(payload: ValidateTradeRequest):
    oms = _get_oms()
    result = await asyncio.wait_for(
        asyncio.to_thread(oms.run, payload.trade.dict()),
        timeout=REQUEST_TIMEOUT
    )
    return result
```

### Configuration Loading

Configuration precedence (highest to lowest):
1. Environment variables
2. YAML configuration file
3. Default values in `config.py`

**Implementation**: `config.py` uses a layered approach, loading defaults, then YAML, then applying env var overrides.

---

## Related Documentation

- **[API Documentation](../../docs/README.md)** - Complete endpoint reference, configuration, deployment
- **[Testing Tools](../../docs/API_TESTING_TOOLS.md)** - How to test the API
- **[Desk Agent Orchestrator](../desk_agent/README.md)** - Core orchestration engine
- **[OMS Agent](../oms/README.md)** - Trade validation logic
- **[Pricing Agent](../pricing/README.md)** - Pricing validation and enrichment
- **[Architecture Overview](../../docs/ARCHITECTURE.md)** - System architecture
