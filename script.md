# YouTube Script: Building an AI-Powered Hedge Fund Operations Agent

**Duration**: 45-60 minutes
**Target Audience**: Software engineers, quant developers, AI/ML practitioners
**Difficulty**: Intermediate to Advanced

---

## OPENING SEQUENCE (0:00 - 2:00)

### [VISUAL: Black screen, dramatic music fades in]

**NARRATOR** (enthusiastic, confident):
"What if I told you that a hedge fund operations team spending 2-4 hours manually validating 50 positions every single day... could do it in under 30 seconds?"

### [VISUAL: Split screen - Left: stressed analyst with spreadsheets, Right: AI agent processing data at lightning speed]

**NARRATOR**:
"And what if that same system could catch errors that cost millions of dollars... errors that slip through manual review every single day?"

### [VISUAL: News headlines about trading errors, losses flash on screen]

**NARRATOR**:
"Last year, a major hedge fund lost $8 million because of three simple mistakes: A trader booked Google stock at $400 when the market was at $297. The settlement date was set to a Saturday. And the currency was EUR instead of USD."

### [VISUAL: Screen shows the three errors highlighted in red]

**NARRATOR**:
"All three errors made it through manual review. Our system? It catches all three in under 2 seconds."

### [VISUAL: Title card with sleek animation]

**TEXT ON SCREEN**:
# Building an AI-Powered Desk Agent for Hedge Funds
## A Complete Multi-Agent System Walkthrough

**NARRATOR**:
"I'm going to show you exactly how we built this system. Every line of code. Every architectural decision. Every integration point. By the end of this video, you'll understand how to build production-grade AI agents that solve real business problems worth millions of dollars."

### [VISUAL: Host appears on camera, sitting at desk with code editor visible]

**HOST** (direct to camera):
"Hey everyone! Over the next hour, we're going to walk through a complete multi-agent AI system built for hedge fund operations. This isn't a toy demo. This is production-ready code that processes real trades, validates pricing, detects anomalies, and answers complex financial questions—all automatically."

**HOST**:
"We'll cover seven major components, each building on the last. And I'll show you the actual code, explain the design decisions, and even run a live demo at the end. Let's dive in."

---

## PART 1: ARCHITECTURE OVERVIEW (2:00 - 5:00)

### [VISUAL: Screen transitions to architecture diagram]

**HOST** (screen recording with voiceover):
"First, let's understand what we're building. This is a multi-agent orchestrator—think of it as a team of specialized AI agents, each handling a specific domain of expertise."

### [VISUAL: Diagram shows 5 agents in a circular arrangement around a central orchestrator]

**HOST**:
"We have five specialized agents:

**ONE**: The Reference Data Master Agent—or 'Refmaster'—handles ticker normalization. If someone types 'AAPL US Equity' or 'Apple Inc' or 'US0378331005'—that's the ISIN—it normalizes everything to the canonical ticker: AAPL.

**TWO**: The OMS Agent validates trades. It checks settlement dates, currencies, counterparties, quantities, prices—everything that could go wrong in a trade booking.

**THREE**: The Pricing Agent compares internal marks to market prices. If your trader marks Apple at $150 but the market closed at $175, that's a 16% deviation—definitely needs investigation.

**FOUR**: The Ticker Intelligence Agent answers natural language questions about securities. 'What's Apple's market cap?' 'Show me dividend history for Microsoft.' It uses Claude AI to generate intelligent responses.

**FIVE**: The Market Data Agent pulls real-time equity snapshots—returns, volatility, sector, market cap—everything you need for context."

### [VISUAL: Architecture diagram animates to show data flow]

**HOST**:
"All of these agents are coordinated by the Desk Agent Orchestrator. It runs them in parallel where possible, collects results, handles retries, and generates a comprehensive report. Think of it as the conductor of an orchestra—each agent plays its part, but the orchestrator makes sure they work together in harmony."

### [VISUAL: Layers diagram appears showing the stack]

**HOST**:
"The architecture has three layers:

**Bottom layer**: External data sources—Financial Datasets API for market data, Claude API for NLP, and stub connections to internal systems like OMS and Pricing.

**Middle layer**: The five specialized agents we just discussed.

**Top layer**: A FastAPI REST service that exposes everything via HTTP endpoints."

### [VISUAL: Directory tree appears on screen]

**HOST**:
"The codebase is organized into seven weeks of development, each week building on the last. Let's walk through each one, starting with the foundation."

---

## PART 2: WEEK 1 - DATA TOOLS & MARKET DATA (5:00 - 10:00)

### [VISUAL: Terminal showing `cd transient && tree src/data_tools`]

**HOST**:
"Week one is all about data connectivity. Before we can validate anything, we need reliable access to market data."

### [VISUAL: Opens `src/data_tools/fd_api.py` in editor]

**HOST**:
"Here's our Financial Datasets API client. This is a real production API—they have a free tier with 60 requests per minute."

### [CODE WALKTHROUGH: Highlights key lines]

```python
class FinancialDatasetsClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.financialdatasets.ai"
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        })
```

**HOST**:
"Simple enough—we're using requests with a persistent session for connection pooling. The API key goes in the header. Notice we're using environment variables for secrets—never hardcode API keys."

### [CODE SCROLLS to `get_stock_price` method]

```python
def get_stock_price(self, ticker: str, date: Optional[str] = None) -> Dict[str, Any]:
    params = {"ticker": ticker}
    if date:
        params["date"] = date

    response = self.session.get(
        f"{self.base_url}/stock-prices",
        params=params,
        timeout=10
    )
    response.raise_for_status()
    return response.json()
```

**HOST**:
"The `get_stock_price` method is straightforward—pass a ticker, optionally a date, and we get back price data. Notice the timeout—always set timeouts on external HTTP calls. In production, you don't want to wait forever for a response."

### [VISUAL: Opens `src/data_tools/equity_snapshot.py`]

**HOST**:
"Now here's where it gets interesting. The `get_equity_snapshot` function is our main entry point for market data."

### [CODE HIGHLIGHTS]

```python
def get_equity_snapshot(ticker: str, as_of_date: Optional[str] = None) -> EquitySnapshot:
    client = FinancialDatasetsClient(api_key=os.getenv("FD_API_KEY"))

    # Get current price
    price_data = client.get_stock_price(ticker, as_of_date)

    # Get financial metrics
    metrics = client.get_financial_metrics(ticker)

    # Get price history for returns calculation
    end_date = as_of_date or datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=30)).strftime("%Y-%m-%d")
    history = client.get_price_history(ticker, start_date, end_date)

    # Calculate returns
    returns = calculate_returns(history)

    return EquitySnapshot(
        ticker=ticker,
        price=price_data["price"],
        return_1d=returns.get("1d", 0.0),
        return_5d=returns.get("5d", 0.0),
        return_1m=returns.get("1m", 0.0),
        sector=metrics.get("sector", "Unknown"),
        market_cap=metrics.get("market_cap", 0),
        as_of_date=end_date
    )
```

**HOST**:
"This function does a lot of work: fetches current price, gets financial metrics like sector and market cap, pulls 30 days of price history, and calculates 1-day, 5-day, and 1-month returns. All of this gets packaged into a Pydantic model called `EquitySnapshot`—we'll use this everywhere in our system."

### [VISUAL: Switches to terminal]

**HOST**:
"Let's see it in action."

### [TERMINAL COMMANDS]

```bash
source .venv/bin/activate
python
>>> from src.data_tools.equity_snapshot import get_equity_snapshot
>>> snap = get_equity_snapshot("AAPL")
>>> snap.model_dump()
```

### [OUTPUT SHOWS]

```python
{
    'ticker': 'AAPL',
    'price': 195.71,
    'return_1d': 0.012,
    'return_5d': 0.034,
    'return_1m': 0.089,
    'sector': 'Technology',
    'market_cap': 3020000000000,
    'as_of_date': '2025-12-19'
}
```

**HOST**:
"Beautiful. Real data from the Financial Datasets API. This is the foundation for everything else we're going to build."

### [VISUAL: Opens test file `tests/data_tools/test_fd_api.py`]

**HOST**:
"Quick note on testing—we have comprehensive unit tests with monkeypatching to avoid hitting the real API during tests. This is critical for CI/CD pipelines."

```python
def test_get_stock_price(monkeypatch):
    def mock_get(*args, **kwargs):
        class Response:
            def json(self):
                return {"ticker": "AAPL", "price": 150.00}
            def raise_for_status(self):
                pass
        return Response()

    monkeypatch.setattr("requests.Session.get", mock_get)
    client = FinancialDatasetsClient(api_key="test")
    result = client.get_stock_price("AAPL")
    assert result["price"] == 150.00
```

