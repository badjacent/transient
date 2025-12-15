# Demo Script (Week 7)

## Timing (10–12 minutes)
1. **Problem framing (1 min):** Booking/pricing errors, manual QA, audit/compliance pressure.
2. **Architecture tour (1–2 min):** FastAPI → Desk Agent orchestrator → OMS/Pricing/Refmaster/Ticker/Market data.
3. **Health/readiness (1 min):** `GET /health` showing version, env, scenarios path status.
4. **Clean run (2 min):** `POST /run-desk-agent` with `scenarios/clean_day.json`; highlight `summary.overall_status=OK`, narrative, zero issues.
5. **Issue run (3 min):** `scenarios/mis_booked_trade.json` and `bad_mark.json`; walk through `trade_issues`, `pricing_flags`, market context, summary percentages.
6. **Value (2 min):** Faster checks, fewer breaks, audit-friendly JSON with `X-Request-ID`, configurable tolerances/retries, extensible agents.
7. **Q&A (1–2 min):** Latency targets, logging/metrics, integration options (direct REST, SDK), security/cors/env separation.

## Backups
- If market data or scenarios unavailable, show `/scenarios` listing and `/validate-trade` for direct OMS QA.
- Keep `logs/service.log` handy to show request IDs and structured logging.
