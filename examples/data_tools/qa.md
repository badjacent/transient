# Q&A Generation from 10-K Filings

This document describes how `qa.json` was generated from 10-K HTML filings.

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

from src.data_tools.qa_builder import generate_qa_pairs

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

# Process each filing
results = []

for filing in filings:
    print(f"\nProcessing {filing['company']} {filing['year']} 10-K: {filing['filename']}")
    
    try:
        # Generate Q&A pairs using ticker and year (this works with SEC filings)
        qa_pairs = generate_qa_pairs(
            ticker=filing['ticker'],
            year=filing['year'],
            max_questions=50,  # Reasonable number for example
            use_mda_only=True,  # Focus on MD&A section
            api_key=openai_key
        )
        
        # Add metadata and Q&A pairs to results
        result = {
            "filename": filing['filename'],
            "company": filing['company'],
            "year": filing['year'],
            "source_file": filing['path'],
            "num_qa_pairs": len(qa_pairs),
            "qa_pairs": [qa_pair.model_dump() for qa_pair in qa_pairs]
        }
        results.append(result)
        
        print(f"  Generated {len(qa_pairs)} Q&A pairs")
        
    except Exception as e:
        print(f"  Error processing {filing['filename']}: {e}")
        # Add error result
        result = {
            "filename": filing['filename'],
            "company": filing['company'],
            "year": filing['year'],
            "source_file": filing['path'],
            "error": str(e),
            "num_qa_pairs": 0,
            "qa_pairs": []
        }
        results.append(result)

# Write results to JSON file
output_file = "examples/data_tools/qa.json"
output_path = Path(output_file)
output_path.parent.mkdir(parents=True, exist_ok=True)

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\nResults written to {output_file}")
print(f"Total filings processed: {len(filings)}")
print(f"Total Q&A pairs: {sum(r['num_qa_pairs'] for r in results)}")
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

The `qa.json` file contains an array of filing results. Each result includes:

- `filename`: Original HTML file name
- `company`: Company name
- `year`: Filing year
- `source_file`: Local file path
- `num_qa_pairs`: Number of Q&A pairs generated
- `qa_pairs`: Array of Q&A objects, each containing:
  - `question`: The generated question
  - `answer`: The answer extracted from the filing
  - `context`: (Optional) Context from the filing that supports the answer

## Dependencies

- `financial-datasets` library for parsing SEC filings and generating Q&A pairs
- `openai` (via financial-datasets) for LLM-based Q&A generation
- OpenAI API key required (set in `.env` file as `OPENAI_API_KEY`)

## Notes

- The Q&A generation uses GPT-4-turbo model by default
- Only the MD&A (Management's Discussion and Analysis) section (Item 7) was used
- The generation process can take several minutes per filing depending on the number of questions requested