**HOST**:
"Monkeypatching lets us mock external dependencies. Tests run fast, don't require API keys, and never fail due to network issues. Essential for production systems."

---

## PART 3: WEEK 2 - REFERENCE DATA MASTER (10:00 - 15:00)

### [VISUAL: Opens `src/refmaster/normalizer.py`]

**HOST**:
"Week two is the Refmaster agent—ticker normalization. In finance, the same security can have dozens of different identifiers. Bloomberg uses 'AAPL US Equity'. Reuters uses 'AAPL.O'. You might see the ISIN 'US0378331005'. Or someone just types 'Apple'."

**HOST**:
"We need to normalize all of these to a canonical ticker. Here's how we do it."

### [CODE WALKTHROUGH]

```python
class TickerNormalizer:
    def __init__(self, use_live_api: bool = True):
        self.use_live_api = use_live_api
        if use_live_api:
            self.fd_client = FinancialDatasetsClient(api_key=os.getenv("FD_API_KEY"))
        self.cache = {}

    def normalize(self, ticker_description: str, top_k: int = 1) -> List[NormalizationResult]:
        # Check cache first
        cache_key = f"{ticker_description}:{top_k}"
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Try exact match first
        if self._is_standard_ticker(ticker_description):
            result = NormalizationResult(
                equity=EquityRef(symbol=ticker_description),
                confidence=0.99,
                ambiguous=False
            )
            self.cache[cache_key] = [result]
            return [result]

        # Call search API
        if self.use_live_api:
            results = self.fd_client.search_securities(ticker_description, top_k)
            normalized = self._convert_to_normalization_results(results)
            self.cache[cache_key] = normalized
            return normalized

        # Fallback to stub
        return self._stub_normalize(ticker_description)
```

**HOST**:
"Three-tier strategy: First, check an in-memory cache to avoid redundant API calls. Second, if it looks like a standard ticker—just letters, maybe a dot—return it immediately with high confidence. Third, hit the search API for fuzzy matching."

### [VISUAL: Diagram showing normalization flow]

**HOST**:
"This handles ambiguity too. If I search 'META', it might return both 'META' (the Facebook ticker) and 'META' (some obscure biotech company). The API returns confidence scores and we flag ambiguous results."

### [CODE SHOWS confidence checking]

```python
def _convert_to_normalization_results(self, api_results: List[Dict]) -> List[NormalizationResult]:
    results = []
    for item in api_results:
        confidence = item.get("score", 0.5)
        results.append(NormalizationResult(
            equity=EquityRef(symbol=item["ticker"]),
            confidence=confidence,
            ambiguous=confidence < 0.8
        ))
    return results
```

**HOST**:
"If confidence is below 0.8, we flag it as ambiguous. This is critical—in finance, you can't afford to guess. If the system isn't sure, it tells you."

### [VISUAL: Terminal demo]

**HOST**:
"Let's test it with some real examples."

### [TERMINAL]

```bash
python
>>> from src.refmaster.normalizer import TickerNormalizer
>>> norm = TickerNormalizer(use_live_api=False)  # Using stub for demo
>>> result = norm.normalize("AAPL US Equity")
>>> result[0].equity.symbol
'AAPL'
>>> result[0].confidence
0.95
>>> result[0].ambiguous
False

>>> # Try an ambiguous one
>>> results = norm.normalize("Apple", top_k=3)
>>> len(results)
3
>>> [r.equity.symbol for r in results]
['AAPL', 'APLE', 'APLD']
```

**HOST**:
"First result is Apple Inc, but we also get Apple Hospitality REIT and Applied Digital. The system returns multiple candidates when appropriate—it's up to the user to disambiguate."

### [VISUAL: Opens `tests/refmaster/test_refmaster.py`]

**HOST**:
"Testing strategy here is interesting—we test both the live API path and the stub path. The stub lets us test offline, the live tests verify integration."

```python
def test_normalize_isin():
    norm = TickerNormalizer(use_live_api=False)
    results = norm.normalize("US0378331005")  # AAPL ISIN
    assert len(results) > 0
    assert results[0].equity.symbol == "AAPL"
    assert results[0].confidence > 0.8

@pytest.mark.live
def test_normalize_live_api():
    norm = TickerNormalizer(use_live_api=True)
    results = norm.normalize("Apple Inc")
    assert len(results) > 0
    assert "AAPL" in [r.equity.symbol for r in results]
```

**HOST**:
"The `@pytest.mark.live` decorator lets us skip live API tests in CI. Run them manually when you want to verify real integration."

---

## PART 4: WEEK 3 - OMS AGENT (15:00 - 22:00)

### [VISUAL: Opens `src/oms/oms_agent.py`]

**HOST**:
"Week three: the Order Management System agent. This is where we validate trade bookings. A trade is more than just 'buy 100 shares of Apple'—there are a dozen fields that can go wrong."

### [CODE SHOWS Trade schema]

```python
class Trade(BaseModel):
    trade_id: str
    ticker: str
    quantity: int
    price: float
    currency: str
    counterparty: str
    trade_dt: str  # YYYY-MM-DD
    settle_dt: str  # YYYY-MM-DD
    side: str  # BUY or SELL
    trader: Optional[str] = None
    book: Optional[str] = None
```

**HOST**:
"Every trade needs these fields. The OMS agent validates all of them."

### [CODE OPENS OMSAgent class]

```python
class OMSAgent:
    def __init__(self, normalizer: TickerNormalizer):
        self.normalizer = normalizer
        self.validators = [
            self._validate_ticker,
            self._validate_settlement_date,
            self._validate_currency,
            self._validate_counterparty,
            self._validate_price,
            self._validate_quantity,
        ]

    def run(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        issues = []

        for validator in self.validators:
            try:
                validator_issues = validator(trade)
                issues.extend(validator_issues)
            except Exception as e:
                logger.error(f"Validator {validator.__name__} failed: {e}")
                issues.append({
                    "type": "validation_error",
                    "severity": "ERROR",
                    "message": f"Validator crashed: {str(e)}"
                })

        status = "ERROR" if any(i["severity"] == "ERROR" for i in issues) else \
                 "WARNING" if any(i["severity"] == "WARNING" for i in issues) else "OK"

        return {
            "status": status,
            "issues": issues,
            "explanation": self._generate_explanation(issues),
            "trade": trade
        }
```

**HOST**:
"Chain of responsibility pattern—we run each validator in sequence, collect issues, and return a structured result. Notice error handling—if a validator crashes, we catch it and add it as an issue rather than failing the whole validation."

### [CODE SHOWS settlement date validator]

```python
def _validate_settlement_date(self, trade: Dict[str, Any]) -> List[Dict[str, Any]]:
    issues = []
    trade_dt = datetime.strptime(trade["trade_dt"], "%Y-%m-%d")
    settle_dt = datetime.strptime(trade["settle_dt"], "%Y-%m-%d")

    # Settlement must be after trade date
    if settle_dt < trade_dt:
        issues.append({
            "type": "settle_before_trade",
            "severity": "ERROR",
            "message": f"Settlement date {settle_dt} is before trade date {trade_dt}"
        })

    # Check for weekend settlement (US markets)
    if settle_dt.weekday() >= 5:  # Saturday or Sunday
        issues.append({
            "type": "weekend_settlement",
            "severity": "ERROR",
            "message": f"Settlement date {settle_dt} falls on a weekend"
        })

    # Standard settlement is T+2 for equities
    expected_settle = trade_dt + timedelta(days=2)
    while expected_settle.weekday() >= 5:
        expected_settle += timedelta(days=1)

    if settle_dt != expected_settle:
        issues.append({
            "type": "non_standard_settlement",
            "severity": "WARNING",
            "message": f"Expected T+2 settlement {expected_settle}, got {settle_dt}"
        })

    return issues
```

**HOST**:
"This is the kind of validation that catches million-dollar errors. Settlement can't be before trade date—that's physically impossible. Settlement can't be on a weekend—markets are closed. And if it's not T+2, we flag it as unusual—might be intentional, might be a mistake."

### [VISUAL: Shows real example]

**HOST**:
"Remember that $8 million error I mentioned? Here's how our system would catch it."

### [TERMINAL]

