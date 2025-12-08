"""FinancialDatasets.ai API client for fetching equity market data."""

import os
from typing import Dict
from datetime import date, timedelta
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_URL = "https://api.financialdatasets.ai"


def _get_api_key() -> str:
    """Get API key from environment variables."""
    api_key = os.getenv("FINANCIAL_DATASETS_API_KEY")
    if not api_key:
        raise ValueError(
            "FINANCIAL_DATASETS_API_KEY not found in environment variables. "
            "Please set it in your .env file."
        )
    return api_key


def _get_headers() -> Dict[str, str]:
    """Get API headers with authentication."""
    return {"X-API-KEY": _get_api_key()}


def get_price_snapshot(ticker: str, end_date: date) -> Dict:
    """
    Get price snapshot data for a specific date.
    
    Fetches: price on end_date, 1D return (vs previous trading day), 5D return (vs 5 trading days ago).
    This function assumes NO CORPORATE ACTIONS (splits, dividends, etc.) between the dates.
    
    IMPORTANT ASSUMPTION: This function assumes no corporate actions (stock splits, 
    reverse splits, dividends, spinoffs, etc.) have occurred between the end_date 
    and the comparison dates. If corporate actions have occurred, the returns will 
    be incorrect. For accurate returns with corporate actions, use adjusted prices.

    IMPORTANT ASSUMPTION: This function assumes trading on all trading days between the end date
    and comparison dates. If there are is no trading on said trading dates, the dates
    used for the calculations will be wrong. We don't have access to the trading calendar,
    so we can't know what dates to look back to.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "MSFT")
        end_date: End date for historical data as a date object
        
    Returns:
        Dictionary with the following structure:
        {
            "ticker": str,
            "price": float,  # Last price on end_date
            "return_1d": float,  # Return multiplier vs previous trading day (1.01 = up 1%)
            "return_5d": float,  # Return multiplier vs 5 trading days ago (1.01 = up 1%)
            "date": str,  # End date in YYYY-MM-DD format
            "source": "financialdatasets.ai"
        }
        
    Raises:
        ValueError: If API key is missing, ticker is invalid, or date format is invalid
        requests.RequestException: If API request fails
    """
    if not ticker or not isinstance(ticker, str):
        raise ValueError("Ticker must be a non-empty string")
    
    if not isinstance(end_date, date):
        raise ValueError("end_date must be a date object")
    
    ticker = ticker.upper().strip()
    headers = _get_headers()
    
    # Convert date to string for API calls
    date_str = end_date.strftime("%Y-%m-%d")
    
    snapshot = {
        "ticker": ticker,
        "source": "financialdatasets.ai",
        "date": date_str
    }
    
    try:
        # Get historical prices ending on the specified date
        # Request enough days to account for weekends/holidays (need at least 5 trading days)
        days_to_request = 10  # Request 10 days to ensure we get 5+ trading days
        
        prices_response = None
        
        # Get historical data for specific date
        # API documentation: https://docs.financialdatasets.ai/api-reference/endpoint/prices/historical
        # Required params: ticker, interval, interval_multiplier, start_date, end_date
        # Calculate start_date (days_to_request days before end_date to get enough data for 5D return)
        start_date_obj = end_date - timedelta(days=days_to_request)
        start_date_str = start_date_obj.strftime("%Y-%m-%d")
        
        prices_url = f"{BASE_URL}/prices"
        prices_params = {
            "ticker": ticker,
            "interval": "day",
            "interval_multiplier": 1,
            "start_date": start_date_str,
            "end_date": date_str,
            "limit": days_to_request
        }
        
        # Extract prices from response and normalize to a list of close prices
        # Prices are returned in chronological order (oldest first)
        close_prices = []
        
        prices_response = requests.get(
            prices_url,
            headers=headers,
            params=prices_params,
            timeout=10
        )
        
        if prices_response.status_code == 200:
            prices_data = prices_response.json()
            
            # Handle historical prices endpoint response: {"prices": [...], "next_page_url": "..."}
            if isinstance(prices_data, dict) and "prices" in prices_data:
                price_list = prices_data["prices"]
            elif isinstance(prices_data, list):
                price_list = prices_data
            else:
                price_list = []
            
            # Extract close prices in chronological order
            # Exclude days with zero volume (non-trading days)
            for price_item in price_list:
                if isinstance(price_item, dict):
                    volume = price_item.get("volume", 0)
                    close = price_item.get("close")
                    # Only include days with trading volume > 0
                    if close is not None and volume and volume > 0:
                        close_prices.append(float(close))
        
        
        # Calculate returns from the chronological list of close prices
        # close_prices is in chronological order: [oldest, ..., newest]
        if close_prices:
            # Latest price (on end_date) is the last item
            price = close_prices[-1]
            snapshot["price"] = price
            
            # Calculate 1D return: compare to previous day
            # Returns are multipliers: 1.01 means up 1%, 0.99 means down 1%
            if len(close_prices) >= 2:
                prev_price = close_prices[-2]
                if prev_price > 0:
                    snapshot["return_1d"] = price / prev_price
            
            # Calculate 5D return: compare to price 5 trading days ago
            # Use index -6 (6th from end) to get exactly 5 trading days back
            # (index -1 is current, -2 is 1 day ago, ..., -6 is 5 days ago)
            # Returns are multipliers: 1.01 means up 1%, 0.99 means down 1%
            # Note: Only trading days (volume > 0) are included in close_prices
            if len(close_prices) >= 6:
                price_5d_ago = close_prices[-6]
                if price_5d_ago > 0:
                    snapshot["return_5d"] = price / price_5d_ago
        
        # Final validation and defaults
        if "price" not in snapshot or snapshot.get("price", 0) == 0:
            raise ValueError(
                f"Could not retrieve price data for ticker {ticker} on date {date_str}. "
                f"API may not have data for this ticker/date."
            )
        
        if "return_1d" not in snapshot:
            snapshot["return_1d"] = 1.0  # 1.0 means no change
        
        # Note: 5D return calculation uses index 7 to approximate 5 trading days
        # This assumes no more than 2 non-trading days (weekend) in a 7-day period
        # For more accuracy, we would need explicit trading day information from the API
        if "return_5d" not in snapshot:
            snapshot["return_5d"] = 1.0  # 1.0 means no change
        
        return snapshot
        
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(
            f"Failed to fetch price snapshot from FinancialDatasets.ai API for {ticker} "
            f"on date {date_str}: {e}"
        ) from e
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError(
            f"Error parsing price snapshot data for ticker {ticker} on date {date_str}: {e}"
        ) from e


