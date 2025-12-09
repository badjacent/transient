"""Unit tests for fd_api module using real API calls."""

import os
import pytest
from datetime import date
from dotenv import load_dotenv
from src.data_tools.fd_api import get_price_snapshot
from src.data_tools.schemas import EquitySnapshot, PriceSnapshot

# Load environment variables
load_dotenv()


@pytest.fixture
def api_key():
    """Get API key from environment."""
    key = os.getenv("FINANCIAL_DATASETS_API_KEY")
    if not key:
        pytest.skip("FINANCIAL_DATASETS_API_KEY not set in environment")
    return key


# Hardcoded expected prices from Yahoo Finance for AAPL
# Base date: June 5, 2024 (first Wednesday in June 2024)
# Prices from Yahoo Finance historical data
EXPECTED_AAPL_JUNE_5_2024 = {
    "date": "2024-06-05",
    "price": 195.87,  # June 5, 2024 close (from Yahoo Finance)
    "price_1d_ago": 194.35,  # June 4, 2024 close (from Yahoo Finance)
    "price_5d_ago": 190.29,  # May 29, 2024 close (from Yahoo Finance)
}

# Hardcoded expected prices from Yahoo Finance for AAPL
# Base date: December 27, 2024 (Friday - regular trading day)
# Prices from Yahoo Finance historical data
EXPECTED_AAPL_DEC_27_2024 = {
    "date": "2024-12-27",  # Requested date (Friday)
    "price": 255.59,  # December 27, 2024 close price (from Yahoo Finance)
    "price_1d_ago": 259.02,  # December 26, 2024 close (from Yahoo Finance)
    "price_5d_ago": 249.79,  # December 19, 2024 close (from Yahoo Finance) - 5 trading days before Dec 27 (after excluding zero-volume days)
}

# Hardcoded expected prices from Yahoo Finance for AAPL
# Base date: January 13, 2025 (Monday)
# Prices from Yahoo Finance historical data
EXPECTED_AAPL_JAN_13_2025 = {
    "date": "2025-01-13",  # Requested date (Monday)
    "price": 234.40,  # January 13, 2025 close price (from Yahoo Finance)
    "price_1d_ago": 236.85,  # January 10, 2025 close (from Yahoo Finance)
    "price_5d_ago": 243.36,  # January 8, 2025 close (from Yahoo Finance) - 5 trading days before Jan 13
}


def test_get_price_snapshot_june_5_2024(api_key):
    """Test get_price_snapshot with June 5, 2024 as base date using real API."""
    # Call the function with June 5, 2024
    # Note: This will use the real API, so results may differ from hardcoded values
    # if the API doesn't have data for this date or returns different prices
    test_date = date(2024, 6, 5)
    result = get_price_snapshot("AAPL", test_date)
    assert isinstance(result, PriceSnapshot)
    data = result.model_dump()
    
    # Verify basic structure
    assert data["ticker"] == "AAPL"
    assert data["date"] == "2024-06-05"
    assert data["source"] == "financialdatasets.ai"
    
    # Verify we got a price
    assert "price" in data
    assert data["price"] > 0
    assert isinstance(data["price"], float)
    
    # Verify returns are calculated (may differ from expected due to API data)
    assert "return_1d" in data
    assert isinstance(data["return_1d"], float)
    
    assert "return_5d" in data
    assert isinstance(data["return_5d"], float)
    
    # Verify the price matches expected
    assert abs(data["price"] - EXPECTED_AAPL_JUNE_5_2024["price"]) < 0.001, \
        f"Price mismatch: got {data['price']}, expected ~{EXPECTED_AAPL_JUNE_5_2024['price']}"
    
    # Calculate expected returns from price ratios (very tight tolerance since we use unadjusted prices)
    expected_1d = EXPECTED_AAPL_JUNE_5_2024["price"] / EXPECTED_AAPL_JUNE_5_2024["price_1d_ago"]
    assert abs(data["return_1d"] - expected_1d) < 1e-7, \
        f"1D return mismatch: got {data['return_1d']:.10f}, expected {expected_1d:.10f}"
    
    expected_5d = EXPECTED_AAPL_JUNE_5_2024["price"] / EXPECTED_AAPL_JUNE_5_2024["price_5d_ago"]
    assert abs(data["return_5d"] - expected_5d) < 1e-7, \
        f"5D return mismatch: got {data['return_5d']:.10f}, expected {expected_5d:.10f}"