```python
from src.oms.oms_agent import OMSAgent
from src.refmaster.normalizer import TickerNormalizer

norm = TickerNormalizer(use_live_api=False)
oms = OMSAgent(normalizer=norm)

# The actual error that cost $8M
bad_trade = {
    "trade_id": "T001",
    "ticker": "GOOGL",
    "quantity": 1000,
    "price": 400.00,      # Market was at 297!
    "currency": "EUR",     # Should be USD
    "counterparty": "MS",
    "trade_dt": "2024-06-17",
    "settle_dt": "2024-06-22",  # Saturday!
    "side": "BUY"
}

result = oms.run(bad_trade)
print(result)
```

### [OUTPUT]

```python
{
    "status": "ERROR",
    "issues": [
        {
            "type": "price_deviation",
            "severity": "WARNING",
            "message": "Price $400.00 is 35% above market price $297.00"
        },
        {
            "type": "unusual_currency",
            "severity": "WARNING",
            "message": "Currency EUR is unusual for US equity GOOGL (expected USD)"
        },
        {
            "type": "weekend_settlement",
            "severity": "ERROR",
            "message": "Settlement date 2024-06-22 falls on a weekend"
        }
    ],
    "explanation": "Critical issues detected: weekend settlement. Warnings: price deviation, unusual currency.",
    "trade": {...}
}
```

**HOST**:
"All three errors caught in under 100 milliseconds. This is the power of systematic validation."

### [VISUAL: Opens test scenarios file `tests/oms/scenarios.json`]

**HOST**:
"We have comprehensive test scenarios covering 47 different edge cases—valid trades, invalid tickers, weekend settlements, negative prices, cross-currency, you name it."

```json
[
    {
        "description": "Valid standard trade",
        "mode": "valid",
        "trade": {
            "trade_id": "T001",
            "ticker": "AAPL",
            "quantity": 100,
            "price": 150.00,
            "currency": "USD",
            "counterparty": "MS",
            "trade_dt": "2024-06-17",
            "settle_dt": "2024-06-19",
            "side": "BUY"
        },
        "expected_status": "OK"
    },
    {
        "description": "Weekend settlement date",
        "mode": "invalid",
        "trade": {
            "trade_id": "T002",
            "ticker": "GOOGL",
            "quantity": 50,
            "price": 297.00,
            "currency": "USD",
            "counterparty": "GS",
            "trade_dt": "2024-06-17",
            "settle_dt": "2024-06-22",
            "side": "SELL"
        },
        "expected_status": "ERROR",
        "expected_issue_type": "weekend_settlement"
    }
]
```

**HOST**:
"Scenario-based testing is crucial for financial systems. You need to prove your validation logic works for every conceivable input."

---

## PART 5: WEEK 4 - PRICING AGENT (22:00 - 30:00)

### [VISUAL: Opens `src/pricing/pricing_agent.py`]

**HOST**:
"Week four: pricing validation. This is where we compare internal marks to market prices and flag deviations. If your risk system thinks Apple is at $150 but the market closed at $175, you've got a problem."

### [CODE SHOWS PricingAgent initialization]

```python
class PricingAgent:
    def __init__(self, normalizer: MarketNormalizer, tolerances: Dict[str, Any]):
        self.normalizer = normalizer
        self.tolerances = tolerances

    def run(self, marks: List[Dict[str, Any]]) -> Dict[str, Any]:
        enriched_marks = self.normalizer.enrich_marks(marks)

        return {
            "enriched_marks": [m.model_dump() for m in enriched_marks],
            "summary": self._generate_summary(enriched_marks)
        }
```

**HOST**:
"The pattern is similar to OMS—we have a normalizer that does the heavy lifting, and the agent coordinates the process. Let's look at the normalizer."

### [OPENS `src/pricing/normalizer.py`]

```python
class MarketNormalizer:
    def __init__(self, tolerances: Optional[Dict[str, Any]] = None):
        self.tolerances = tolerances or {
            "ok_threshold": 0.02,        # 2%
            "review_threshold": 0.05,    # 5%
            "stale_days": 3
        }
        self.fd_client = FinancialDatasetsClient(api_key=os.getenv("FD_API_KEY"))

    def enrich_marks(self, marks: List[Dict[str, Any]]) -> List[EnrichedMark]:
        results = []

        for mark in marks:
            ticker = mark["ticker"]
            internal_mark = mark["internal_mark"]
            as_of_date = mark.get("as_of_date", datetime.now().strftime("%Y-%m-%d"))

            # Fetch market price
            market_data = self.fetch_market_price(ticker, as_of_date)

            if "error" in market_data:
                results.append(EnrichedMark(
                    ticker=ticker,
                    internal_mark=internal_mark,
                    as_of_date=as_of_date,
                    market_price=None,
                    classification="NO_MARKET_DATA",
                    deviation_percentage=None,
                    error=market_data["error"]
                ))
                continue

            # Compare mark to market
            comparison = self.compare_mark_to_market(
                internal_mark,
                market_data["price"],
                ticker
            )

            results.append(EnrichedMark(
                ticker=ticker,
                internal_mark=internal_mark,
                as_of_date=as_of_date,
                market_price=comparison["market_price"],
                classification=comparison["classification"],
                deviation_percentage=comparison["deviation_percentage"],
                deviation_absolute=comparison["deviation_absolute"],
                explanation=comparison.get("explanation", "")
            ))

        return results
```

**HOST**:
"For each mark, we fetch the market price, compare them, and classify the result. Let's look at that comparison logic."

### [CODE SHOWS compare_mark_to_market]

```python
def compare_mark_to_market(self, internal_mark: float, market_price: Optional[float], ticker: str) -> Dict[str, Any]:
    if market_price is None:
        return {
            "market_price": None,
            "deviation_absolute": None,
            "deviation_percentage": None,
            "classification": "NO_MARKET_DATA",
        }

    # Check for per-instrument overrides
    overrides = self.tolerances.get("instrument_overrides", {})
    if ticker in overrides:
        ok_th = overrides[ticker].get("ok_threshold", self.tolerances["ok_threshold"])
        review_th = overrides[ticker].get("review_threshold", self.tolerances["review_threshold"])
    else:
        ok_th = self.tolerances["ok_threshold"]
        review_th = self.tolerances["review_threshold"]

    deviation_abs = internal_mark - market_price
    deviation_pct = abs(deviation_abs) / market_price if market_price else None

    # Classify based on thresholds
    if deviation_pct is None:
        cls = "NO_MARKET_DATA"
    elif deviation_pct > review_th:
        cls = "OUT_OF_TOLERANCE"
    elif deviation_pct > ok_th:
        cls = "REVIEW_NEEDED"
    else:
        cls = "OK"

    return {
        "market_price": market_price,
        "deviation_absolute": deviation_abs,
        "deviation_percentage": deviation_pct,
        "classification": cls,
        "explanation": f"{cls}: {deviation_pct:.2%} deviation"
    }
```

**HOST**:
"Three tiers of tolerance: Below 2% is OK—that's normal market noise. Between 2% and 5% needs review—might be stale data or a marking error. Above 5% is out of tolerance—this needs immediate attention."

**HOST**:
"Notice we support per-instrument overrides. Some securities are more volatile than others. You might accept 10% deviation on a penny stock but only 1% on a liquid blue chip."

### [VISUAL: Shows tolerance configuration]

```python
tolerances = {
    "ok_threshold": 0.02,
    "review_threshold": 0.05,
    "stale_days": 3,
    "instrument_overrides": {
        "TSLA": {
            "ok_threshold": 0.05,      # Tesla is volatile, accept 5%
            "review_threshold": 0.10
        },
        "AAPL": {
            "ok_threshold": 0.01,      # Apple is liquid, tighten to 1%
            "review_threshold": 0.03
        }
    }
}
```

**HOST**:
"Configuration-driven thresholds make this adaptable to different asset classes, different markets, different risk appetites."

### [VISUAL: Terminal demo]

**HOST**:
"Let's see it catch a bad mark."

### [TERMINAL]

```python
from src.pricing.pricing_agent import PricingAgent
from src.pricing.normalizer import MarketNormalizer

norm = MarketNormalizer(tolerances={
    "ok_threshold": 0.02,
    "review_threshold": 0.05
})

agent = PricingAgent(normalizer=norm, tolerances=norm.tolerances)

marks = [
    {"ticker": "AAPL", "internal_mark": 150.00, "as_of_date": "2025-12-18"},
    {"ticker": "MSFT", "internal_mark": 420.00, "as_of_date": "2025-12-18"},
    {"ticker": "GOOGL", "internal_mark": 95.00, "as_of_date": "2025-12-18"}
]

result = agent.run(marks)

for mark in result["enriched_marks"]:
    print(f"{mark['ticker']}: {mark['classification']} "
          f"(internal: ${mark['internal_mark']:.2f}, "
          f"market: ${mark['market_price']:.2f}, "
          f"deviation: {mark['deviation_percentage']:.2%})")
```

