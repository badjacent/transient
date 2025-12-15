"""FinancialDatasets.ai client for basic equity snapshots."""

import os
from datetime import date, timedelta
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

from src.data_tools.schemas import (
    BalanceSheet,
    CashFlowStatement,
    CompanyFacts,
    EquitySnapshot,
    IncomeStatement,
    PriceSnapshot,
)

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


def get_income_statements(
    ticker: str,
    years: int = 4,
    period: str = "annual"
) -> List[IncomeStatement]:
    """
    Fetch income statement history for the requested ticker.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "NVDA").
        years: Number of most recent statements to return.
        period: "annual" or "quarterly" per FinancialDatasets API.

    Returns:
        List of dicts (newest first) with income statement fields.
    """
    if not ticker or not isinstance(ticker, str):
        raise ValueError("Ticker must be a non-empty string")
    if years <= 0:
        raise ValueError("years must be a positive integer")

    symbol = ticker.upper().strip()
    headers = _get_headers()
    url = f"{BASE_URL}/financials/income-statements"
    params = {
        "ticker": symbol,
        "limit": years,
        "period": period,
    }

    response = requests.get(url, headers=headers, params=params, timeout=10)
    if response.status_code != 200:
        error_msg = response.text or f"status {response.status_code}"
        try:
            error_data = response.json()
            error_msg = error_data.get("message") or error_data.get("error") or error_msg
        except Exception:
            pass
        raise requests.exceptions.RequestException(
            f"Failed to fetch income statements for {symbol}: {error_msg}"
        )

    payload = response.json()
    if isinstance(payload, dict):
        statements = payload.get("financials") or payload.get("data") or payload.get("items")
        if statements is None and "results" in payload:
            statements = payload["results"]
        if statements is None:
            for value in payload.values():
                if isinstance(value, list) and value:
                    statements = value
                    break
    elif isinstance(payload, list):
        statements = payload
    else:
        statements = None

    if not statements:
        raise ValueError(f"No income statements returned for {symbol}")

    normalized: List[IncomeStatement] = []
    for entry in statements:
        if not isinstance(entry, dict):
            continue
        
        # Helper function to try multiple field name variations (case-insensitive)
        def get_field(*field_names):
            for name in field_names:
                # Try exact match first
                value = entry.get(name)
                if value is not None:
                    return value
                # Try case-insensitive match
                for key in entry.keys():
                    if isinstance(key, str) and key.lower() == name.lower():
                        return entry[key]
            return None
        
        # Extract fields with multiple fallback names
        fiscal_year = get_field(
            "fiscalYear", "fiscal_year", "calendarYear", "calendar_year", 
            "year", "fiscalYearEnd", "fiscal_year_end"
        )
        # Try to extract year from date string if fiscal_year is None
        if fiscal_year is None:
            date_str = get_field("date", "reportDate", "report_date", "filingDate", "filing_date")
            if date_str and isinstance(date_str, str):
                try:
                    # Try to extract year from YYYY-MM-DD format
                    fiscal_year = int(date_str.split("-")[0])
                except (ValueError, AttributeError):
                    pass
        
        operating_income = get_field(
            "operatingIncome", "operating_income", "operatingIncomeLoss", 
            "operating_income_loss", "operatingProfit", "operating_profit",
            "ebit", "EBIT"
        )
        
        net_income = get_field(
            "netIncome", "net_income", "netIncomeLoss", "net_income_loss",
            "netIncomeApplicableToCommonShares", "net_income_applicable_to_common_shares",
            "netEarnings", "net_earnings", "profit", "netProfit", "net_profit"
        )
        
        diluted_eps = get_field(
            "dilutedEPS", "diluted_eps", "epsDiluted", "eps_diluted",
            "earningsPerShareDiluted", "earnings_per_share_diluted",
            "eps", "EPS"
        )
        
        model = IncomeStatement(
            ticker=entry.get("ticker") or entry.get("symbol") or symbol,
            period=str(entry.get("period") or entry.get("reportType") or entry.get("report_type") or period),
            fiscal_year=int(fiscal_year) if fiscal_year is not None else None,
            fiscal_period=get_field("fiscalPeriod", "fiscal_period", "quarter", "fiscalQuarter", "fiscal_quarter"),
            total_revenue=get_field("totalRevenue", "total_revenue", "revenue", "sales", "netSales", "net_sales"),
            cost_of_revenue=get_field("costOfRevenue", "cost_of_revenue", "costOfSales", "cost_of_sales", "cogs", "COGS"),
            gross_profit=get_field("grossProfit", "gross_profit", "grossIncome", "gross_income"),
            operating_income=operating_income,
            net_income=net_income,
            diluted_eps=diluted_eps,
            currency=get_field("currency", "reportedCurrency", "reported_currency", "currencyCode", "currency_code"),
            raw=entry,
        )
        normalized.append(model)

    if not normalized:
        raise ValueError(f"Unable to parse income statements for {symbol}")

    return normalized[:years]


