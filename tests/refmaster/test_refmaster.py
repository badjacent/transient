"""Tests for RefMaster and NormalizerAgent with ambiguous cases."""

import pytest
from src.refmaster.refmaster import RefMaster, NormalizerAgent
from src.data_tools.schemas import Equity


class TestRefMaster:
    """Basic tests for RefMaster."""

    def test_loads_equities(self):
        """Test that RefMaster loads equities from data file."""
        rm = RefMaster()
        assert len(rm.equities) > 0
        assert all(isinstance(eq, Equity) for eq in rm.equities)

    def test_symbols(self):
        """Test that symbols() returns list of ticker symbols."""
        rm = RefMaster()
        symbols = rm.symbols()
        assert isinstance(symbols, list)
        assert len(symbols) > 0
        assert "AAPL" in symbols


class TestNormalizerAgentExactMatches:
    """Tests for exact, high-confidence matches."""

    def test_exact_symbol_match(self):
        """Test exact ticker symbol match."""
        agent = NormalizerAgent()
        matches = agent.normalize("AAPL")
        
        assert len(matches) > 0
        assert matches[0][0].symbol == "AAPL"
        assert matches[0][1] >= 0.9  # High confidence for exact match

    def test_exact_isin_match(self):
        """Test exact ISIN match (highest confidence)."""
        agent = NormalizerAgent()
        matches = agent.normalize("US0378331005")
        
        assert len(matches) > 0
        assert matches[0][0].isin == "US0378331005"
        assert matches[0][1] == 1.0  # Perfect confidence for ISIN

    def test_exact_cusip_match(self):
        """Test exact CUSIP match."""
        agent = NormalizerAgent()
        # Get AAPL's CUSIP from refmaster
        rm = RefMaster()
        aapl = next(eq for eq in rm.equities if eq.symbol == "AAPL")
        matches = agent.normalize(aapl.cusip)
        
        assert len(matches) > 0
        assert matches[0][0].cusip == aapl.cusip
        assert matches[0][1] >= 0.95  # Very high confidence for CUSIP

    def test_exact_cik_match(self):
        """Test exact CIK match."""
        agent = NormalizerAgent()
        # Get AAPL's CIK from refmaster
        rm = RefMaster()
        aapl = next(eq for eq in rm.equities if eq.symbol == "AAPL")
        if aapl.cik:
            matches = agent.normalize(aapl.cik)
            
            assert len(matches) > 0
            assert matches[0][0].cik == aapl.cik
            assert matches[0][1] >= 0.95  # Very high confidence for CIK

    def test_symbol_with_country_code(self):
        """Test symbol with country code (e.g., 'AAPL US')."""
        agent = NormalizerAgent()
        matches = agent.normalize("AAPL US")
        
        assert len(matches) > 0
        assert matches[0][0].symbol == "AAPL"
        assert matches[0][1] >= 0.9

    def test_symbol_with_exchange_suffix(self):
        """Test symbol with exchange suffix (e.g., 'AAPL.OQ')."""
        agent = NormalizerAgent()
        matches = agent.normalize("AAPL.OQ")
        
        assert len(matches) > 0
        assert matches[0][0].symbol == "AAPL"
        assert matches[0][1] >= 0.9


class TestNormalizerAgentAmbiguousCases:
    """Tests for ambiguous cases with multiple matches or low confidence."""

    def test_exchange_only_match_low_confidence(self):
        """Test that exchange-only matches have low confidence."""
        agent = NormalizerAgent()
        matches = agent.normalize("NASDAQ")
        
        # Should match multiple NASDAQ-listed equities
        assert len(matches) > 1
        # All matches should have low confidence (exchange-only)
        for equity, score in matches:
            assert score <= 0.3
            assert "NASDAQ" in equity.exchange.upper()

    def test_partial_symbol_match(self):
        """Test partial symbol match (substring)."""
        agent = NormalizerAgent()
        # "AAP" could match "AAPL" as substring
        matches = agent.normalize("AAP")
        
        # Should find AAPL if it exists
        aapl_matches = [m for m in matches if m[0].symbol == "AAPL"]
        if aapl_matches:
            # Substring match should have lower confidence than exact
            assert aapl_matches[0][1] < 0.9

    def test_word_boundary_symbol_match(self):
        """Test word boundary symbol match (better than substring)."""
        agent = NormalizerAgent()
        # "AAPL stock" should match AAPL with word boundary
        matches = agent.normalize("AAPL stock")
        
        assert len(matches) > 0
        aapl_match = next((m for m in matches if m[0].symbol == "AAPL"), None)
        if aapl_match:
            # Word boundary match should have good confidence
            assert aapl_match[1] >= 0.85

    def test_company_name_with_exchange(self):
        """Test company name with exchange (low confidence, exchange match only)."""
        agent = NormalizerAgent()
        matches = agent.normalize("Apple Inc NASDAQ")
        
        # Should match NASDAQ equities, but low confidence since we don't have company names
        assert len(matches) > 0
        # All should be NASDAQ-listed
        for equity, score in matches:
            assert "NASDAQ" in equity.exchange.upper()
            # Low confidence since we're only matching on exchange
            assert score <= 0.3

    def test_multiple_candidates_ranked(self):
        """Test that multiple candidates are properly ranked by confidence."""
        agent = NormalizerAgent()
        # "NASDAQ" should return many matches, all ranked by confidence
        matches = agent.normalize("NASDAQ")
        
        assert len(matches) > 1
        # Verify they're sorted by confidence (descending)
        scores = [score for _, score in matches]
        assert scores == sorted(scores, reverse=True)
        # All scores should be the same for exchange-only matches
        assert all(s <= 0.3 for s in scores)

    def test_no_match_returns_empty(self):
        """Test that unknown input returns empty list."""
        agent = NormalizerAgent()
        matches = agent.normalize("XYZ123UNKNOWN")
        
        assert len(matches) == 0

    def test_symbol_with_exchange_bonus(self):
        """Test that symbol + exchange match gets bonus confidence."""
        agent = NormalizerAgent()
        rm = RefMaster()
        aapl = next(eq for eq in rm.equities if eq.symbol == "AAPL")
        
        # Match symbol with matching exchange
        matches = agent.normalize(f"AAPL {aapl.exchange}")
        
        assert len(matches) > 0
        aapl_match = next((m for m in matches if m[0].symbol == "AAPL"), None)
        if aapl_match:
            # Should have higher confidence than symbol-only
            assert aapl_match[1] >= 0.95


class TestNormalizerAgentEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_string(self):
        """Test that empty string returns empty results."""
        agent = NormalizerAgent()
        matches = agent.normalize("")
        assert len(matches) == 0

    def test_whitespace_only(self):
        """Test that whitespace-only input returns empty results."""
        agent = NormalizerAgent()
        matches = agent.normalize("   ")
        assert len(matches) == 0

    def test_case_insensitive(self):
        """Test that matching is case-insensitive."""
        agent = NormalizerAgent()
        matches_lower = agent.normalize("aapl")
        matches_upper = agent.normalize("AAPL")
        
        assert len(matches_lower) > 0
        assert len(matches_upper) > 0
        assert matches_lower[0][0].symbol == matches_upper[0][0].symbol

    def test_cik_with_leading_zeros(self):
        """Test CIK matching with various leading zero formats."""
        agent = NormalizerAgent()
        rm = RefMaster()
        aapl = next(eq for eq in rm.equities if eq.symbol == "AAPL")
        
        if aapl.cik:
            # Test with full 10-digit CIK
            matches1 = agent.normalize(aapl.cik)
            # Test with CIK without leading zeros
            cik_no_zeros = aapl.cik.lstrip("0")
            matches2 = agent.normalize(cik_no_zeros)
            
            # Both should match AAPL
            if matches1:
                assert matches1[0][0].symbol == "AAPL"
            if matches2:
                assert matches2[0][0].symbol == "AAPL"

    def test_isin_partial_match(self):
        """Test partial ISIN match (CUSIP portion)."""
        agent = NormalizerAgent()
        rm = RefMaster()
        aapl = next(eq for eq in rm.equities if eq.symbol == "AAPL")
        
        # Use the CUSIP part of the ISIN
        if aapl.isin.startswith("US") and len(aapl.isin) >= 11:
            cusip_part = aapl.isin[2:11]  # Skip "US" prefix and check digit
            matches = agent.normalize(cusip_part)
            
            # Should match AAPL with good confidence (CUSIP match)
            aapl_matches = [m for m in matches if m[0].symbol == "AAPL"]
            if aapl_matches:
                assert aapl_matches[0][1] >= 0.95


class TestNormalizerAgentMultipleMatches:
    """Tests for scenarios with multiple possible matches."""

    def test_all_nasdaq_equities_match_exchange(self):
        """Test that exchange query returns all equities from that exchange."""
        agent = NormalizerAgent()
        rm = RefMaster()
        
        # Get all NASDAQ equities
        nasdaq_equities = [eq for eq in rm.equities if "NASDAQ" in eq.exchange.upper()]
        
        if nasdaq_equities:
            matches = agent.normalize("NASDAQ")
            
            # Should match all NASDAQ equities
            matched_symbols = {m[0].symbol for m in matches}
            nasdaq_symbols = {eq.symbol for eq in nasdaq_equities}
            
            # All NASDAQ equities should be in matches
            assert nasdaq_symbols.issubset(matched_symbols)

    def test_confidence_decreases_with_ambiguity(self):
        """Test that ambiguous inputs have lower confidence scores."""
        agent = NormalizerAgent()
        
        # Exact match should have high confidence
        exact_matches = agent.normalize("AAPL")
        exact_confidence = exact_matches[0][1] if exact_matches else 0.0
        
        # Exchange-only match should have lower confidence
        exchange_matches = agent.normalize("NASDAQ")
        exchange_confidence = exchange_matches[0][1] if exchange_matches else 0.0
        
        assert exact_confidence > exchange_confidence