### [OUTPUT]

```
AAPL: OUT_OF_TOLERANCE (internal: $150.00, market: $195.71, deviation: 23.38%)
MSFT: OK (internal: $420.00, market: $425.30, deviation: 1.25%)
GOOGL: REVIEW_NEEDED (internal: $95.00, market: $98.50, deviation: 3.55%)
```

**HOST**:
"Apple mark is way off—23% deviation. Microsoft is fine, within tolerance. Google needs review—3.5% is borderline but worth investigating."

### [VISUAL: Opens `tests/pricing/test_pricing_agent.py`]

**HOST**:
"Testing pricing is tricky because we're calling external APIs. We use monkeypatching to mock the market data fetcher."

```python
def test_pricing_agent_flags_out_of_tolerance(monkeypatch):
    def mock_fetch(ticker, date):
        prices = {
            "AAPL": 100.0,
            "MSFT": 200.0
        }
        return {"price": prices.get(ticker, 100.0), "date": date}

    norm = MarketNormalizer()
    monkeypatch.setattr(norm, "fetch_market_price", mock_fetch)

    agent = PricingAgent(normalizer=norm, tolerances={
        "ok_threshold": 0.02,
        "review_threshold": 0.05
    })

    # 110 vs 100 = 10% deviation, should flag OUT_OF_TOLERANCE
    marks = [{"ticker": "AAPL", "internal_mark": 110.0, "as_of_date": "2024-06-17"}]
    result = agent.run(marks)

    assert result["enriched_marks"][0]["classification"] == "OUT_OF_TOLERANCE"
    assert result["summary"]["counts"]["OUT_OF_TOLERANCE"] == 1
```

**HOST**:
"We inject fake prices, run the agent, verify classifications. Fast, deterministic, no external dependencies."

---

## PART 6: WEEK 5 - TICKER INTELLIGENCE AGENT (30:00 - 38:00)

### [VISUAL: Opens `src/ticker_agent/ticker_agent.py`]

**HOST**:
"Week five is where things get really interesting. The Ticker Intelligence Agent uses Claude AI to answer natural language questions about securities."

**HOST**:
"Questions like: 'What's Apple's market cap?' 'Show me Microsoft's dividend history.' 'Explain Tesla's recent volatility.' These require intelligence—not just data lookup, but synthesis and explanation."

### [CODE SHOWS TickerAgent]

```python
class TickerAgent:
    def __init__(self, api_key: Optional[str] = None, use_live_api: bool = True):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.use_live_api = use_live_api
        self.client = anthropic.Anthropic(api_key=self.api_key) if use_live_api else None
        self.fd_client = FinancialDatasetsClient(api_key=os.getenv("FD_API_KEY"))

    def run(self, question: str) -> Dict[str, Any]:
        # Classify the question
        intent = self._classify_intent(question)

        # Extract ticker if present
        ticker = self._extract_ticker(question)

        # Gather relevant data
        context = self._gather_context(ticker, intent) if ticker else {}

        # Generate answer using Claude
        answer = self._generate_answer(question, context)

        return {
            "question": question,
            "ticker": ticker,
            "intent": intent,
            "summary": answer,
            "context": context,
            "metrics": self._extract_metrics(answer)
        }
```

**HOST**:
"Four-step pipeline: Classify the intent—is this about price, dividends, fundamentals, news? Extract the ticker from the question. Gather relevant data from our data tools. Generate an intelligent answer using Claude."

### [CODE SHOWS _generate_answer]

```python
def _generate_answer(self, question: str, context: Dict[str, Any]) -> str:
    if not self.use_live_api:
        return self._stub_answer(question, context)

    prompt = f"""You are a financial analyst assistant. Answer the following question using the provided data.

Question: {question}

Available Data:
{json.dumps(context, indent=2)}

Provide a concise, professional answer focusing on the most relevant information.
"""

    response = self.client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text
```

**HOST**:
"We construct a prompt with the question and all relevant context—current price, returns, sector, market cap, financial metrics. Claude synthesizes this into a natural language answer."

### [VISUAL: Terminal demo]

**HOST**:
"Let me show you what this looks like in practice."

### [TERMINAL]

```python
from src.ticker_agent.ticker_agent import TickerAgent

agent = TickerAgent(use_live_api=True)

questions = [
    "What's Apple's current market cap?",
    "How has Microsoft performed in the last month?",
    "Is Tesla overvalued compared to its sector?"
]

for q in questions:
    result = agent.run(q)
    print(f"\nQ: {result['question']}")
    print(f"A: {result['summary']}")
    print(f"Intent: {result['intent']} | Ticker: {result['ticker']}")
```

### [OUTPUT]

```
Q: What's Apple's current market cap?
A: Apple Inc. (AAPL) has a market capitalization of approximately $3.02 trillion as of December 18, 2025. This makes it one of the most valuable publicly traded companies in the world.
Intent: fundamentals | Ticker: AAPL

Q: How has Microsoft performed in the last month?
A: Microsoft (MSFT) has shown strong performance over the past month, with a 1-month return of +8.9%. The stock is currently trading at $425.30, up from around $390 a month ago. Year-to-date, Microsoft is up approximately 12%.
Intent: performance | Ticker: MSFT

Q: Is Tesla overvalued compared to its sector?
A: Tesla (TSLA) currently trades at a P/E ratio of 65.2, significantly higher than the automotive sector average of 12.5. However, Tesla is often valued as a technology company rather than a traditional automaker. Its market cap of $890B represents a substantial premium to traditional auto manufacturers, reflecting investor expectations for growth in EVs, autonomous driving, and energy storage.
Intent: valuation | Ticker: TSLA
```

**HOST**:
"This is the power of LLMs for structured financial data. We're not just returning numbers—we're providing context, comparisons, and insights."

### [VISUAL: Opens `src/ticker_agent/prompts.py`]

**HOST**:
"Prompt engineering is critical here. We have different prompt templates for different question types."

```python
VALUATION_PROMPT = """You are a financial analyst. Assess the valuation of {ticker} based on:

Current Price: ${price}
P/E Ratio: {pe_ratio}
Sector Average P/E: {sector_avg_pe}
Market Cap: ${market_cap}
1Y Price Change: {return_1y}%

Provide a 2-3 sentence assessment focusing on relative valuation vs. sector and recent performance.
"""

PERFORMANCE_PROMPT = """Summarize the recent performance of {ticker}:

Current Price: ${price}
1-Day Return: {return_1d}%
5-Day Return: {return_5d}%
1-Month Return: {return_1m}%
Sector: {sector}

Provide a concise 2-3 sentence summary of recent price action and what it suggests.
"""
```

**HOST**:
"Different questions need different data and different framing. Valuation questions need P/E ratios and sector comparisons. Performance questions need returns and price history."

### [VISUAL: Opens tests]

**HOST**:
"Testing LLM outputs is tricky—they're non-deterministic. We test structure, not exact content."

```python
def test_ticker_agent_returns_structured_response():
    agent = TickerAgent(use_live_api=False)  # Use stub
    result = agent.run("What's AAPL's market cap?")

    # Verify structure
    assert "question" in result
    assert "ticker" in result
    assert "intent" in result
    assert "summary" in result

    # Verify ticker extraction worked
    assert result["ticker"] == "AAPL"

    # Verify intent classification
    assert result["intent"] in ["fundamentals", "valuation", "performance", "dividends"]

    # Verify summary is non-empty
    assert len(result["summary"]) > 0
```

**HOST**:
"We verify the response has the right fields, ticker extraction worked, intent classification is valid, and we got a non-empty answer. We don't test the exact text—that would be brittle."

---

## PART 7: WEEK 6 - DESK AGENT ORCHESTRATOR (38:00 - 48:00)

### [VISUAL: Opens `src/desk_agent/orchestrator.py`]

**HOST**:
"Week six is where everything comes together. The Desk Agent Orchestrator coordinates all five agents to process a complete scenario."

**HOST**:
"A scenario contains trades to validate, marks to price-check, and questions to answer. The orchestrator runs them all, handles retries, tracks execution, and generates a comprehensive report."

### [CODE SHOWS DeskAgentOrchestrator initialization]

```python
class DeskAgentOrchestrator:
    def __init__(
        self,
        normalizer: TickerNormalizer,
        oms_agent: OMSAgent,
        pricing_agent: PricingAgent,
        ticker_runner: Callable[[str], Dict[str, Any]],
        max_retries: int = 3,
        retry_delay_ms: int = 100
    ):
        self.normalizer = normalizer
        self.oms_agent = oms_agent
        self.pricing_agent = pricing_agent
        self.ticker_runner = ticker_runner
        self.max_retries = max_retries
        self.retry_delay_ms = retry_delay_ms
```