def get_balance_sheets(
    ticker: str,
    years: int = 4,
    period: str = "annual"
) -> List[BalanceSheet]:
    """
    Fetch balance sheet history for the requested ticker.
    
    Balance sheets provide critical risk metrics:
    - Liquidity: current ratio, working capital, cash position
    - Leverage: debt-to-equity, total debt levels
    - Financial health: assets vs liabilities

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "TSLA").
        years: Number of most recent statements to return.
        period: "annual" or "quarterly" per FinancialDatasets API.

    Returns:
        List of BalanceSheet objects (newest first) with assets, liabilities, equity, and calculated risk metrics.
    """
    if not ticker or not isinstance(ticker, str):
        raise ValueError("Ticker must be a non-empty string")
    if years <= 0:
        raise ValueError("years must be a positive integer")

    symbol = ticker.upper().strip()
    headers = _get_headers()
    url = f"{BASE_URL}/financials/balance-sheets"
    params = {
        "ticker": symbol,
        "limit": years,
        "period": period,
    }

    response = requests.get(url, headers=headers, params=params, timeout=10)
    if response.status_code != 200:
        error_msg = response.text or f"status {response.status_code}"
        try:
            error_data = response.json()
            error_msg = error_data.get("message") or error_data.get("error") or error_msg
        except Exception:
            pass
        raise requests.exceptions.RequestException(
            f"Failed to fetch balance sheets for {symbol}: {error_msg}"
        )

    payload = response.json()
    # FinancialDatasets.ai returns balance_sheets array directly in response
    # See: https://docs.financialdatasets.ai/api-reference/endpoint/financials/balance-sheets
    if isinstance(payload, dict):
        statements = payload.get("balance_sheets") or payload.get("financials") or payload.get("data") or payload.get("items")
        if statements is None and "results" in payload:
            statements = payload["results"]
        if statements is None:
            for value in payload.values():
                if isinstance(value, list) and value:
                    statements = value
                    break
    elif isinstance(payload, list):
        statements = payload
    else:
        statements = None

    if not statements:
        raise ValueError(f"No balance sheets returned for {symbol}")

    normalized: List[BalanceSheet] = []
    for entry in statements:
        if not isinstance(entry, dict):
            continue
        
        # Helper function to try multiple field name variations (case-insensitive)
        # If fields are still null, check entry.keys() or entry.get("raw") to see actual API field names
        def get_field(*field_names):
            for name in field_names:
                # Try exact match first
                value = entry.get(name)
                if value is not None:
                    return value
                # Try case-insensitive match
                for key in entry.keys():
                    if isinstance(key, str) and key.lower() == name.lower():
                        return entry[key]
            return None
        
        # FinancialDatasets.ai API uses snake_case field names
        # Documentation: https://docs.financialdatasets.ai/api-reference/endpoint/financials/balance-sheets
        
        # Extract year from report_period (format: "2023-12-25")
        fiscal_year = None
        report_period = entry.get("report_period")
        if report_period and isinstance(report_period, str):
            try:
                fiscal_year = int(report_period.split("-")[0])
            except (ValueError, AttributeError):
                pass
        
        # Use exact API field names (snake_case) as primary, with fallbacks
        current_assets = get_field("current_assets", "currentAssets", "totalCurrentAssets")
        current_liabilities = get_field("current_liabilities", "currentLiabilities", "totalCurrentLiabilities")
        
        # API uses: current_debt (not shortTermDebt) and non_current_debt (not longTermDebt)
        current_debt = get_field("current_debt", "currentDebt", "shortTermDebt", "short_term_debt")
        non_current_debt = get_field("non_current_debt", "nonCurrentDebt", "longTermDebt", "long_term_debt")
        
        # API provides total_debt directly
        total_debt = get_field("total_debt", "totalDebt")
        if total_debt is None:
            # Calculate from components if not provided
            lt_debt = non_current_debt or 0
            st_debt = current_debt or 0
            if lt_debt != 0 or st_debt != 0:
                total_debt = lt_debt + st_debt
        
        # API uses: shareholders_equity (snake_case)
        shareholders_equity = get_field("shareholders_equity", "shareholdersEquity", "totalStockholdersEquity", "total_stockholders_equity")
        total_equity = shareholders_equity  # Use shareholders_equity as total_equity
        
        # API uses: cash_and_equivalents (not cashAndCashEquivalents)
        cash_and_cash_equivalents = get_field(
            "cash_and_equivalents",  # Primary: exact API field name
            "cashAndCashEquivalents", "cash_and_cash_equivalents",
            "cashAndShortTermInvestments", "cash_and_short_term_investments"
        )
        
        # Calculate risk metrics
        current_ratio = None
        if current_assets is not None and current_liabilities is not None and current_liabilities != 0:
            current_ratio = current_assets / current_liabilities
        
        debt_to_equity = None
        if total_debt is not None and total_equity is not None and total_equity != 0:
            debt_to_equity = total_debt / total_equity
        
        working_capital = None
        if current_assets is not None and current_liabilities is not None:
            working_capital = current_assets - current_liabilities
        
        model = BalanceSheet(
            ticker=entry.get("ticker") or entry.get("symbol") or symbol,
            period=str(entry.get("period") or period),  # API uses: "annual", "quarterly", or "ttm"
            fiscal_year=int(fiscal_year) if fiscal_year is not None else None,
            fiscal_period=entry.get("fiscal_period"),  # API field: fiscal_period
            total_assets=entry.get("total_assets"),  # API field: total_assets
            current_assets=current_assets,
            cash_and_cash_equivalents=cash_and_cash_equivalents,
            total_liabilities=entry.get("total_liabilities"),  # API field: total_liabilities
            current_liabilities=current_liabilities,
            total_debt=total_debt if total_debt != 0 else None,  # API field: total_debt
            long_term_debt=non_current_debt,  # Map non_current_debt to long_term_debt
            short_term_debt=current_debt,  # Map current_debt to short_term_debt
            total_equity=total_equity,
            shareholders_equity=shareholders_equity,
            current_ratio=current_ratio,
            debt_to_equity=debt_to_equity,
            working_capital=working_capital,
            currency=entry.get("currency"),  # API field: currency
            raw=entry,
        )
        normalized.append(model)

    if not normalized:
        raise ValueError(f"Unable to parse balance sheets for {symbol}")

    return normalized[:years]


