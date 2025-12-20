# API Testing Tools & UI Options

## Built-in: FastAPI Swagger UI (Recommended)

FastAPI automatically generates interactive API documentation. **No installation needed!**

### Access

Once your service is running (`python -m src.service.main`):

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Features

✅ **Try It Out**: Click "Try it out" on any endpoint to test it interactively  
✅ **Request Builder**: Fill in request parameters with a form UI  
✅ **Response Viewer**: See formatted JSON responses  
✅ **Schema Documentation**: View request/response models  
✅ **Copy as cURL**: Generate curl commands from your requests  
✅ **Authentication**: Add headers (e.g., `X-API-Key`) if needed

### Example Workflow

1. Open http://localhost:8000/docs
2. Find `/validate-trade` endpoint
3. Click "Try it out"
4. Fill in the request body:
   ```json
   {
     "trade": {
       "ticker": "AAPL",
       "quantity": 100,
       "price": 150.0,
       "currency": "USD",
       "counterparty": "MS",
       "trade_dt": "2025-12-17",
       "settle_dt": "2025-12-19"
     },
     "verbose": true
   }
   ```
5. Click "Execute"
6. View the response with step-by-step validation details

### Advantages

- **Zero setup** - Already available
- **Always in sync** - Auto-generated from your code
- **Schema validation** - Shows required/optional fields
- **Error examples** - See what errors look like
- **No external tools** - Works in any browser

---

## Alternative Tools

### 1. Postman

**Best for**: Team collaboration, collections, environments, automated testing

**Installation**:

```bash
# macOS
brew install --cask postman

# Or download from https://www.postman.com/downloads/
```

**Features**:

- Save requests in collections
- Environment variables (dev/stage/prod)
- Pre/post request scripts
- Automated testing
- Team sharing
- API monitoring

**Setup**:

1. Import OpenAPI spec: `http://localhost:8000/openapi.json`
2. Or manually create requests
3. Set base URL: `http://localhost:8000`

**Use Case**: When you need to save/share API collections or run automated tests

---

### 2. Insomnia

**Best for**: Clean UI, GraphQL support, plugin ecosystem

**Installation**:

```bash
# macOS
brew install --cask insomnia

# Or download from https://insomnia.rest/download
```

**Features**:

- Beautiful, modern UI
- Workspace organization
- Plugin support
- Code generation (Python, JavaScript, etc.)
- Environment management

**Use Case**: When you prefer a cleaner UI or need GraphQL support

---

### 3. HTTPie Desktop

**Best for**: Command-line users who want a GUI

**Installation**:

```bash
# macOS
brew install --cask httpie

# Or download from https://httpie.io/product
```

**Features**:

- Command-line tool with GUI
- Syntax highlighting
- Request history
- Export to various formats

**Use Case**: If you're comfortable with command-line but want visual feedback

---

### 4. HTTPie CLI

**Best for**: Command-line users

**Installation**:

```bash
pip install httpie
# Or
brew install httpie
```

**Usage**:

```bash
# Simple GET
http GET localhost:8000/health

# POST with JSON
http POST localhost:8000/validate-trade \
  trade:='{"ticker":"AAPL","quantity":100,"price":150.00,"currency":"USD","counterparty":"MS","trade_dt":"2025-12-17","settle_dt":"2025-12-19"}' \
  verbose:=true

# Pretty JSON output
http GET localhost:8000/health | jq
```

**Use Case**: Quick command-line testing, scripts, CI/CD

---

### 5. VS Code REST Client Extension

**Best for**: Developers who live in VS Code

**Installation**:

1. Open VS Code
2. Extensions → Search "REST Client"
3. Install by Huachao Mao

**Usage**:
Create `api-tests.http`:

```http
### Health Check
GET http://localhost:8000/health

### Validate Trade
POST http://localhost:8000/validate-trade
Content-Type: application/json

{
  "trade": {
    "ticker": "AAPL",
    "quantity": 100,
    "price": 150.00,
    "currency": "USD",
    "counterparty": "MS",
    "trade_dt": "2025-12-17",
    "settle_dt": "2025-12-19"
  },
  "verbose": true
}

### Ticker Agent
POST http://localhost:8000/ticker-agent
Content-Type: application/json

{
  "question": "What are TSLA's fundamentals and risk trends?"
}
```

Click "Send Request" above each request.

**Use Case**: Keep API tests in your repo, version controlled

---

### 6. curl + jq (Command Line)

**Best for**: Scripts, automation, quick testing

**Installation**:

```bash
# macOS (jq)
brew install jq

# curl is pre-installed
```

**Usage**:

```bash
# Pretty JSON output
curl -X POST http://localhost:8000/validate-trade \
  -H "Content-Type: application/json" \
  -d '{
    "trade": {
      "ticker": "AAPL",
      "quantity": 100,
      "price": 150.00,
      "currency": "USD",
      "counterparty": "MS",
      "trade_dt": "2025-12-17",
      "settle_dt": "2025-12-19"
    },
    "verbose": true
  }' | jq

# Save to file
curl http://localhost:8000/health | jq > health.json
```

**Use Case**: Automation, CI/CD, quick one-off tests

---

## Recommendation

### For Quick Testing & Development

**Use FastAPI Swagger UI** (`/docs`) - It's already there, always up-to-date, and requires no setup.

### For Team Collaboration

**Use Postman** - Share collections, environments, and run automated tests.

### For Version-Controlled Tests

**Use VS Code REST Client** - Keep `.http` files in your repo alongside your code.

### For Automation/Scripts

**Use HTTPie CLI or curl** - Perfect for CI/CD and shell scripts.

---

## Quick Start: Swagger UI

1. **Start your service**:

   ```bash
   python -m src.service.main
   ```

2. **Open browser**:

   ```
   http://localhost:8000/docs
   ```

3. **Test an endpoint**:

   - Expand `/validate-trade`
   - Click "Try it out"
   - Fill in the request body
   - Click "Execute"
   - View the response

4. **Copy as cURL**:
   - After executing, click "Copy" to get the curl command

That's it! No installation, no setup, just open and test.

---

## Example: Testing Verbose Trade Validation

1. Open http://localhost:8000/docs
2. Find `POST /validate-trade`
3. Click "Try it out"
4. Paste this in the request body:
   ```json
   {
     "trade": {
       "ticker": "AAPL",
       "quantity": 100,
       "price": 150.0,
       "currency": "USD",
       "counterparty": "MS",
       "trade_dt": "2025-12-17",
       "settle_dt": "2025-12-19"
     },
     "verbose": true
   }
   ```
5. Click "Execute"
6. Scroll down to see the `verbose.steps` array with detailed validation results

---

## Tips

- **Swagger UI** auto-updates when you change your API code (if using `--reload`)
- **Postman** can import your OpenAPI spec for all endpoints at once
- **VS Code REST Client** files can be committed to git for team sharing
- **HTTPie** has better JSON formatting than curl by default
- Use **jq** with curl for pretty-printing: `curl ... | jq`

---

## Security Note

⚠️ **Production**: Disable Swagger UI in production or restrict access:

```python
# In production, you might want to disable docs
app = FastAPI(docs_url=None, redoc_url=None)
```

Or use authentication middleware to protect `/docs`.
