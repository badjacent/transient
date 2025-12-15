"""Extract Q&A pairs and structured fundamentals from 10-K filings."""

import json
import os
import re
from io import StringIO
from pathlib import Path
from typing import List, Optional

import pandas as pd
from dotenv import load_dotenv
from financial_datasets.generator import DatasetGenerator
from financial_datasets.parser import FilingItem, FilingParser

from src.data_tools.schemas import QAPair

# Load environment variables
load_dotenv()


def extract_mda_section(ticker: str, year: int) -> Optional[str]:
    """Return Item 7 (MD&A) text; raise with context on parser/network failures."""
    parser = FilingParser()
    try:
        items = parser.get_10K_items(
            ticker=ticker,
            year=year,
            item_names=[FilingItem.ITEM_7]
        )
        if items and len(items) > 0:
            return items[0]
        return None
    except Exception as exc:
        raise RuntimeError(f"Failed to extract MD&A for {ticker} {year}") from exc


def extract_full_10k(ticker: str, year: int) -> Optional[str]:
    """Return concatenated 10-K text; raise with context on parser/network failures."""
    parser = FilingParser()
    try:
        items = parser.get_10K_items(
            ticker=ticker,
            year=year,
            item_names=[]
        )
        if items:
            return "\n\n".join(items)
        return None
    except Exception as exc:
        raise RuntimeError(f"Failed to extract 10-K for {ticker} {year}") from exc


