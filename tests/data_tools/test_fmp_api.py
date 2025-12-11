import os

import pytest
from dotenv import load_dotenv

from src.data_tools.fmp_api import get_security_identifiers
from src.data_tools.schemas import Equity

load_dotenv()


def test_get_security_identifiers_smoke():
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        pytest.skip("FMP_API_KEY not set in environment")
    eq = get_security_identifiers("AAPL")
    assert isinstance(eq, Equity)
    assert eq.symbol == "AAPL"
    # CUSIP/ISIN may be missing depending on plan; ensure no exceptions and strings returned
    assert isinstance(eq.cusip, str)
    assert isinstance(eq.isin, str)
    assert isinstance(eq.currency, str)
