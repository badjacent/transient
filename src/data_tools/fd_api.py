"""FinancialDatasets.ai client for basic equity snapshots."""

import os
from typing import Dict, Optional
from datetime import date, timedelta
import requests
from dotenv import load_dotenv
from src.data_tools.schemas import CompanyFacts, EquitySnapshot, PriceSnapshot

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


def get_price_snapshot(ticker: str, end_date: date) -> PriceSnapshot:
    """
    Fetch close, 1D, and 5D returns ending on end_date.

    IMPORTANT ASSUMPTION: No corporate-action adjustments (splits/dividends/etc.); returns are raw ratios on provided closes.
    IMPORTANT ASSUMPTION: Trading-calendar awareness is absent; requests pull a window and infer trading days from nonzero-volume records.
    """
    if not ticker or not isinstance(ticker, str):
        raise ValueError("Ticker must be a non-empty string")
    
    if not isinstance(end_date, date):
        raise ValueError("end_date must be a date object")
    
    ticker = ticker.upper().strip()
    headers = _get_headers()
    
    date_str = end_date.strftime("%Y-%m-%d")
    
    snapshot = {"ticker": ticker, "source": "financialdatasets.ai"}
    
    try:
        days_to_request = 10
        
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
        
        prices_response = requests.get(
            prices_url,
            headers=headers,
            params=prices_params,
            timeout=10
        )
        
        # Check for API errors (non-200 status codes)
        if prices_response.status_code != 200:
            error_msg = f"API returned status {prices_response.status_code}"
            try:
                error_data = prices_response.json()
                if "message" in error_data:
                    error_msg = error_data["message"]
                elif "error" in error_data:
                    error_msg = error_data["error"]
            except:
                error_msg = prices_response.text or error_msg
            raise requests.exceptions.RequestException(
                f"Failed to fetch prices from FinancialDatasets.ai API for {ticker} "
                f"on date {date_str}: {error_msg}"
            )
        
        prices_data = prices_response.json()
        
        if isinstance(prices_data, dict) and "prices" in prices_data:
            price_list = prices_data["prices"]
        elif isinstance(prices_data, list):
            price_list = prices_data
        else:
            price_list = []
        
        price_points = []
        for price_item in price_list:
            if isinstance(price_item, dict):
                volume = price_item.get("volume", 0)
                close = price_item.get("close")
                if close is not None and volume and volume > 0:
                    price_points.append(
                        {
                            "close": float(close),
                            "date": price_item.get("date") or price_item.get("as_of_date"),
                        }
                    )

        if not price_points:
            raise ValueError(
                f"Could not retrieve price data for ticker {ticker} on date {date_str}. "
                f"API may not have data for this ticker/date."
            )

        closes = [p["close"] for p in price_points]
        price = closes[-1]
        snapshot["price"] = price
        snapshot["date"] = price_points[-1]["date"] or date_str

        if len(closes) < 2:
            raise ValueError(f"Insufficient data to compute 1D return for {ticker} ending {snapshot['date']}")
        prev_price = closes[-2]
        if prev_price <= 0:
            raise ValueError(f"Invalid previous price for 1D return for {ticker} ending {snapshot['date']}")
        snapshot["return_1d"] = price / prev_price

        if len(closes) < 6:
            raise ValueError(f"Insufficient data to compute 5D return for {ticker} ending {snapshot['date']}")
        price_5d_ago = closes[-6]
        if price_5d_ago <= 0:
            raise ValueError(f"Invalid historical price for 5D return for {ticker} ending {snapshot['date']}")
        snapshot["return_5d"] = price / price_5d_ago

        return PriceSnapshot(**snapshot)
        
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(
            f"Failed to fetch price snapshot from FinancialDatasets.ai API for {ticker} "
            f"on date {date_str}: {e}"
        ) from e
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError(
            f"Error parsing price snapshot data for ticker {ticker} on date {date_str}: {e}"
        ) from e


def get_company_facts(ticker: str) -> CompanyFacts:
    """Fetch current market cap/sector/industry; raise on missing or failed data."""
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
        
        if company_response.status_code != 200:
            error_msg = company_response.text or f"status {company_response.status_code}"
            try:
                error_data = company_response.json()
                error_msg = error_data.get("message") or error_data.get("error") or error_msg
            except Exception:
                pass
            raise requests.exceptions.RequestException(
                f"Failed to fetch company facts for {ticker}: {error_msg}"
            )

        company_data = company_response.json()
        if isinstance(company_data, dict) and "company_facts" in company_data:
            company_facts = company_data["company_facts"]
            if "sector" in company_facts:
                facts["sector"] = str(company_facts["sector"])
            if "industry" in company_facts:
                facts["industry"] = str(company_facts.get("industry", ""))
            if "market_cap" in company_facts:
                facts["market_cap"] = float(company_facts["market_cap"])

        missing = [field for field in ("market_cap", "sector") if field not in facts]
        if missing:
            raise ValueError(f"Company facts incomplete for {ticker}: missing {', '.join(missing)}")

        return CompanyFacts(**facts)
        
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(
            f"Failed to fetch company facts from FinancialDatasets.ai API for {ticker}: {e}"
        ) from e
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError(
            f"Error parsing company facts data for ticker {ticker}: {e}"
        ) from e


def _get_previous_weekday(target_date: Optional[date] = None) -> date:
    """
    Get the previous weekday (Monday-Friday) from the given date.
    
    If target_date is None, uses today's date.
    If target_date is already a weekday, returns target_date.
    Otherwise, goes back until finding a weekday (Monday=0, Sunday=6).
    
    Args:
        target_date: Date to start from (defaults to today if None)
        
    Returns:
        The most recent weekday (Monday-Friday) on or before target_date
    """
    if target_date is None:
        target_date = date.today()
    
    # Keep going back until we hit a weekday (Monday=0 through Friday=4)
    while target_date.weekday() >= 5:  # Saturday=5, Sunday=6
        target_date -= timedelta(days=1)
    
    return target_date


def get_equity_snapshot(ticker: str, end_date: Optional[date] = None) -> EquitySnapshot:
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
        end_date: End date for historical price data as a date object.
                 If None, uses the previous weekday (most recent Monday-Friday).
        
    Returns:
        EquitySnapshot model combining price/return data with company facts.
        
    Raises:
        ValueError: If API key is missing or ticker is invalid
        requests.RequestException: If API request fails
    """
    # If no date provided, use the previous weekday
    if end_date is None:
        end_date = _get_previous_weekday()
    
    # Get price snapshot (with dates)
    price_data = get_price_snapshot(ticker, end_date)
    
    # Get company facts (without dates, current data)
    company_data = get_company_facts(ticker)
    
    # Combine the results
    combined = EquitySnapshot(
        ticker=price_data.ticker,
        price=price_data.price,
        return_1d=price_data.return_1d,
        return_5d=price_data.return_5d,
        market_cap=company_data.market_cap,
        sector=company_data.sector,
        industry=company_data.industry,
        date=price_data.date,
        source=price_data.source,
    )
    
    return combined
