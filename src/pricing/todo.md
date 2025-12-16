# Artifacts
- [ ] `src/pricing/marks.csv`: synthetic EOD mark file (~50 instruments) with `instrument_id`, `ticker`, `internal_mark`, `as_of_date`, and optional `notes`.
- [ ] `config/pricing_tolerances.yaml`: config describing global/per-instrument tolerances (OK/review/out-of-tolerance thresholds, stale-day rules).
- [ ] `src/pricing/market_normalizer.py` (or equivalent): loads marks, pulls FD close prices, handles missing data, and classifies each mark (OK/REVIEW_NEEDED/OUT_OF_TOLERANCE/NO_MARKET_DATA/STALE_MARK) while attaching deviations and metadata.
- [ ] `src/pricing/pricing_agent.py`: orchestrates mark loading, normalization, classification, and explanation/report generation; emits structured results and optional Markdown/JSON report.
- [ ] `examples/pricing_report.md`: sample auditor-friendly report showing the agent output for the production-pressure scenario (12 divergent marks).
- [ ] `tests/pricing/test_pricing_agent.py`: unit/integration tests covering tolerance loading, market fetch fallbacks, classification logic, explanation text, and report aggregation.
- [ ] `src/pricing/README.md`: documentation covering objectives, schema, config knobs, CLI/API usage, report format, and instructions for answering auditor requests.

# Non-Artifacts
- [ ] Scenario guidance: document (README or report intro) how to respond when auditors flag ∼12 divergent marks—include workflow/timing expectations and how to adjust tolerances rapidly.