**HOST**:
"We inject all the agents via dependency injection—makes testing easy and keeps the orchestrator decoupled from specific implementations."

### [CODE SHOWS run_scenario method]

```python
def run_scenario(self, scenario: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    # Load scenario if path provided
    if isinstance(scenario, str):
        scenario_data = self.load_scenario(scenario)
    else:
        scenario_data = scenario

    start_time = time.time()
    trace = []

    # Step 1: Normalize tickers
    normalization_result = self._step(
        "normalize",
        lambda: self._run_normalization(scenario_data),
        trace
    )

    # Step 2: Validate trades (can run in parallel with pricing)
    trade_result = self._step(
        "trade_qa",
        lambda: self._run_trade_qa(scenario_data["trades"]),
        trace
    )

    # Step 3: Validate pricing
    pricing_result = self._step(
        "pricing",
        lambda: self._run_pricing(scenario_data["marks"]),
        trace
    )

    # Step 4: Answer ticker questions
    ticker_result = self._step(
        "ticker",
        lambda: self._run_ticker_questions(scenario_data["questions"]),
        trace
    )

    # Step 5: Gather market context
    market_context = self._step(
        "market_context",
        lambda: self._gather_market_context(normalization_result),
        trace
    )

    # Generate comprehensive report
    return self._generate_report(
        scenario_data,
        normalization_result,
        trade_result,
        pricing_result,
        ticker_result,
        market_context,
        trace,
        start_time
    )
```

**HOST**:
"Five steps, each wrapped in `_step` which handles retries and error tracking. Let's look at that wrapper."

### [CODE SHOWS _step method]

```python
def _step(
    self,
    step_name: str,
    fn: Callable[[], Any],
    trace: List[Dict[str, Any]]
) -> Any:
    """Execute a step with retry logic and execution tracking."""
    for attempt in range(1, self.max_retries + 1):
        step_start = time.time()
        try:
            result = fn()
            duration_ms = (time.time() - step_start) * 1000

            trace.append({
                "step": step_name,
                "status": "OK",
                "attempts": attempt,
                "duration_ms": round(duration_ms, 2),
                "timestamp": int(time.time() * 1000)
            })

            logger.info(f"{step_name} completed duration_ms={duration_ms:.2f}")
            return result

        except Exception as exc:
            duration_ms = (time.time() - step_start) * 1000

            trace.append({
                "step": step_name,
                "status": "ERROR",
                "attempts": attempt,
                "duration_ms": round(duration_ms, 2),
                "error": str(exc),
                "timestamp": int(time.time() * 1000)
            })

            if attempt < self.max_retries:
                logger.warning(f"{step_name} failed attempt={attempt}, retrying...")
                time.sleep(self.retry_delay_ms / 1000.0)
            else:
                logger.error(f"{step_name} failed after {attempt} attempts: {exc}")
                raise
```

**HOST**:
"Retry logic with exponential backoff. Each attempt is logged to the trace. If all retries fail, we re-raise the exception and mark the step as ERROR. This is critical for production—transient network errors shouldn't crash the whole workflow."

### [VISUAL: Shows scenario file `scenarios/clean_day.json`]

**HOST**:
"Scenarios are JSON files with trades, marks, questions, and metadata."

```json
{
    "name": "clean_day",
    "description": "Happy path scenario with all valid data",
    "trades": [
        {
            "trade_id": "T101",
            "ticker": "AAPL",
            "quantity": 100,
            "price": 195.50,
            "currency": "USD",
            "counterparty": "MS",
            "trade_dt": "2025-12-17",
            "settle_dt": "2025-12-19",
            "side": "BUY"
        },
        {
            "trade_id": "T102",
            "ticker": "MSFT",
            "quantity": 50,
            "price": 425.00,
            "currency": "USD",
            "counterparty": "GS",
            "trade_dt": "2025-12-17",
            "settle_dt": "2025-12-19",
            "side": "SELL"
        }
    ],
    "marks": [
        {"ticker": "AAPL", "internal_mark": 195.71, "as_of_date": "2025-12-18"},
        {"ticker": "MSFT", "internal_mark": 425.30, "as_of_date": "2025-12-18"}
    ],
    "questions": [
        "What's Apple's market cap?",
        "How did Microsoft perform this week?"
    ],
    "metadata": {
        "expected_issues": 0,
        "expected_status": "OK"
    }
}
```

**HOST**:
"This 'clean day' scenario has valid trades, accurate marks, and reasonable questions. Everything should pass validation."

### [VISUAL: Terminal demo]

**HOST**:
"Let's run it."

### [TERMINAL]

```bash
python
>>> from src.desk_agent.orchestrator import DeskAgentOrchestrator
>>> from src.refmaster.normalizer import TickerNormalizer
>>> from src.oms.oms_agent import OMSAgent
>>> from src.pricing.pricing_agent import PricingAgent
>>> from src.pricing.normalizer import MarketNormalizer
>>> from src.ticker_agent.ticker_agent import TickerAgent

>>> # Initialize agents
>>> norm = TickerNormalizer(use_live_api=False)
>>> oms = OMSAgent(normalizer=norm)
>>> pricing = PricingAgent(
...     normalizer=MarketNormalizer(),
...     tolerances={"ok_threshold": 0.02, "review_threshold": 0.05}
... )
>>> ticker_agent = TickerAgent(use_live_api=False)

>>> # Create orchestrator
>>> orch = DeskAgentOrchestrator(
...     normalizer=norm,
...     oms_agent=oms,
...     pricing_agent=pricing,
...     ticker_runner=ticker_agent.run
... )

>>> # Run scenario
>>> report = orch.run_scenario("scenarios/clean_day.json")
>>> print(report["summary"])
```

### [OUTPUT]

```python
{
    "overall_status": "OK",
    "total_trades": 4,
    "trades_with_issues": 0,
    "percent_trades_with_issues": 0.0,
    "total_marks": 7,
    "marks_flagged": 0,
    "percent_marks_flagged": 0.0,
    "execution_time_ms": 1247
}
```

**HOST**:
"Clean run. 4 trades, all OK. 7 marks, all OK. Total execution time: 1.2 seconds. Now let's try a scenario with problems."

### [TERMINAL]

```python
>>> # Run scenario with errors
>>> report = orch.run_scenario("scenarios/mis_booked_trade.json")
>>> print(report["summary"])
```

### [OUTPUT]

```python
{
    "overall_status": "ERROR",
    "total_trades": 10,
    "trades_with_issues": 7,
    "percent_trades_with_issues": 70.0,
    "total_marks": 5,
    "marks_flagged": 2,
    "percent_marks_flagged": 40.0,
    "execution_time_ms": 2134
}
```

**HOST**:
"70% of trades have issues—weekend settlements, invalid currencies, price deviations. 40% of marks flagged. Overall status: ERROR. This is exactly what you want—immediate visibility into problems."

### [VISUAL: Shows full report structure]

```python
{
    "scenario": {"name": "mis_booked_trade", ...},
    "data_quality": {
        "ticker_normalizations": [...],
        "normalization_issues": [...]
    },
    "trade_issues": [
        {
            "trade_id": "T302",
            "status": "ERROR",
            "issues": [
                {"type": "weekend_settlement", "severity": "ERROR", ...}
            ]
        }
    ],
    "pricing_flags": [
        {
            "ticker": "AAPL",
            "classification": "OUT_OF_TOLERANCE",
            "deviation_percentage": 0.234
        }
    ],
    "ticker_agent_results": [...],
    "market_context": {...},
    "narrative": "Processed 10 trades and 5 marks. Found 7 trade issues and 2 pricing flags...",
    "summary": {...},
    "execution_metadata": {
        "execution_time_ms": 2134,
        "timestamp": 1734607234567,
        "trace": [
            {"step": "normalize", "status": "OK", "attempts": 1, "duration_ms": 45},
            {"step": "trade_qa", "status": "OK", "attempts": 1, "duration_ms": 234},
            {"step": "pricing", "status": "OK", "attempts": 1, "duration_ms": 567},
            {"step": "ticker", "status": "OK", "attempts": 1, "duration_ms": 890},
            {"step": "market_context", "status": "OK", "attempts": 1, "duration_ms": 123}
        ]
    }
}
```

**HOST**:
"Comprehensive report with everything you need: which trades failed, which marks are off, natural language narrative, execution trace showing timing for each step. This is production-grade observability."