def test_get_price_snapshot_december_27_2024(api_key):
    """Test get_price_snapshot with December 27, 2024 (Friday - regular trading day) using real API."""
    # December 27, 2024 is a Friday, a regular trading day
    test_date = date(2024, 12, 27)
    result = get_price_snapshot("AAPL", test_date)
    assert isinstance(result, PriceSnapshot)
    data = result.model_dump()
    
    # Verify basic structure
    assert data["ticker"] == "AAPL"
    assert data["date"] == "2024-12-27"  # Date should be the requested date
    assert data["source"] == "financialdatasets.ai"
    
    # Verify we got a price
    assert "price" in data
    assert data["price"] > 0
    assert isinstance(data["price"], float)
    
    # Verify returns are calculated
    assert "return_1d" in data
    assert isinstance(data["return_1d"], float)
    
    assert "return_5d" in data
    assert isinstance(data["return_5d"], float)
    
    # Verify the price matches expected (Dec 27, 2024 close: 255.59)
    assert abs(data["price"] - EXPECTED_AAPL_DEC_27_2024["price"]) < 0.001, \
        f"Price mismatch: got {data['price']}, expected ~{EXPECTED_AAPL_DEC_27_2024['price']}"
    
    # Calculate expected returns from price ratios (very tight tolerance since we use unadjusted prices)
    expected_1d = EXPECTED_AAPL_DEC_27_2024["price"] / EXPECTED_AAPL_DEC_27_2024["price_1d_ago"]
    assert abs(data["return_1d"] - expected_1d) < 1e-7, \
        f"1D return mismatch: got {data['return_1d']:.10f}, expected {expected_1d:.10f}"
    
    expected_5d = EXPECTED_AAPL_DEC_27_2024["price"] / EXPECTED_AAPL_DEC_27_2024["price_5d_ago"]
    assert abs(data["return_5d"] - expected_5d) < 1e-7, \
        f"5D return mismatch: got {data['return_5d']:.10f}, expected {expected_5d:.10f}"


def test_get_price_snapshot_january_13_2025(api_key):
    """Test get_price_snapshot with January 13, 2025 (Monday) using real API."""
    test_date = date(2025, 1, 13)
    result = get_price_snapshot("AAPL", test_date)
    assert isinstance(result, PriceSnapshot)
    data = result.model_dump()
    
    # Verify basic structure
    assert data["ticker"] == "AAPL"
    assert data["date"] == "2025-01-13"  # Date should be the requested date
    assert data["source"] == "financialdatasets.ai"
    
    # Verify we got a price
    assert "price" in data
    assert data["price"] > 0
    assert isinstance(data["price"], float)
    
    # Verify returns are calculated
    assert "return_1d" in data
    assert isinstance(data["return_1d"], float)
    
    assert "return_5d" in data
    assert isinstance(data["return_5d"], float)
    
    # Verify the price matches expected (Jan 13, 2025 close: 234.40)
    assert abs(data["price"] - EXPECTED_AAPL_JAN_13_2025["price"]) < 0.001, \
        f"Price mismatch: got {data['price']}, expected ~{EXPECTED_AAPL_JAN_13_2025['price']}"
    
    # Calculate expected returns from price ratios (very tight tolerance since we use unadjusted prices)
    expected_1d = EXPECTED_AAPL_JAN_13_2025["price"] / EXPECTED_AAPL_JAN_13_2025["price_1d_ago"]
    assert abs(data["return_1d"] - expected_1d) < 1e-7, \
        f"1D return mismatch: got {data['return_1d']:.10f}, expected {expected_1d:.10f}"
    
    expected_5d = EXPECTED_AAPL_JAN_13_2025["price"] / EXPECTED_AAPL_JAN_13_2025["price_5d_ago"]
    assert abs(data["return_5d"] - expected_5d) < 1e-7, \
        f"5D return mismatch: got {data['return_5d']:.10f}, expected {expected_5d:.10f}"


def test_get_price_snapshot_requires_date():
    """Test that get_price_snapshot requires a date parameter."""
    with pytest.raises(TypeError):
        get_price_snapshot("AAPL")  # Missing required argument
    
    # Test that it requires a date object, not a string
    with pytest.raises(ValueError, match="end_date must be a date object"):
        get_price_snapshot("AAPL", "2024-06-05")  # String instead of date


def test_get_price_snapshot_invalid_date_type():
    """Test get_price_snapshot with invalid date type."""
    with pytest.raises(ValueError, match="end_date must be a date object"):
        get_price_snapshot("AAPL", "2024-06-05")  # String instead of date
    
    with pytest.raises(ValueError, match="end_date must be a date object"):
        get_price_snapshot("AAPL", None)  # None instead of date


