# Ticker Agent (Week 2)

Lightweight ticker Q&A helper that classifies a question, resolves a ticker, fetches a snapshot via `data_tools.fd_api.get_equity_snapshot`, and returns structured intent/summary/metrics. LLM classification is optional; heuristics are always available as fallback.

## Supported intents
- `price_performance_summary`: price, 1D/5D returns.
- `financials_revenue_summary`: price, market cap, sector/industry.
- `dividend_overview`: placeholder fields (`dividend_yield`, `next_ex_date` = None).
- `volatility_comparison_convertible`: uses 5D return as proxy.
- `generic_unhandled`: default when no pattern matches.

## Usage
```python
from src.ticker_agent.ticker_agent import run

resp = run("How is AAPL performing?")
# resp -> {intent, summary, metrics, source, system_prompt, tools_prompt}
```

## Configuration
- Env vars (loaded via `load_dotenv()`): `LLM_MODEL` or `OPENAI_MODEL` to enable LLM classifier; otherwise heuristics are used.
- Market data is always fetched via `data_tools.fd_api.get_equity_snapshot`; no direct API keys configured here.

## Invocation by other agents
- Desk/OMS/Pricing should import `ticker_agent.run(question)` and consume the returned dict. Do not call market data directly from here; rely on `data_tools`.

## Files
- `ticker_agent.py`: core API and heuristics.
- `classifier.py`: optional LLM classifier (expects `(intent, confidence, slots)`).
- `prompts.py`: system/tools prompt strings.
- `intents_data.json` (+ loader/builder scripts): intent definitions for classifier.
