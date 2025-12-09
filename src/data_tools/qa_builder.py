"""Extract Q&A pairs from 10-K HTML filings or MD&A sections using financial-datasets library."""

import json
import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from financial_datasets.parser import FilingParser, FilingItem
from financial_datasets.generator import DatasetGenerator
from src.data_tools.schemas import QAPair

# Load environment variables
load_dotenv()


def extract_mda_section(ticker: str, year: int) -> Optional[str]:
    """
    Extract the MD&A (Management's Discussion and Analysis) section from a 10-K filing.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "MSFT")
        year: Year of the 10-K filing
        
    Returns:
        The MD&A section text as a string, or None if not found
    """
    parser = FilingParser()
    try:
        # Item 7 is the MD&A section
        items = parser.get_10K_items(
            ticker=ticker,
            year=year,
            item_names=[FilingItem.ITEM_7]
        )
        if items and len(items) > 0:
            return items[0]
        return None
    except Exception as e:
        print(f"Error extracting MD&A for {ticker} {year}: {e}")
        return None


def extract_full_10k(ticker: str, year: int) -> Optional[str]:
    """
    Extract the full 10-K filing text.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "MSFT")
        year: Year of the 10-K filing
        
    Returns:
        The full 10-K text as a string, or None if not found
    """
    parser = FilingParser()
    try:
        # Get all items from the 10-K
        items = parser.get_10K_items(
            ticker=ticker,
            year=year,
            item_names=[]  # Empty list gets all items
        )
        if items:
            # Join all items into a single text
            return "\n\n".join(items)
        return None
    except Exception as e:
        print(f"Error extracting 10-K for {ticker} {year}: {e}")
        return None


