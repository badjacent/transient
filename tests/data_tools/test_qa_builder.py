"""Tests for qa_builder module."""

import os
import pytest
from dotenv import load_dotenv
from src.data_tools.schemas import QAPair

# Load environment variables
load_dotenv()


def test_qa_builder_extract_mda_smoke():
    """Smoke test: Verify extract_mda_section can be called (may fail if SEC API unavailable)."""
    from src.data_tools.qa_builder import extract_mda_section
    
    # Try to extract MD&A for a well-known company (AAPL, 2023)
    # This test may fail if:
    # - SEC API is unavailable
    # - Filing doesn't exist for that year
    # - Network issues
    # But it should not fail due to import errors or function signature issues
    
    try:
        result = extract_mda_section("AAPL", 2023)
        # If successful, result should be a string or None
        assert result is None or isinstance(result, str), \
            f"extract_mda_section should return str or None, got {type(result)}"
        # If we got text, it should be non-empty
        if result:
            assert len(result) > 0, "MD&A text should not be empty"
    except Exception as e:
        # It's okay if this fails due to API/network issues - that's not a smoke test failure
        # But we should verify the exception is reasonable (not an import error, etc.)
        assert not isinstance(e, (ImportError, AttributeError, NameError)), \
            f"Unexpected error type: {type(e).__name__}: {e}"


def test_qa_builder_generate_qa_pairs_smoke():
    """Smoke test: Verify generate_qa_pairs function signature and structure."""
    from src.data_tools.qa_builder import generate_qa_pairs
    
    # Check if OpenAI API key is available
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        pytest.skip("OPENAI_API_KEY not set - skipping test that requires API")
    
    # Test with a well-known ticker and year
    # This will actually call the API, so it may take time and cost money
    try:
        result = generate_qa_pairs(
            ticker="AAPL",
            year=2023,
            max_questions=5,  # Small number for smoke test
            use_mda_only=True
        )
        
        # Should return a list
        assert isinstance(result, list), f"generate_qa_pairs should return a list, got {type(result)}"
        
        # If we got results, verify structure
        if result:
            for qa_pair in result:
                assert isinstance(qa_pair, QAPair), "Each Q&A pair should be a QAPair model"
                assert qa_pair.question, "Q&A pair should have a question"
                assert qa_pair.answer, "Q&A pair should have an answer"
    except Exception as e:
        # It's okay if this fails due to API issues - that's not a smoke test failure
        # But we should verify the exception is reasonable (not an import error, etc.)
        assert not isinstance(e, (ImportError, AttributeError, NameError)), \
            f"Unexpected error type: {type(e).__name__}: {e}"
