# Data Tools Cleanup TODO (implementation-ready)
Audience: implementation agent. Focus on tightening docs and surfacing failures; avoid masking errors.

## Docstring and Comment Cleanup
- [x] `fd_api.py`: condense docstrings for `get_price_snapshot`/`get_equity_snapshot` to essential behavior and risks; remove inline comments that narrate obvious steps; rely on models for return structure.
- [x] `qa_builder.py`: replace repeated helper docstrings with a concise module-level note; trim inline comments in dataset-flattening loops; keep only a brief note where behavior is non-obvious.
- [x] `schemas.py`: no changes needed; verify brevity is retained.

## Surface Failures Instead of Masking
- [x] `fd_api.py::get_company_facts`: on non-200 responses, stop returning “Unknown”/0 defaults; raise or return structured error objects so callers can act on auth/404/server failures.
- [x] `fd_api.py::get_price_snapshot`: ensure returned dates reflect actual market data date (not just requested date); avoid defaulting missing returns to 1.0—signal incomplete data via None/exception/flag.
- [x] `qa_builder.py::extract_mda_section` / `extract_full_10k`: stop swallowing all exceptions and printing; return structured error or re-raise with context so parser/network/auth issues are visible upstream.

## Deduplicate and Validate Dataset Flattening
- [x] `qa_builder.py`: consolidate dataset-flattening loops into a single helper that validates item shapes; if unexpected shapes are encountered, emit an explicit error/log rather than silently dropping to empty lists.

## Testing/Validation
- [x] Add/update tests to cover: non-200 fact fetch handling, price snapshot date/returns when data is missing, parser errors surfacing from QA builder, and error on unexpected dataset shapes.
