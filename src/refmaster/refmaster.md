# Refmaster Identifiers (Note)

We don’t have a licensed reference-data source for identifiers (CUSIP/ISIN/CIK), so refmaster uses a best-effort approach:

- CIK: fetched from the SEC’s public ticker→CIK mapping when available.
- CUSIP/ISIN: attempted via FinancialModelingPrep (if FMP_API_KEY is set); otherwise generated deterministically (synthetic) to satisfy schema shape.
- Exchange: heuristically assigned (4-letter symbols → NASDAQ, <4 → NYSE) when not provided.

Because of these constraints, the identifiers in `refmaster_data.json` should be treated as placeholders for experimentation, not production-grade reference data.*** End Patch
