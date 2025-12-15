# Data Tools Deliverables

## Artifacts
- [ ] Create the `data_tools/` package scaffold (modules: `__init__.py`, `fd_api.py`, `qa_builder.py`, `schemas.py`, `examples/`, `tests/`).
- [ ] Implement `fd_api.get_equity_snapshot` returning the specified snapshot JSON (ticker, price, 1D/5D returns, market cap, sector, source).
- [ ] Implement `qa_builder.generate_qa_from_file(path)` that extracts filing content and emits Q&A records.
- [ ] Add CLI entry point `python -m data_tools.fd_api <ticker>` that prints the snapshot summary and persists JSON to `examples/snapshot_output.json`.
- [ ] Populate `examples/snapshot_output.json` with snapshots for at least three tickers.
- [ ] Produce `examples/sample_qa.jsonl` containing representative question/answer rows from filings.
- [ ] Set up project environment: virtualenv, `requirements.txt`, and `.env` with the FinancialDatasets API key plus required config.
- [ ] Author README covering objectives, inputs/outputs, CLI usage, sample workflows, and how future agents will call these tools; add docstrings where logic is non-obvious.

## Non-Artifacts (Evaluation Checklist)
- [ ] Snapshot outputs always match the schema (ticker, price, return_1d, return_5d, market_cap, sector, source) with deterministic formatting.
- [ ] API or parsing failures surface as explicit errors (no silent defaults) so downstream agents can decide how to recover.
- [ ] QA generation produces a clean `.jsonl` file without malformed entries; unexpected filing structures are handled or reported consistently.
- [ ] README and inline docs clearly explain setup, execution steps, and integration touchpoints for other teams.
- [ ] Tests or documented manual validation steps confirm schema adherence and core behavior for both snapshot and QA paths.
