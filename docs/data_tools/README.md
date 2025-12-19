# Q&A Generation from 10-K Filings

This document describes how `sample_qa.jsonl` was generated from 10-K HTML filings.

## Source Files

The following 10-K filings were processed:

1. **Tesla 10-K (2020)**

   - Filename: `tsla-10k_20201231.htm`
   - Source: https://www.sec.gov/Archives/edgar/data/1318605/000156459021004599/tsla-10k_20201231.htm
   - Local path: `examples/data_tools/filings/tsla-10k_20201231.htm`

2. **Apple 10-K (2023)**
   - Filename: `aapl-20230930.htm`
   - Source: https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm
   - Local path: `examples/data_tools/filings/aapl-20230930.htm`

## Code Used to Generate Q&A Pairs

The following Python script was used to generate the Q&A pairs:

```python
"""Process 10-K filings and generate Q&A pairs."""

import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables first (before importing qa_builder)
load_dotenv()

from src.data_tools.qa_builder import generate_qa

# Get OpenAI API key
openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    raise ValueError("OPENAI_API_KEY not set in environment")

# Define the filings to process
filings = [
    {
        "filename": "tsla-10k_20201231.htm",
        "company": "Tesla",
        "ticker": "TSLA",
        "year": 2020,
        "path": "examples/data_tools/filings/tsla-10k_20201231.htm",
        "url": "https://www.sec.gov/Archives/edgar/data/1318605/000156459021004599/tsla-10k_20201231.htm"
    },
    {
        "filename": "aapl-20230930.htm",
        "company": "Apple",
        "ticker": "AAPL",
        "year": 2023,
        "path": "examples/data_tools/filings/aapl-20230930.htm",
        "url": "https://www.sec.gov/Archives/edgar/data/320193/000032019323000106/aapl-20230930.htm"
    }
]

# Where we will write JSON Lines (one QA pair per line)
output_path = Path("examples/data_tools/sample_qa.jsonl")
output_path.parent.mkdir(parents=True, exist_ok=True)

with output_path.open("w", encoding="utf-8") as fh:
    for filing in filings:
        print(f"\nProcessing {filing['company']} {filing['year']} 10-K: {filing['filename']}")
        abs_path = Path(filing["path"]).resolve()

        try:
            qa_pairs = generate_qa(
                ticker=filing["ticker"],
                year=filing["year"],
                max_questions=50,
                use_mda_only=True,
                api_key=openai_key
            )
            print(f"  Generated {len(qa_pairs)} Q&A pairs")
        except Exception as exc:
            print(f"  Error processing {filing['filename']}: {exc}")
            continue

        for qa_pair in qa_pairs:
            record = {
                "company": filing["company"],
                "year": filing["year"],
                "source_file": str(abs_path),
                **qa_pair.model_dump(),
            }
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"\nResults written to {output_path}")
```

## Execution

The script was run using:

```bash
uv run python3 process_filings.py
```

## Results

- **Tesla 2020 10-K**: 48 Q&A pairs generated
- **Apple 2023 10-K**: 45 Q&A pairs generated
- **Total**: 93 Q&A pairs

## Output Format

The `sample_qa.jsonl` file contains one JSON object per line with:

- `company`: Company name
- `year`: Filing year
- `source_file`: Absolute path to the HTML file or URL used by the generator
- `question`: Generated question
- `answer`: Model answer grounded in the filing
- `context`: Optional supporting excerpt when provided by the generator

## Dependencies

- `financial-datasets` library for parsing SEC filings and generating Q&A pairs
- `openai` (via financial-datasets) for LLM-based Q&A generation
- OpenAI API key required (set in `.env` file as `OPENAI_API_KEY`)

## Notes

- The Q&A generation uses GPT-4-turbo model by default
- Only the MD&A (Management's Discussion and Analysis) section (Item 7) was used
- The generation process can take several minutes per filing depending on the number of questions requested

## Data Quality & Source Assumptions

- `financialdatasets.ai` does **not** adjust prices for corporate actions (splits, dividends, symbol changes). Snapshot returns are raw ratios of the provided close prices, so dividend-heavy names will appear to gap lower on ex-div dates and split activity must be handled downstream.
- The service lacks canonical security identifiers (ISIN/CUSIP/FIGI) and only supports ticker strings, which introduces ambiguity for dual-listed or share-class variants.
- There is no trading-calendar awareness; the price fetch simply requests a rolling window and infers trading days from nonzero-volume rows. Holidays/halts are not automatically aligned to an exchange calendar.
- Neither the snapshot API nor the QA pipeline includes sentiment/news data. When a portfolio manager asks for "sentiment," the current Week 1 tools can only return fundamentals and return metrics; sentiment must be sourced elsewhere (or clearly noted as unavailable).
- Because these gaps mirror the `fd_api.py` "IMPORTANT ASSUMPTION" notes, downstream agents must validate prices against an authoritative feed before using them for risk, OMS, or pricing workflows.