def test_get_price_snapshot_invalid_ticker():
    """Test get_price_snapshot with invalid ticker."""
    with pytest.raises(ValueError, match="Ticker must be a non-empty string"):
        get_price_snapshot("", "2024-06-05")
    
    with pytest.raises(ValueError, match="Ticker must be a non-empty string"):
        get_price_snapshot(None, "2024-06-05")


def test_get_price_snapshot_returns_correct_structure(api_key):
    """Test that get_price_snapshot returns the correct structure using real API."""
    test_date = date(2024, 6, 5)
    result = get_price_snapshot("AAPL", test_date)
    assert isinstance(result, PriceSnapshot)
    data = result.model_dump()
    
    # Verify all required keys are present
    required_keys = ["ticker", "price", "return_1d", "return_5d", "date", "source"]
    for key in required_keys:
        assert key in data, f"Missing required key: {key}"
    
    # Verify types
    assert isinstance(data["ticker"], str)
    assert isinstance(data["price"], float)
    assert isinstance(data["return_1d"], float)
    assert isinstance(data["return_5d"], float)
    assert isinstance(data["date"], str)
    assert isinstance(data["source"], str)
    
    # Verify values are reasonable
    assert data["price"] > 0
    assert data["ticker"] == "AAPL"
    assert data["source"] == "financialdatasets.ai"


def test_get_equity_snapshot(api_key):
    """Test get_equity_snapshot function using real API."""
    from src.data_tools.fd_api import get_equity_snapshot
    
    # Test with a specific date - use today's date
    today = date.today()
    result = get_equity_snapshot("AAPL", today)
    assert isinstance(result, EquitySnapshot)
    data = result.model_dump()
    
    # Verify all required keys are present
    required_keys = ["ticker", "price", "return_1d", "return_5d", "market_cap", "sector", "date", "source"]
    for key in required_keys:
        assert key in data, f"Missing required key: {key}"
    
    # Verify types
    assert isinstance(data["ticker"], str)
    assert isinstance(data["price"], float)
    assert isinstance(data["return_1d"], float)
    assert isinstance(data["return_5d"], float)
    assert isinstance(data["market_cap"], float)
    assert isinstance(data["sector"], str)
    assert isinstance(data["date"], str)
    assert isinstance(data["source"], str)
    
    # Verify values are reasonable
    assert data["ticker"] == "AAPL"
    assert data["price"] > 0
    assert data["market_cap"] > 0
    assert data["sector"] != "Unknown"  # Should have a real sector
    assert data["source"] == "financialdatasets.ai"
    
    # Industry is optional but should be present if available
    if "industry" in data:
        assert isinstance(data["industry"], str)


def test_get_equity_snapshot_with_date(api_key):
    """Test get_equity_snapshot function with a specific date using real API."""
    from src.data_tools.fd_api import get_equity_snapshot
    
    # Test with June 5, 2024
    test_date = date(2024, 6, 5)
    result = get_equity_snapshot("AAPL", test_date)
    assert isinstance(result, EquitySnapshot)
    data = result.model_dump()
    
    # Verify date is set correctly
    assert data["date"] == "2024-06-05"
    
    # Verify all required fields are present
    assert "price" in data
    assert "market_cap" in data
    assert "sector" in data
    assert data["price"] > 0
    assert data["market_cap"] > 0


def test_get_equity_snapshot_none_date(api_key):
    """Test get_equity_snapshot function with None date (should use previous weekday)."""
    from src.data_tools.fd_api import get_equity_snapshot, _get_previous_weekday
    
    # Test with None date - should use previous weekday
    result = get_equity_snapshot("AAPL", None)
    assert isinstance(result, EquitySnapshot)
    data = result.model_dump()
    
    # Verify all required keys are present
    required_keys = ["ticker", "price", "return_1d", "return_5d", "market_cap", "sector", "date", "source"]
    for key in required_keys:
        assert key in data, f"Missing required key: {key}"
    
    # Verify the date used is the previous weekday
    expected_date = _get_previous_weekday()
    assert data["date"] == expected_date.strftime("%Y-%m-%d")
    
    # Verify the date is a weekday (Monday=0, Friday=4)
    result_date = date.fromisoformat(data["date"])
    assert result_date.weekday() < 5, f"Date {data['date']} should be a weekday"
    
    # Verify values are reasonable
    assert data["ticker"] == "AAPL"
    assert data["price"] > 0
    assert data["market_cap"] > 0
    assert data["source"] == "financialdatasets.ai"