def get_cash_flow_statements(
    ticker: str,
    years: int = 4,
    period: str = "annual"
) -> List[CashFlowStatement]:
    """
    Fetch cash flow statement history for the requested ticker.
    
    Cash flow statements provide critical liquidity and cash generation metrics:
    - Operating cash flow: core business cash generation
    - Free cash flow: operating cash flow minus capital expenditures
    - Cash from financing/investing: capital allocation patterns

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "TSLA").
        years: Number of most recent statements to return.
        period: "annual" or "quarterly" per FinancialDatasets API.

    Returns:
        List of CashFlowStatement objects (newest first) with cash flow metrics.
    """
    if not ticker or not isinstance(ticker, str):
        raise ValueError("Ticker must be a non-empty string")
    if years <= 0:
        raise ValueError("years must be a positive integer")

    symbol = ticker.upper().strip()
    headers = _get_headers()
    url = f"{BASE_URL}/financials/cash-flow-statements"
    params = {
        "ticker": symbol,
        "limit": years,
        "period": period,
    }

    response = requests.get(url, headers=headers, params=params, timeout=10)
    if response.status_code != 200:
        error_msg = response.text or f"status {response.status_code}"
        try:
            error_data = response.json()
            error_msg = error_data.get("message") or error_data.get("error") or error_msg
        except Exception:
            pass
        raise requests.exceptions.RequestException(
            f"Failed to fetch cash flow statements for {symbol}: {error_msg}"
        )

    payload = response.json()
    # FinancialDatasets.ai returns cash_flow_statements array directly in response
    # See: https://docs.financialdatasets.ai/api-reference/endpoint/financials/cash-flow-statements
    if isinstance(payload, dict):
        statements = payload.get("cash_flow_statements") or payload.get("financials") or payload.get("data") or payload.get("items")
        if statements is None and "results" in payload:
            statements = payload["results"]
        if statements is None:
            for value in payload.values():
                if isinstance(value, list) and value:
                    statements = value
                    break
    elif isinstance(payload, list):
        statements = payload
    else:
        statements = None

    if not statements:
        raise ValueError(f"No cash flow statements returned for {symbol}")

    normalized: List[CashFlowStatement] = []
    for entry in statements:
        if not isinstance(entry, dict):
            continue
        
        # FinancialDatasets.ai API uses snake_case field names
        # Documentation: https://docs.financialdatasets.ai/api-reference/endpoint/financials/cash-flow-statements
        
        # Extract year from report_period (format: "2023-12-25")
        fiscal_year = None
        report_period = entry.get("report_period")
        if report_period and isinstance(report_period, str):
            try:
                fiscal_year = int(report_period.split("-")[0])
            except (ValueError, AttributeError):
                pass
        
        # API provides these fields directly (snake_case):
        # - net_cash_flow_from_operations (maps to operating_cash_flow)
        # - capital_expenditure (singular, not plural)
        # - free_cash_flow (provided directly by API!)
        # - net_cash_flow_from_investing (maps to investing_cash_flow)
        # - net_cash_flow_from_financing (maps to financing_cash_flow)
        # - change_in_cash_and_equivalents (maps to net_change_in_cash)
        
        operating_cash_flow = entry.get("net_cash_flow_from_operations")  # Primary: exact API field name
        if operating_cash_flow is None:
            # Fallback to camelCase variations
            operating_cash_flow = entry.get("operatingCashFlow") or entry.get("cashFromOperatingActivities")
        
        capital_expenditures = entry.get("capital_expenditure")  # API uses singular
        if capital_expenditures is None:
            capital_expenditures = entry.get("capital_expenditures") or entry.get("capitalExpenditure")
        # CapEx is often negative in cash flow statements, but we'll use as-is for calculation
        
        # API provides free_cash_flow directly!
        free_cash_flow = entry.get("free_cash_flow")
        # If not provided, calculate from operating_cash_flow - capital_expenditure
        if free_cash_flow is None and operating_cash_flow is not None:
            if capital_expenditures is not None:
                # CapEx is typically negative in cash flow, so add it (subtract negative = add)
                free_cash_flow = operating_cash_flow - abs(capital_expenditures) if capital_expenditures < 0 else operating_cash_flow - capital_expenditures
            else:
                free_cash_flow = operating_cash_flow
        
        investing_cash_flow = entry.get("net_cash_flow_from_investing")  # Primary: exact API field name
        if investing_cash_flow is None:
            investing_cash_flow = entry.get("cashFromInvestingActivities") or entry.get("investingCashFlow")
        
        financing_cash_flow = entry.get("net_cash_flow_from_financing")  # Primary: exact API field name
        if financing_cash_flow is None:
            financing_cash_flow = entry.get("cashFromFinancingActivities") or entry.get("financingCashFlow")
        
        net_change_in_cash = entry.get("change_in_cash_and_equivalents")  # Primary: exact API field name
        if net_change_in_cash is None:
            net_change_in_cash = entry.get("netChangeInCash") or entry.get("netChangeInCashAndCashEquivalents")
        
        model = CashFlowStatement(
            ticker=entry.get("ticker") or entry.get("symbol") or symbol,
            period=str(entry.get("period") or period),  # API uses: "annual", "quarterly", or "ttm"
            fiscal_year=int(fiscal_year) if fiscal_year is not None else None,
            fiscal_period=entry.get("fiscal_period"),  # API field: fiscal_period
            operating_cash_flow=operating_cash_flow,
            capital_expenditures=capital_expenditures,
            investing_cash_flow=investing_cash_flow,
            financing_cash_flow=financing_cash_flow,
            net_change_in_cash=net_change_in_cash,
            free_cash_flow=free_cash_flow,
            currency=entry.get("currency"),  # API field: currency
            raw=entry,
        )
        normalized.append(model)

    if not normalized:
        raise ValueError(f"Unable to parse cash flow statements for {symbol}")

    return normalized[:years]


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
