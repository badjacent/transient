"""Test connectivity to FinancialDatasets.ai API."""

import os
import pytest
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@pytest.fixture
def api_key():
    """Get API key from environment."""
    key = os.getenv("FINANCIAL_DATASETS_API_KEY")
    if not key:
        pytest.skip("FINANCIAL_DATASETS_API_KEY not set in environment")
    return key


@pytest.fixture
def api_headers(api_key):
    """Create API headers with authentication."""
    return {"X-API-KEY": api_key}


def test_api_connectivity(api_headers):
    """Test basic connectivity to FinancialDatasets.ai API."""
    # Use the financial metrics endpoint for AAPL
    url = "https://api.financialdatasets.ai/financial-metrics/latest/AAPL"
    
    response = requests.get(url, headers=api_headers, timeout=10)
    
    # The API is reachable if we get any response (not a connection error)
    # 200 = success, 404 = endpoint not found (but API is reachable), 
    # 401/403 = auth issues (but API is reachable)
    assert response.status_code in [200, 404, 401, 403], \
        f"Unexpected status code {response.status_code}: {response.text}"
    
    # If we got 200, verify the response structure
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, dict), "Response should be a JSON object"
        assert data, "Response should contain data"


def test_api_key_valid(api_headers):
    """Test that the API key is valid by making an authenticated request."""
    # Try to get financial metrics for a well-known ticker
    url = "https://api.financialdatasets.ai/financial-metrics/latest/AAPL"
    
    response = requests.get(url, headers=api_headers, timeout=10)
    
    # If we get 401, the API key is invalid
    if response.status_code == 401:
        pytest.fail("API key appears to be invalid (401 Unauthorized)")
    
    # If we get 403, we might not have access to this endpoint
    if response.status_code == 403:
        pytest.skip("API key valid but endpoint access denied (403)")
    
    # Otherwise, we should get a successful response
    assert response.status_code in [200, 404], \
        f"Unexpected status code {response.status_code}: {response.text}"


def test_api_endpoint_availability(api_headers):
    """Test that the API endpoint is reachable."""
    # Test a simple endpoint that should always be available
    url = "https://api.financialdatasets.ai/health"
    
    try:
        response = requests.get(url, headers=api_headers, timeout=10)
        # Health endpoint might return 200 or might not exist (404)
        # Either way, if we get a response, the API is reachable
        assert response.status_code in [200, 404, 401], \
            f"Unexpected status code {response.status_code}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Failed to reach API endpoint: {e}")