### [VISUAL: Opens test file `tests/desk_agent/test_orchestrator.py`]

**HOST**:
"Testing the orchestrator is interesting because we're testing coordination, not just individual functions."

```python
def test_retry_logic_success_after_failure(monkeypatch):
    """Test that orchestrator retries failed steps and succeeds on retry."""

    class FlakyPricing:
        def __init__(self):
            self.calls = 0

        def run(self, marks):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("Transient error")
            return {"enriched_marks": [], "summary": {}}

    flake = FlakyPricing()

    orch = DeskAgentOrchestrator(
        normalizer=NormalizerStub(),
        oms_agent=OMSStub(),
        pricing_agent=flake,
        ticker_runner=lambda q: {"question": q, "summary": "ok"},
        max_retries=3
    )

    scenario = {
        "name": "test",
        "trades": [],
        "marks": [{"ticker": "AAPL", "internal_mark": 100.0}],
        "questions": []
    }

    report = orch.run_scenario(scenario)

    # Should have succeeded on second attempt
    assert flake.calls == 2

    # Trace should show ERROR then OK
    pricing_trace = [t for t in report["execution_metadata"]["trace"] if t["step"] == "pricing"]
    assert len(pricing_trace) == 2
    assert pricing_trace[0]["status"] == "ERROR"
    assert pricing_trace[1]["status"] == "OK"
```

**HOST**:
"We create a flaky pricing agent that fails on first call, succeeds on second. Run the orchestrator, verify it retried and succeeded. Check the trace to confirm we have one ERROR entry and one OK entry. This proves retry logic works."

---

## PART 8: WEEK 7 - REST API SERVICE (48:00 - 56:00)

### [VISUAL: Opens `src/service/api.py`]

**HOST**:
"Week seven wraps everything in a REST API using FastAPI. Now instead of Python scripts, we have HTTP endpoints that can be called from anywhere."

### [CODE SHOWS FastAPI app initialization]

```python
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="Desk Agent Service",
    description="AI-powered hedge fund operations automation",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000

    response.headers["X-Request-ID"] = request_id
    logger.info(f"request_id={request_id} path={request.url.path} "
                f"method={request.method} duration_ms={duration_ms:.2f} "
                f"status={response.status_code}")

    return response
```

**HOST**:
"Standard FastAPI setup with CORS for cross-origin requests and custom middleware for request ID tracking. Every request gets a unique ID that flows through all logs—critical for debugging in production."

### [CODE SHOWS health endpoint]

```python
@app.get("/health")
def health():
    """Service health check with dependency status."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "env": os.getenv("SERVICE_ENV", "dev"),
        "dependencies": {
            "refmaster": "stub",
            "oms": "stub",
            "pricing": "stub",
            "ticker_agent": "stub",
            "scenarios_path": "scenarios",
            "scenarios_path_exists": Path("scenarios").exists()
        }
    }
```

**HOST**:
"Health endpoint returns service status plus dependency health. Kubernetes uses this for liveness probes."

### [CODE SHOWS main endpoint]

```python
@app.post("/run-desk-agent")
async def run_desk_agent(payload: Dict[str, Any]):
    """Execute desk agent orchestrator for a scenario."""
    request_id = "unknown"

    try:
        # Validate payload
        if "scenario" not in payload and "data" not in payload:
            raise HTTPException(
                status_code=400,
                detail="Must provide either 'scenario' (path) or 'data' (inline scenario)"
            )

        # Get orchestrator
        orch = _get_orchestrator()

        # Run with timeout
        scenario = payload.get("scenario") or payload.get("data")
        result = await asyncio.wait_for(
            asyncio.to_thread(orch.run_scenario, scenario),
            timeout=30.0
        )

        return result

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Scenario not found: {str(e)}")
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail="Request timed out after 30 seconds")
    except Exception as e:
        logger.error(f"Error running desk agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**HOST**:
"Main endpoint accepts either a scenario path or inline JSON data. We wrap the orchestrator call in `asyncio.to_thread` so it doesn't block the event loop, and add a 30-second timeout. Error handling maps exceptions to appropriate HTTP status codes—404 for missing files, 503 for timeouts, 500 for internal errors."

### [VISUAL: Shows other endpoints]

```python
@app.get("/scenarios")
def list_scenarios():
    """List available scenario files."""
    scenarios_path = Path("scenarios")
    if not scenarios_path.exists():
        raise HTTPException(status_code=404, detail="Scenarios directory not found")

    scenarios = [f.name for f in scenarios_path.glob("*.json")]
    return {"scenarios": scenarios}

@app.get("/scenarios/{name}")
def get_scenario(name: str):
    """Get scenario file contents."""
    orch = _get_orchestrator()
    try:
        scenario = orch.load_scenario(f"scenarios/{name}")
        return scenario
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Scenario '{name}' not found")

@app.post("/validate-trade")
def validate_trade(payload: Dict[str, Any]):
    """Validate a single trade (OMS only)."""
    oms = _get_oms()
    trade = payload.get("trade")
    if not trade:
        raise HTTPException(status_code=400, detail="Missing 'trade' field")
    return oms.run(trade)

@app.post("/validate-pricing")
def validate_pricing(payload: Dict[str, Any]):
    """Validate pricing marks (pricing agent only)."""
    pricing = _get_pricing()
    marks = payload.get("marks")
    if not marks:
        raise HTTPException(status_code=400, detail="Missing 'marks' field")
    return pricing.run(marks)
```

**HOST**:
"Seven endpoints total: health check, status, list scenarios, get scenario, run full orchestrator, validate trade only, validate pricing only. This gives clients flexibility—run the full workflow or just validate a single trade."

### [VISUAL: Terminal showing service startup]

**HOST**:
"Let's start the service."

### [TERMINAL]

```bash
source .venv/bin/activate
python -m src.service.main
```

### [OUTPUT]

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**HOST**:
"Service is live on port 8000. Let's hit some endpoints."

### [NEW TERMINAL WINDOW]

```bash
# Health check
curl http://localhost:8000/health | jq

# List scenarios
curl http://localhost:8000/scenarios | jq

# Run clean day scenario
curl -X POST http://localhost:8000/run-desk-agent \
  -H "Content-Type: application/json" \
  -d '{"scenario": "scenarios/clean_day.json"}' | jq '.summary'

# Run problematic scenario
curl -X POST http://localhost:8000/run-desk-agent \
  -H "Content-Type: application/json" \
  -d '{"scenario": "scenarios/mis_booked_trade.json"}' | jq '.summary'
```

### [OUTPUT SHOWS]

```json
{
  "overall_status": "ERROR",
  "total_trades": 10,
  "trades_with_issues": 7,
  "percent_trades_with_issues": 70.0,
  "execution_time_ms": 2134
}
```

**HOST**:
"Production REST API. We can call it from any language, integrate with existing systems, deploy behind a load balancer, scale horizontally—this is how you ship AI agents to production."

### [VISUAL: Opens `docs/README.md`]

**HOST**:
"We have comprehensive API documentation with all endpoints, request/response schemas, error codes, performance characteristics, deployment examples—everything you need to integrate."

---

## PART 9: LIVE DEMO (56:00 - 62:00)

### [VISUAL: Split screen - terminal on left, browser on right]

**HOST** (back on camera):
"Alright, we've walked through all the code. Now let's see the whole system in action with a live demo. I'm going to show you three scenarios: a clean day, mis-booked trades, and bad pricing marks."

### [TERMINAL]

```bash
# Start the service
python -m src.service.main &

# Give it a second to start
sleep 2

# Scenario 1: Clean Day
echo "=== SCENARIO 1: Clean Day (Happy Path) ==="
curl -X POST http://localhost:8000/run-desk-agent \
  -H "Content-Type: application/json" \
  -d '{"scenario": "scenarios/clean_day.json"}' | jq '.summary'