def _get_openai_api_key() -> str:
    """
    Get OpenAI API key from environment variables.
    
    Returns:
        OpenAI API key string
        
    Raises:
        ValueError: If OPENAI_API_KEY is not set in environment
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError(
            "OPENAI_API_KEY not found in environment variables. "
            "Please set it in your .env file."
        )
    return api_key


def generate_qa_pairs(
    ticker: str,
    year: int,
    max_questions: int = 100,
    use_mda_only: bool = True,
    model: str = "gpt-4-turbo",
    api_key: Optional[str] = None
) -> List[QAPair]:
    """
    Generate Q&A pairs from a 10-K filing using DatasetGenerator.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "MSFT")
        year: Year of the 10-K filing
        max_questions: Maximum number of Q&A pairs to generate
        use_mda_only: If True, generate only from MD&A section (Item 7); if False, use full 10-K
        model: OpenAI model to use (default: "gpt-4-turbo")
        api_key: OpenAI API key. If None, uses OPENAI_API_KEY from .env file.
        
    Returns:
        List of QAPair models with question/answer (and optional context)
        
    Raises:
        ValueError: If OPENAI_API_KEY is not set and api_key is not provided
    """
    # Get API key from parameter or environment
    openai_key = api_key or _get_openai_api_key()
    
    # Initialize generator
    generator = DatasetGenerator(
        model=model,
        api_key=openai_key
    )
    
    # Generate from 10-K
    # If use_mda_only, specify Item 7 (MD&A section)
    item_names = ["Item 7"] if use_mda_only else []
    
    dataset = generator.generate_from_10K(
        ticker=ticker,
        year=year,
        max_questions=max_questions,
        item_names=item_names
    )
    
    # Convert dataset to list of Q&A pairs
    # The dataset returns a tuple: ('items', [DatasetItem(...), ...])
    # Each DatasetItem has question, answer, and context attributes
    qa_pairs: List[QAPair] = []
    if hasattr(dataset, '__iter__'):
        for item in dataset:
            # Dataset is a tuple: ('items', [DatasetItem(...)])
            if isinstance(item, tuple) and len(item) == 2 and item[0] == 'items':
                dataset_items = item[1]
                for dataset_item in dataset_items:
                    # DatasetItem has question, answer, and context attributes
                    if hasattr(dataset_item, 'question') and hasattr(dataset_item, 'answer'):
                        qa_pair = {
                            "question": dataset_item.question,
                            "answer": dataset_item.answer
                        }
                        # Include context if available
                        if hasattr(dataset_item, 'context') and dataset_item.context:
                            qa_pair["context"] = dataset_item.context
                        qa_pairs.append(QAPair(**qa_pair))
            elif isinstance(item, dict):
                # If it's already a dict with question/answer, use it
                if "question" in item and "answer" in item:
                    qa_pairs.append(QAPair(
                        question=item["question"],
                        answer=item["answer"],
                        context=item.get("context")
                    ))
            elif hasattr(item, 'question') and hasattr(item, 'answer'):
                # If it's an object with question/answer attributes
                qa_pair = {
                    "question": item.question,
                    "answer": item.answer
                }
                if hasattr(item, 'context') and item.context:
                    qa_pair["context"] = item.context
                qa_pairs.append(QAPair(**qa_pair))
    
    return qa_pairs


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
    qa_pairs = generate_qa_pairs(
        ticker=ticker,
        year=year,
        max_questions=max_questions,
        use_mda_only=use_mda_only,
        model=model,
        api_key=api_key
    )
    
    if not qa_pairs:
        print(f"No Q&A pairs generated for {ticker} {year}")
        return 0
    
    # Write to JSONL file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for qa_pair in qa_pairs:
            json_line = json.dumps(qa_pair.model_dump(), ensure_ascii=False)
            f.write(json_line + "\n")
    
    print(f"Extracted {len(qa_pairs)} Q&A pairs to {output_file}")
    return len(qa_pairs)


def generate_qa_pairs_from_file(
    file_url: str,
    max_questions: int = 100,
    model: str = "gpt-4-turbo",
    api_key: Optional[str] = None
) -> List[QAPair]:
    """
    Generate Q&A pairs from a 10-K HTML file URL using DatasetGenerator.
    
    Supports:
    - HTTP/HTTPS URLs: "https://www.sec.gov/.../file.htm"
    - file:// URLs: "file:///path/to/file.htm" or "file:///C:/path/to/file.htm" (Windows)
    - Local file paths: "/path/to/file.htm" or "C:/path/to/file.htm" (Windows)
    
    Note: The library's generate_from_pdf() method works with HTML files from SEC EDGAR,
    even though the method name suggests PDFs.
    
    Args:
        file_url: URL or path to the 10-K HTML file
        max_questions: Maximum number of Q&A pairs to generate
        model: OpenAI model to use (default: "gpt-4-turbo")
        api_key: OpenAI API key. If None, uses OPENAI_API_KEY from .env file.
        
    Returns:
        List of QAPair models with question/answer (and optional context)
        
    Raises:
        ValueError: If OPENAI_API_KEY is not set and api_key is not provided
        FileNotFoundError: If local file path doesn't exist
    """
    from urllib.parse import urlparse
    
    # Get API key from parameter or environment
    openai_key = api_key or _get_openai_api_key()
    
    # Handle file:// URLs and local file paths
    parsed = urlparse(file_url)
    if parsed.scheme == 'file' or (not parsed.scheme and Path(file_url).exists()):
        # Convert file:// URL to local path, or use the path directly
        if parsed.scheme == 'file':
            file_path = parsed.path
            # Handle Windows file:// URLs (e.g., file:///C:/path -> C:/path)
            if os.name == 'nt' and file_path.startswith('/') and len(file_path) > 3 and file_path[2] == ':':
                file_path = file_path[1:]
        else:
            file_path = file_url
        
        # Verify file exists
        if not Path(file_path).exists():
            raise FileNotFoundError(f"HTML file not found: {file_path}")
        
        # Convert local path to file:// URL for the library
        # The library may need an absolute path
        abs_path = str(Path(file_path).absolute())
        # Use file:// URL format
        file_url = f"file://{abs_path}" if not abs_path.startswith('/') else f"file:///{abs_path}"
    
    # Initialize generator
    generator = DatasetGenerator(
        model=model,
        api_key=openai_key
    )
    
    # Generate from HTML file URL (library's generate_from_pdf works with HTML files)
    dataset = generator.generate_from_pdf(
        url=file_url,
        max_questions=max_questions
    )
    
    # Convert dataset to list of Q&A pairs
    # The dataset returns a tuple: ('items', [DatasetItem(...), ...])
    # Each DatasetItem has question, answer, and context attributes
    qa_pairs: List[QAPair] = []
    if hasattr(dataset, '__iter__'):
        for item in dataset:
            # Dataset is a tuple: ('items', [DatasetItem(...)])
            if isinstance(item, tuple) and len(item) == 2 and item[0] == 'items':
                dataset_items = item[1]
                for dataset_item in dataset_items:
                    # DatasetItem has question, answer, and context attributes
                    if hasattr(dataset_item, 'question') and hasattr(dataset_item, 'answer'):
                        qa_pair = {
                            "question": dataset_item.question,
                            "answer": dataset_item.answer
                        }
                        # Include context if available
                        if hasattr(dataset_item, 'context') and dataset_item.context:
                            qa_pair["context"] = dataset_item.context
                        qa_pairs.append(QAPair(**qa_pair))
            elif isinstance(item, dict):
                # If it's already a dict with question/answer, use it
                if "question" in item and "answer" in item:
                    qa_pairs.append(QAPair(
                        question=item["question"],
                        answer=item["answer"],
                        context=item.get("context")
                    ))
            elif hasattr(item, 'question') and hasattr(item, 'answer'):
                # If it's an object with question/answer attributes
                qa_pair = {
                    "question": item.question,
                    "answer": item.answer
                }
                if hasattr(item, 'context') and item.context:
                    qa_pair["context"] = item.context
                qa_pairs.append(QAPair(**qa_pair))
    
    return qa_pairs


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
    qa_pairs = generate_qa_pairs_from_file(
        file_url=file_url,
        max_questions=max_questions,
        model=model,
        api_key=api_key
    )
    
    if not qa_pairs:
        print(f"No Q&A pairs generated from file: {file_url}")
        return 0
    
    # Write to JSONL file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for qa_pair in qa_pairs:
            json_line = json.dumps(qa_pair.model_dump(), ensure_ascii=False)
            f.write(json_line + "\n")
    
    print(f"Extracted {len(qa_pairs)} Q&A pairs to {output_file}")
    return len(qa_pairs)