def get_10k_items(ticker: str, year: int, item_names: Optional[List[str]] = None) -> List[str]:
    """
    Return the raw HTML items for a given 10-K.

    Args:
        ticker: Stock ticker.
        year: Filing year.
        item_names: Optional list of item identifiers to filter (defaults to full filing).

    Returns:
        List of HTML strings for the requested sections.
    """
    parser = FilingParser()
    try:
        return parser.get_10K_items(
            ticker=ticker,
            year=year,
            item_names=item_names or []
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch 10-K items for {ticker} {year}") from exc


def _get_openai_api_key() -> str:
    """Return OpenAI API key from env or raise."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in environment variables. "
            "Please set it in your .env file."
        )
    return api_key


def _flatten_dataset(dataset) -> List[QAPair]:
    """Normalize generator output; raise on unexpected shapes instead of silently dropping."""
    qa_pairs: List[QAPair] = []
    if not hasattr(dataset, "__iter__"):
        raise ValueError("Dataset is not iterable; cannot extract Q&A pairs.")

    for item in dataset:
        if isinstance(item, tuple) and len(item) == 2 and item[0] == "items":
            dataset_items = item[1]
            for dataset_item in dataset_items:
                if hasattr(dataset_item, "question") and hasattr(dataset_item, "answer"):
                    qa_pair = {"question": dataset_item.question, "answer": dataset_item.answer}
                    if getattr(dataset_item, "context", None):
                        qa_pair["context"] = dataset_item.context
                    qa_pairs.append(QAPair(**qa_pair))
                else:
                    raise ValueError("Dataset item missing question/answer attributes.")
        elif isinstance(item, dict):
            if "question" in item and "answer" in item:
                qa_pairs.append(
                    QAPair(question=item["question"], answer=item["answer"], context=item.get("context"))
                )
            else:
                raise ValueError("Dataset dict missing question/answer keys.")
        elif hasattr(item, "question") and hasattr(item, "answer"):
            qa_pair = {"question": item.question, "answer": item.answer}
            if getattr(item, "context", None):
                qa_pair["context"] = item.context
            qa_pairs.append(QAPair(**qa_pair))
        else:
            raise ValueError(f"Unexpected dataset item shape: {type(item)}")

    return qa_pairs


def _parse_numeric(value) -> Optional[float]:
    """Convert textual cell values to floats."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text or text in {"-", "—", "N/A"}:
        return None
    text = text.replace(",", "").replace("$", "")
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"
    try:
        return float(text)
    except ValueError:
        return None


YEAR_PATTERN = re.compile(r"(20\d{2})")


def _extract_revenue_from_html(html: str, max_years: int = 4) -> List[dict]:
    """Parse HTML tables for revenue rows and return [{year, value}]."""
    try:
        tables = pd.read_html(StringIO(html))
    except ValueError:
        return []

    for table in tables:
        if table.empty or table.shape[1] < 2:
            continue
        table = table.dropna(how="all", axis=1)
        if table.empty or table.shape[1] < 2:
            continue

        first_col = table.columns[0]
        for _, row in table.iterrows():
            label = str(row.get(first_col, "")).lower()
            if "revenue" not in label:
                continue
            if "total" not in label and "net" not in label and not label.startswith("revenue"):
                continue

            entries: List[dict] = []
            for col in table.columns[1:]:
                year_match = YEAR_PATTERN.search(str(col))
                if not year_match:
                    continue
                value = _parse_numeric(row.get(col))
                if value is None:
                    continue
                entries.append({"year": int(year_match.group(1)), "value": value})

            if entries:
                entries.sort(key=lambda item: item["year"], reverse=True)
                return entries[:max_years]

    return []


def extract_revenue_history(
    ticker: str,
    year: int,
    max_years: int = 4
) -> List[dict]:
    """
    Extract a normalized revenue series from a 10-K filing.

    Returns:
        List of dicts [{"year": 2024, "value": ...}, ...] sorted by year desc.
    """
    items = get_10k_items(ticker=ticker, year=year, item_names=[])
    if not items:
        raise RuntimeError(f"No 10-K content available for {ticker} {year}")

    for html in items:
        entries = _extract_revenue_from_html(html, max_years=max_years)
        if entries:
            return entries

    raise RuntimeError(f"Unable to locate revenue table for {ticker} {year}")


def generate_qa(
    ticker: str,
    year: int,
    max_questions: int = 100,
    use_mda_only: bool = True,
    model: str = "gpt-4-turbo",
    api_key: Optional[str] = None
) -> List[QAPair]:
    """Generate Q&A pairs from a 10-K using DatasetGenerator; surfaces errors instead of printing."""
    openai_key = api_key or _get_openai_api_key()
    generator = DatasetGenerator(
        model=model,
        api_key=openai_key
    )
    
    item_names = ["Item 7"] if use_mda_only else []
    
    dataset = generator.generate_from_10K(
        ticker=ticker,
        year=year,
        max_questions=max_questions,
        item_names=item_names
    )
    
    return _flatten_dataset(dataset)


def extract_qa_from_10k(
    ticker: str,
    year: int,
    output_file: str,
    use_mda_only: bool = True,
    max_questions: int = 100,
    model: str = "gpt-4-turbo",
    api_key: Optional[str] = None
) -> int:
    """
    Extract Q&A pairs from a 10-K filing and save to JSONL file.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "MSFT")
        year: Year of the 10-K filing
        output_file: Path to output JSONL file
        use_mda_only: If True, extract only from MD&A section; if False, use full 10-K
        max_questions: Maximum number of Q&A pairs to generate
        model: OpenAI model to use (default: "gpt-4-turbo")
        api_key: OpenAI API key. If None, uses OPENAI_API_KEY from .env file.
        
    Returns:
        Number of Q&A pairs extracted
        
    Raises:
        ValueError: If OPENAI_API_KEY is not set and api_key is not provided
    """
    # Generate Q&A pairs directly from 10-K using DatasetGenerator
    qa_pairs = generate_qa(
        ticker=ticker,
        year=year,
        max_questions=max_questions,
        use_mda_only=use_mda_only,
        model=model,
        api_key=api_key
    )
    
    if not qa_pairs:
        raise RuntimeError(f"No Q&A pairs generated for {ticker} {year}; check filings or generator output.")
    
    # Write to JSONL file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for qa_pair in qa_pairs:
            json_line = json.dumps(qa_pair.model_dump(), ensure_ascii=False)
            f.write(json_line + "\n")
    
    print(f"Extracted {len(qa_pairs)} Q&A pairs to {output_file}")
    return len(qa_pairs)


def generate_qa_from_file(
    file_url: str,
    max_questions: int = 100,
    model: str = "gpt-4-turbo",
    api_key: Optional[str] = None
) -> List[QAPair]:
    """Generate Q&A pairs from a 10-K HTML file/URL; surfaces errors."""
    from urllib.parse import urlparse
    
    openai_key = api_key or _get_openai_api_key()
    
    parsed = urlparse(file_url)
    local_path: Optional[str] = None
    if parsed.scheme == 'file':
        local_path = parsed.path
        if os.name == 'nt' and local_path.startswith('/') and len(local_path) > 3 and local_path[2] == ':':
            local_path = local_path[1:]
    elif not parsed.scheme:
        local_path = file_url
    
    if local_path is not None:
        path_obj = Path(local_path)
        if not path_obj.exists():
            raise FileNotFoundError(f"HTML file not found: {path_obj}")
        
        abs_path = str(path_obj.absolute())
        file_url = f"file://{abs_path}" if not abs_path.startswith('/') else f"file:///{abs_path}"
    
    generator = DatasetGenerator(
        model=model,
        api_key=openai_key
    )
    
    dataset = generator.generate_from_pdf(
        url=file_url,
        max_questions=max_questions
    )
    
    return _flatten_dataset(dataset)


def extract_qa_from_file(
    file_url: str,
    output_file: str,
    max_questions: int = 100,
    model: str = "gpt-4-turbo",
    api_key: Optional[str] = None
) -> int:
    """
    Extract Q&A pairs from a 10-K HTML file URL or local file and save to JSONL file.
    
    Supports:
    - HTTP/HTTPS URLs: "https://www.sec.gov/.../file.htm"
    - file:// URLs: "file:///path/to/file.htm" or "file:///C:/path/to/file.htm" (Windows)
    - Local file paths: "/path/to/file.htm" or "C:/path/to/file.htm" (Windows)
    
    Note: The library's generate_from_pdf() method works with HTML files from SEC EDGAR,
    even though the method name suggests PDFs.
    
    Args:
        file_url: URL or path to the 10-K HTML file
        output_file: Path to output JSONL file
        max_questions: Maximum number of Q&A pairs to generate
        model: OpenAI model to use (default: "gpt-4-turbo")
        api_key: OpenAI API key. If None, uses OPENAI_API_KEY from .env file.
        
    Returns:
        Number of Q&A pairs extracted
        
    Raises:
        ValueError: If OPENAI_API_KEY is not set and api_key is not provided
        FileNotFoundError: If local file path doesn't exist
    """
    # Generate Q&A pairs from HTML file
    qa_pairs = generate_qa_from_file(
        file_url=file_url,
        max_questions=max_questions,
        model=model,
        api_key=api_key
    )
    
    if not qa_pairs:
        raise RuntimeError(f"No Q&A pairs generated from file: {file_url}")
    
    # Write to JSONL file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for qa_pair in qa_pairs:
            json_line = json.dumps(qa_pair.model_dump(), ensure_ascii=False)
            f.write(json_line + "\n")
    
    print(f"Extracted {len(qa_pairs)} Q&A pairs to {output_file}")
    return len(qa_pairs)
