# Desk Agent Service API

**For complete API documentation, see [docs/README.md](../README.md)**

## Quick Reference

The Desk Agent Service is a FastAPI-based REST API that exposes the desk agent orchestrator for hedge fund operations automation.

### Interactive Documentation

Once your service is running (`python -m src.service.main`):

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Quick Start

```bash
# Start service
python -m src.service.main

# Health check
curl http://localhost:8000/health

# Run a scenario
curl -X POST http://localhost:8000/run-desk-agent \
  -H "Content-Type: application/json" \
  -d '{"scenario": "scenarios/clean_day.json"}'

# Validate a trade
curl -X POST http://localhost:8000/validate-trade \
  -H "Content-Type: application/json" \
  -d '{
    "trade": {
      "ticker": "AAPL",
      "quantity": 100,
      "price": 190,
      "currency": "USD",
      "counterparty": "MS",
      "trade_dt": "2024-06-05",
      "settle_dt": "2024-06-07"
    }
  }'

# Normalize a ticker
curl -X POST http://localhost:8000/normalize \
  -H "Content-Type: application/json" \
  -d '{"identifier": "AAPL US", "top_k": 3}'
```

### Available Endpoints

- `GET /health` - Service health & dependency checks
- `POST /run-desk-agent` - Execute desk agent orchestrator
- `GET /scenarios` - List available scenarios
- `GET /scenarios/{name}` - Get scenario details
- `POST /validate-trade` - Validate single trade
- `POST /validate-pricing` - Validate pricing marks
- `POST /ticker-agent` - Answer ticker questions
- `POST /normalize` - Normalize ticker identifiers
- `GET /status` - Lightweight status check
- `GET /config` - Service configuration
- `GET /desk-agent/config` - Desk agent configuration
- `GET /run-desk-agent/verbose` - Execution structure info
- `GET /endpoints` - List all endpoints

### Documentation Resources

- **[API Documentation](../README.md)** - Complete endpoint reference, examples, configuration
- **[Testing Tools](../API_TESTING_TOOLS.md)** - How to test the API (Swagger, Postman, etc.)
- **[Service Module](README.md)** - Service architecture and implementation details
- **[System Architecture](../ARCHITECTURE.md)** - Overall system design
