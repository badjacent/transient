# Artifacts (data/code/tests/docs)
- [ ] `pricing/marks.csv`: synthetic EOD mark file with ~50 instruments including `instrument_id`, `internal_mark`, `as_of_date`, and optional notes.
- [ ] `pricing/tolerances.yaml`: configuration for per-asset or global tolerances (e.g., OK, REVIEW_NEEDED, OUT_OF_TOLERANCE thresholds).
- [ ] `pricing/market_normalizer.py` (or similar): loader that enriches marks with FD close prices and standardized identifiers; handles missing data gracefully.
- [ ] `pricing/pricing_agent.py`: orchestrates normalization, tolerance classification, and explanation generation; returns structured results (status per instrument plus aggregated summary).
- [ ] `examples/pricing_report.md`: sample audit-friendly report illustrating outputs for the production-pressure scenario.
- [ ] `tests/pricing/test_pricing_agent.py`: unit/integration tests covering mark loading, tolerance classification (OK/REVIEW_NEEDED/OUT_OF_TOLERANCE), missing data paths, and aggregated explanation output.
- [ ] `pricing/README.md`: Week 5 documentation describing objectives, data sources, tolerances, API/CLI usage, config knobs, and how to interpret the report.

# Non-Artifacts
- [ ] Scenario guidance: document (in README or scenarios) how to answer the auditor’s “12 diverged marks” request, including workflow/timing expectations and how to customize tolerances for rapid EOD validation.
