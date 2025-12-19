# Pricing Performance Notes

- Current caching: per-ticker/as-of in MarketNormalizer._cache; avoids repeated fetches within a run.
- Retries: configured via PRICING_RETRY_COUNT/PRICING_RETRY_BACKOFF_MS.
- Parallel fetch: set PRICING_MAX_WORKERS>1 to enable threaded market fetch/enrichment.
- Metrics logging: JSONL if PRICING_METRICS_LOG is set (counts, duration_ms, deviations).
- Remaining work: profile with real APIs, tune max_workers vs rate limits, and ensure <30s for ~50 marks.
