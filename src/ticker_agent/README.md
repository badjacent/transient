# Ticker Agent (Week 2)

Lightweight ticker Q&A helper that classifies a question, resolves a ticker, fetches a snapshot via `data_tools.fd_api.get_equity_snapshot`, and returns structured intent/summary/metrics. LLM classification is optional; heuristics are always available as fallback.

## Supported intents
See `src/ticker_agent/intents.md` for the current intent list, metrics schema, and templates.

## Usage
```python
from src.ticker_agent.ticker_agent import run, run_many

resp = run("How is AAPL performing?")
batch = run_many(["AAPL performance", "MSFT news sentiment?"])
# resp -> {intent, summary, metrics, source, system_prompt, tools_prompt}
```

## Configuration
- Env vars (loaded via `load_dotenv()`): `LLM_MODEL` or `OPENAI_MODEL` to enable LLM classifier; otherwise heuristics are used.
- Market data is always fetched via `data_tools.fd_api.get_equity_snapshot`; no direct API keys configured here.

## Invocation by other agents
- Desk/OMS/Pricing should import `ticker_agent.run(question)` (or `run_many([...])`) and consume the returned dict. Do not call market data directly from here; rely on `data_tools`.

## Notes
- Heuristic ticker parsing handles “AAPL US”, “AAPL.OQ”, uppercase tokens.
- Snapshots cached via LRU to reduce repeated market data calls.

## Files
- `ticker_agent.py`: core API and heuristics.
- `classifier.py`: optional LLM classifier (expects `(intent, confidence, slots)`).
- `prompts.py`: system/tools prompt strings.
- `intents_data.json` (+ loader/builder scripts): intent definitions for classifier.