def get_company_facts(ticker: str) -> Dict:
    """
    Get company facts data (current/static information without explicit dates).
    
    Fetches: market cap, sector, industry.
    This data comes from endpoints that provide current company information
    but do not include timestamp information.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "MSFT")
        
    Returns:
        Dictionary with the following structure:
        {
            "ticker": str,
            "market_cap": float,
            "sector": str,
            "industry": str,
            "source": "financialdatasets.ai"
        }
        
    Raises:
        ValueError: If API key is missing or ticker is invalid
        requests.RequestException: If API request fails
    """
    if not ticker or not isinstance(ticker, str):
        raise ValueError("Ticker must be a non-empty string")
    
    ticker = ticker.upper().strip()
    headers = _get_headers()
    
    facts = {
        "ticker": ticker,
        "source": "financialdatasets.ai"
    }
    
    try:
        # Get company facts (current data, no explicit dates)
        company_url = f"{BASE_URL}/company/facts"
        company_params = {"ticker": ticker}
        company_response = requests.get(
            company_url,
            headers=headers,
            params=company_params,
            timeout=10
        )
        
        if company_response.status_code == 200:
            company_data = company_response.json()
            if isinstance(company_data, dict) and "company_facts" in company_data:
                company_facts = company_data["company_facts"]
                if "sector" in company_facts:
                    facts["sector"] = str(company_facts["sector"])
                if "industry" in company_facts:
                    facts["industry"] = str(company_facts.get("industry", ""))
                if "market_cap" in company_facts:
                    facts["market_cap"] = float(company_facts["market_cap"])
        
        # Set defaults for missing values
        if "market_cap" not in facts:
            facts["market_cap"] = 0.0
        if "sector" not in facts:
            facts["sector"] = "Unknown"
        if "industry" not in facts:
            facts["industry"] = ""
        
        return facts
        
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(
            f"Failed to fetch company facts from FinancialDatasets.ai API for {ticker}: {e}"
        ) from e
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError(
            f"Error parsing company facts data for ticker {ticker}: {e}"
        ) from e


def get_equity_snapshot(ticker: str, end_date: date) -> Dict:
    """
    Get a complete snapshot of equity market data for a given ticker.
    
    This is a convenience function that combines:
    - get_price_snapshot() - price and returns data for a specific date
    - get_company_facts() - market cap, sector, industry (current data)
    
    IMPORTANT ASSUMPTION: This function is "all or none" - it goes directly to the
    data source (FinancialDatasets.ai API) with no caching, no intermediate layers,
    and no data transformation beyond basic parsing. The data quality, completeness,
    and availability are entirely dependent on what the data source provides. If the
    source has missing, incorrect, or stale data, this function will return that data
    as-is. There is no validation, cleaning, or fallback mechanism beyond what the
    underlying API endpoints provide.
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "MSFT")
        end_date: End date for historical price data as a date object
        
    Returns:
        Dictionary with the following structure:
        {
            "ticker": str,
            "price": float,
            "return_1d": float,  # Return multiplier (1.01 = up 1%)
            "return_5d": float,  # Return multiplier (1.01 = up 1%)
            "market_cap": float,
            "sector": str,
            "date": str,  # Date from price snapshot
            "source": "financialdatasets.ai"
        }
        
    Raises:
        ValueError: If API key is missing or ticker is invalid
        requests.RequestException: If API request fails
    """
    # Get price snapshot (with dates)
    price_data = get_price_snapshot(ticker, end_date)
    
    # Get company facts (without dates, current data)
    company_data = get_company_facts(ticker)
    
    # Combine the results
    combined = {
        "ticker": ticker,
        "price": price_data.get("price", 0.0),
        "return_1d": price_data.get("return_1d", 1.0),  # 1.0 means no change
        "return_5d": price_data.get("return_5d", 1.0),  # 1.0 means no change
        "market_cap": company_data.get("market_cap", 0.0),
        "sector": company_data.get("sector", "Unknown"),
        "date": price_data.get("date", ""),
        "source": "financialdatasets.ai"
    }
    
    # Add industry if available
    if "industry" in company_data and company_data["industry"]:
        combined["industry"] = company_data["industry"]
    
    return combined