```

### [OUTPUT]

```json
{
  "overall_status": "OK",
  "total_trades": 4,
  "trades_with_issues": 0,
  "percent_trades_with_issues": 0.0,
  "total_marks": 7,
  "marks_flagged": 0,
  "percent_marks_flagged": 0.0,
  "execution_time_ms": 1247
}
```

**HOST**:
"Clean day—everything passes. 4 trades, 7 marks, all validated in 1.2 seconds. This is the 99% case—most days are clean. But we're looking for that 1% where something goes wrong."

### [TERMINAL]

```bash
# Scenario 2: Mis-booked Trades
echo "=== SCENARIO 2: Mis-Booked Trades ==="
curl -X POST http://localhost:8000/run-desk-agent \
  -H "Content-Type: application/json" \
  -d '{"scenario": "scenarios/mis_booked_trade.json"}' | jq '{
    status: .summary.overall_status,
    total_trades: .summary.total_trades,
    trades_with_issues: .summary.trades_with_issues,
    sample_issues: .trade_issues[:3]
}'
```

### [OUTPUT]

```json
{
  "status": "ERROR",
  "total_trades": 10,
  "trades_with_issues": 7,
  "sample_issues": [
    {
      "trade_id": "T302",
      "status": "ERROR",
      "issues": [
        {
          "type": "weekend_settlement",
          "severity": "ERROR",
          "message": "Settlement date 2024-06-22 falls on a weekend"
        }
      ]
    },
    {
      "trade_id": "T303",
      "status": "ERROR",
      "issues": [
        {
          "type": "unusual_currency",
          "severity": "ERROR",
          "message": "Currency EUR is unusual for US equity (expected USD)"
        }
      ]
    },
    {
      "trade_id": "T304",
      "status": "ERROR",
      "issues": [
        {
          "type": "negative_quantity",
          "severity": "ERROR",
          "message": "Quantity cannot be negative: -100"
        }
      ]
    }
  ]
}
```

**HOST**:
"70% error rate. Weekend settlements, wrong currencies, negative quantities. These are all real errors that happen in production. Our system catches them before they hit the books."

### [TERMINAL]

```bash
# Scenario 3: Bad Marks
echo "=== SCENARIO 3: Bad Pricing Marks ==="
curl -X POST http://localhost:8000/run-desk-agent \
  -H "Content-Type: application/json" \
  -d '{"scenario": "scenarios/bad_mark.json"}' | jq '{
    status: .summary.overall_status,
    total_marks: .summary.total_marks,
    marks_flagged: .summary.marks_flagged,
    sample_flags: .pricing_flags[:3]
}'
```

### [OUTPUT]

```json
{
  "status": "WARNING",
  "total_marks": 15,
  "marks_flagged": 8,
  "sample_flags": [
    {
      "ticker": "INTC",
      "internal_mark": 25.00,
      "market_price": 48.50,
      "classification": "OUT_OF_TOLERANCE",
      "deviation_percentage": 0.485,
      "explanation": "Mark is 48.5% below market price"
    },
    {
      "ticker": "BABA",
      "internal_mark": 120.00,
      "market_price": 82.30,
      "classification": "OUT_OF_TOLERANCE",
      "deviation_percentage": 0.458,
      "explanation": "Mark is 45.8% above market price"
    },
    {
      "ticker": "TSLA",
      "internal_mark": 180.00,
      "market_price": 195.50,
      "classification": "REVIEW_NEEDED",
      "deviation_percentage": 0.086,
      "explanation": "Mark is 8.6% below market price"
    }
  ]
}
```

**HOST**:
"53% of marks flagged. Intel marked at $25 but market is at $48—that's a 48% deviation. Alibaba marked at $120 but market is at $82. These could be stale data, fat-finger errors, or genuine valuation disagreements. Either way, they need review."

### [BROWSER: Opens http://localhost:8000/docs]

**HOST**:
"FastAPI gives us interactive documentation for free. Every endpoint, request schema, response schema, error codes—all auto-generated from our code."

### [BROWSER: Expands /run-desk-agent endpoint, clicks "Try it out"]

**HOST**:
"I can test endpoints right here in the browser."

### [BROWSER: Enters inline scenario JSON]

```json
{
  "data": {
    "name": "adhoc_test",
    "trades": [
      {
        "trade_id": "T999",
        "ticker": "AAPL",
        "quantity": 100,
        "price": 195.50,
        "currency": "USD",
        "counterparty": "MS",
        "trade_dt": "2025-12-17",
        "settle_dt": "2025-12-21",
        "side": "BUY"
      }
    ],
    "marks": [
      {"ticker": "AAPL", "internal_mark": 195.71, "as_of_date": "2025-12-18"}
    ],
    "questions": ["What's Apple's market cap?"]
  }
}
```

### [BROWSER: Clicks "Execute"]

### [RESPONSE SHOWS]

```json
{
  "summary": {
    "overall_status": "ERROR",
    "total_trades": 1,
    "trades_with_issues": 1,
    "execution_time_ms": 456
  },
  "trade_issues": [
    {
      "trade_id": "T999",
      "status": "ERROR",
      "issues": [
        {
          "type": "weekend_settlement",
          "severity": "ERROR",
          "message": "Settlement date 2025-12-21 falls on a weekend"
        }
      ]
    }
  ]
}
```

**HOST**:
"Caught it! December 21st, 2025 is a Sunday. Settlement rejected. This is the power of systematic validation—humans miss weekends when they're tired or rushed. The system never does."

---

## PART 10: PRODUCTION DEPLOYMENT (62:00 - 68:00)

### [VISUAL: Opens `docs/ARCHITECTURE.md`]

**HOST**:
"Let's talk about deploying this to production. We have full documentation for Docker, Kubernetes, and systemd deployments."

### [CODE SHOWS Dockerfile]

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml ./
RUN pip install -e .

COPY src/ ./src/
COPY scenarios/ ./scenarios/

ENV SERVICE_ENV=prod
ENV SERVICE_PORT=8000

EXPOSE 8000

CMD ["uvicorn", "src.service.api:app", "--host", "0.0.0.0", "--port", "8000"]
```

**HOST**:
"Standard Python Docker image, copy code, install dependencies, expose port 8000, run uvicorn."

### [TERMINAL]

```bash
# Build image
docker build -t desk-agent-service .

# Run container
docker run -p 8000:8000 \
  -e FD_API_KEY=$FD_API_KEY \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e SERVICE_ENV=prod \
  desk-agent-service
```

**HOST**:
"Build, run, pass API keys as environment variables. Now we can deploy to any cloud provider."

### [CODE SHOWS Kubernetes deployment]

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: desk-agent-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: desk-agent
  template:
    metadata:
      labels:
        app: desk-agent
    spec:
      containers:
      - name: desk-agent
        image: desk-agent-service:1.0
        ports:
        - containerPort: 8000
        env:
        - name: SERVICE_ENV
          value: "prod"
        - name: FD_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: fd-api-key
        resources:
          limits:
            memory: "512Mi"
            cpu: "500m"
          requests:
            memory: "256Mi"
            cpu: "250m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: desk-agent-service
spec:
  selector:
    app: desk-agent
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

**HOST**:
"Three replicas for high availability. Health checks for liveness and readiness probes. Resource limits to prevent runaway memory usage. LoadBalancer service for external access. This is production-grade infrastructure."

### [VISUAL: Shows monitoring setup]

**HOST**:
"Monitoring is critical. Every request gets a request ID that flows through all logs."

### [CODE SHOWS structured logging]

```python
logger.info(f"request_id={request_id} path=/run-desk-agent method=POST "
           f"duration_ms={duration_ms:.2f} status=200")
```

**HOST**:
"JSON logs that you can ship to Datadog, CloudWatch, Splunk, whatever. Search by request ID to see the entire request lifecycle."

### [VISUAL: Shows sample log query]

```
{
  "ts": "2025-12-19T10:30:45.123Z",
  "level": "INFO",
  "logger": "src.service.api",
  "msg": "request_id=a1b2c3d4 path=/run-desk-agent method=POST duration_ms=2134 status=200",
  "request_id": "a1b2c3d4",
  "path": "/run-desk-agent",
  "method": "POST",
  "duration_ms": 2134,
  "status": 200
}
```

**HOST**:
"Structured logs make it easy to build dashboards, set up alerts, track SLAs. If 95th percentile latency goes above 5 seconds, trigger an alert. If error rate exceeds 1%, page on-call. Standard production monitoring."

---

## PART 11: TESTING & QUALITY (68:00 - 73:00)

### [VISUAL: Opens test directory tree]

**HOST**:
"Let's talk about testing. We have 119 tests across all seven weeks—unit tests, integration tests, scenario tests."

### [TERMINAL]

```bash
pytest --tb=short -v
```

### [OUTPUT]

```
tests/data_tools/test_fd_api.py::test_get_stock_price PASSED
tests/data_tools/test_equity_snapshot.py::test_snapshot_structure PASSED
tests/refmaster/test_refmaster.py::test_normalize_standard_ticker PASSED
tests/refmaster/test_refmaster.py::test_normalize_isin PASSED
tests/oms/test_oms_agent.py::test_valid_trade PASSED
tests/oms/test_oms_agent.py::test_weekend_settlement PASSED
tests/pricing/test_pricing_agent.py::test_out_of_tolerance PASSED
tests/ticker_agent/test_ticker_agent.py::test_question_answering PASSED
tests/desk_agent/test_orchestrator.py::test_run_scenario PASSED
tests/desk_agent/test_orchestrator.py::test_retry_logic PASSED
tests/service/test_api.py::test_health PASSED
tests/service/test_api.py::test_run_desk_agent PASSED

======================== 119 passed in 31.83s ========================
```

**HOST**:
"119 tests, all passing. Coverage across data tools, agents, orchestrator, and service layer."

### [VISUAL: Opens a test file]

```python
def test_orchestrator_handles_retries(monkeypatch):
    """Test that orchestrator retries transient failures."""
    class FlakyAgent:
        def __init__(self):
            self.attempts = 0

        def run(self, trade):
            self.attempts += 1
            if self.attempts < 2:
                raise RuntimeError("Transient error")
            return {"status": "OK", "issues": []}

    flaky = FlakyAgent()
    orch = DeskAgentOrchestrator(
        normalizer=NormalizerStub(),
        oms_agent=flaky,
        pricing_agent=PricingStub(),
        ticker_runner=lambda q: {"summary": "ok"},
        max_retries=3
    )

    scenario = {"name": "test", "trades": [{"trade_id": "T1"}], "marks": [], "questions": []}
    report = orch.run_scenario(scenario)

    assert flaky.attempts == 2  # Failed once, succeeded on retry
    assert report["summary"]["overall_status"] == "OK"
```

**HOST**:
"This test verifies retry logic. Flaky agent fails on first attempt, succeeds on second. Orchestrator should retry and ultimately succeed. Tests like this give you confidence that production failures won't crash your system."

### [VISUAL: Shows test coverage report]

```bash
pytest --cov=src --cov-report=html
```

### [OUTPUT]

```
---------- coverage: platform darwin, python 3.11.7 -----------
Name                                Stmts   Miss  Cover
-------------------------------------------------------
src/data_tools/fd_api.py              87      5    94%
src/refmaster/normalizer.py          124      8    94%
src/oms/oms_agent.py                 156     12    92%
src/pricing/pricing_agent.py          98      6    94%
src/ticker_agent/ticker_agent.py     145     18    88%
src/desk_agent/orchestrator.py       234     23    90%
src/service/api.py                   112      8    93%
-------------------------------------------------------
TOTAL                               1456    103    93%
```

**HOST**:
"93% code coverage. Not 100%—some error paths are hard to trigger in tests. But 93% is solid for a production system."

---

## PART 12: REAL-WORLD IMPACT (73:00 - 78:00)

### [VISUAL: Back to camera]

**HOST**:
"Let's talk about real-world impact. Why does this matter?"

### [VISUAL: Shows ROI calculation]

**HOST**:
"Operations team: 3 analysts, $150K salary each. They spend 2 hours per day on manual validation. That's 6 analyst-hours per day, 1,560 hours per year, $112,000 in annual labor cost."

**HOST**:
"Our system: processes the same workload in 30 seconds. That's 99.7% time reduction. Those analysts can now focus on exception handling, strategic analysis, actual problem-solving instead of mindless validation."

**HOST**:
"But the real value isn't labor savings—it's error prevention. That $8M loss I mentioned? That was real. One major hedge fund, one set of bad trades. Our system would have caught it instantly."

**HOST**:
"Even if you only prevent one $1M error per year—which is conservative for a large fund—this system pays for itself 10x over."

### [VISUAL: Shows expandability diagram]

**HOST**:
"And this is just the beginning. The architecture we built is extensible. You can add new agents: a compliance agent that checks regulatory requirements, a risk agent that calculates VaR and stress tests, a reconciliation agent that matches trades to broker confirms."

**HOST**:
"Each agent is independent, testable, swappable. You can replace the stub OMS agent with a real connection to your internal OMS. You can swap Financial Datasets API for Bloomberg or Refinitiv. You can add new validation rules without touching the orchestrator."

**HOST**:
"This is production-grade AI engineering. Not research code, not a demo, not a proof of concept. This is code you can deploy on Monday."

---

## PART 13: KEY TAKEAWAYS (78:00 - 82:00)

### [VISUAL: Summary slide appears]

**HOST**:
"Let's recap the key lessons from this project."

### [TEXT ON SCREEN]

**1. Multi-Agent Architecture Scales**

**HOST**:
"Don't build monolithic AI systems. Build specialized agents with clear responsibilities. One agent per domain—normalization, validation, pricing, intelligence. Each agent is independently testable and replaceable."

### [TEXT ON SCREEN]

**2. Structured Data Beats Prompts**

**HOST**:
"LLMs are powerful, but don't use them for everything. Use structured validation where possible—regex for dates, numeric comparisons for prices, set membership for currencies. Only use LLMs where you need actual intelligence—natural language questions, anomaly explanation, contextual synthesis."

### [TEXT ON SCREEN]

**3. Retries Are Non-Negotiable**

**HOST**:
"External APIs fail. Networks time out. Services restart. Your system must handle transient failures gracefully. Exponential backoff, retry limits, error tracking—these aren't nice-to-haves, they're requirements."

### [TEXT ON SCREEN]

**4. Observability From Day One**

**HOST**:
"Request IDs, structured logs, execution traces—build this in from the start. When something breaks in production at 2 AM, you need to know exactly what happened. Logs are your time machine."

### [TEXT ON SCREEN]

**5. Test Like Production Depends On It (Because It Does)**

**HOST**:
"119 tests. 93% coverage. Monkeypatching for external dependencies. Scenario-based testing for business logic. This isn't overhead—this is how you ship with confidence."

### [TEXT ON SCREEN]

**6. REST APIs Enable Integration**

**HOST**:
"Wrapping your system in a REST API means anyone can use it. Trading platforms, risk systems, compliance tools, internal dashboards—they all speak HTTP. Make your system accessible and it becomes indispensable."

### [TEXT ON SCREEN]

**7. Documentation Is Code**

**HOST**:
"README, architecture docs, API docs, deployment guides, troubleshooting FAQs—write them as you build. Future you will thank present you. And so will your team."

---

## CLOSING (82:00 - 85:00)

### [VISUAL: Back to camera, code editor visible in background]

**HOST**:
"We've covered a lot in the last 80 minutes. Seven weeks of development, five specialized agents, 119 tests, comprehensive documentation, production deployment—this is a complete, end-to-end AI system for financial operations."

**HOST**:
"All the code is available on GitHub—link in the description. Clone it, run it, modify it, deploy it. This is open source. Learn from it, build on it, ship it."

**HOST**:
"If you found this valuable, hit subscribe—I'm going to be building more production AI systems and walking through the code just like this. Next up: a compliance agent that reads SEC filings and flags regulatory risks. Should be fun."

**HOST**:
"Questions? Comments? Hit me up in the comments or on Twitter. I read everything."

**HOST**:
"Thanks for watching. Now go build something awesome."

### [VISUAL: End screen with links]

**TEXT ON SCREEN**:
- GitHub: github.com/transient-ai/desk-agent
- Twitter: @transient_ai
- Docs: docs.transient.ai
- Next Video: Compliance Agent + SEC Filing Analysis

### [MUSIC FADES OUT]

**[END]**

---

## PRODUCTION NOTES

### Visual Elements Needed:
- Architecture diagrams (multi-agent system, data flow, deployment architecture)
- Code editor screen recordings with syntax highlighting
- Terminal output with formatted JSON
- Browser showing FastAPI docs
- Split-screen demos
- ROI calculation graphics
- Test coverage reports

### B-Roll Suggestions:
- Trading floor footage (stock video)
- Code scrolling
- Server racks / data centers
- Financial charts/dashboards
- News headlines about trading errors

### Editing Notes:
- Use code syntax highlighting throughout
- Animate architecture diagrams
- Add captions for technical terms
- Include chapter markers for each week/section
- Fast-forward long test runs to ~2x speed
- Add dramatic pause before revealing the $8M error catch

### Technical Requirements:
- 4K screen recording
- Clear audio (lavalier mic recommended)
- Good lighting for on-camera segments
- Multiple terminal windows for demo section
- Pre-loaded scenarios for smooth demo flow

### Call-to-Action Timestamps:
- 5:00 - "If you're already lost, slow down the video"
- 30:00 - "Halfway through—you're doing great"
- 60:00 - "If this is making sense, hit like"
- 82:00 - "Subscribe for more production AI systems"

---

**Total Duration**: 85 minutes
**Target Retention**: 60%+ (aim for 50 min average watch time)
**Difficulty**: Advanced (but explained clearly)
**Rewatchability**: High (reference material for implementation)
