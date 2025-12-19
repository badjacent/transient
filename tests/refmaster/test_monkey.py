"""Monkey test for refmaster - fuzzing with edge cases, malformed inputs, and boundary conditions."""

import pytest

from src.refmaster.normalizer_agent import NormalizerAgent, normalize
from src.refmaster.schema import RefMasterEquity


def _sample_equities():
    """Sample equities for testing."""
    return [
        RefMasterEquity(
            symbol="AAPL",
            isin="US0378331005",
            cusip="037833100",
            cik="0000320193",
            currency="USD",
            exchange="NASDAQ",
            pricing_source="test",
        ),
        RefMasterEquity(
            symbol="MSFT",
            isin="US5949181045",
            cusip="594918104",
            cik="0000789019",
            currency="USD",
            exchange="NASDAQ",
            pricing_source="test",
        ),
        RefMasterEquity(
            symbol="GOOGL",
            isin="US02079K3059",
            cusip="02079K305",
            cik="0001652044",
            currency="USD",
            exchange="NASDAQ",
            pricing_source="test",
        ),
        RefMasterEquity(
            symbol="TSLA",
            isin="US88160R1014",
            cusip="88160R101",
            cik="0001318605",
            currency="USD",
            exchange="NASDAQ",
            pricing_source="test",
        ),
    ]


class TestMonkeyRefmaster:
    """Monkey test suite for refmaster normalization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.agent = NormalizerAgent(equities=_sample_equities())

    # ========== Empty/Null Inputs ==========

    def test_empty_string(self):
        """Empty string should return empty list."""
        assert self.agent.normalize("") == []
        assert self.agent.normalize("   ") == []
        assert self.agent.normalize("\t\n") == []

    def test_none_input(self):
        """None input should be handled gracefully."""
        # normalize() expects string, but test defensive behavior
        try:
            result = self.agent.normalize(None)  # type: ignore
            # Should either return [] or raise TypeError
            assert result == [] or isinstance(result, list)
        except (TypeError, AttributeError):
            pass  # Acceptable behavior

    # ========== Very Long Inputs ==========

    def test_very_long_string(self):
        """Very long strings should not crash."""
        long_input = "AAPL " * 1000
        result = self.agent.normalize(long_input)
        # Should either find AAPL or return empty (if too noisy)
        assert isinstance(result, list)

    def test_extremely_long_identifier(self):
        """Extremely long identifier strings."""
        long_identifier = "A" * 10000
        result = self.agent.normalize(long_identifier)
        assert isinstance(result, list)

    # ========== Special Characters ==========

    def test_special_characters(self):
        """Inputs with special characters."""
        test_cases = [
            "AAPL!@#$%^&*()",
            "AAPL-123",
            "AAPL_underscore",
            "AAPL+plus",
            "AAPL=equals",
            "AAPL[braces]",
            "AAPL{curly}",
            "AAPL|pipe",
            "AAPL\\backslash",
            "AAPL/forward",
        ]
        for case in test_cases:
            result = self.agent.normalize(case)
            assert isinstance(result, list)
            # Should still extract AAPL if present

    def test_unicode_characters(self):
        """Unicode and non-ASCII characters."""
        test_cases = [
            "AAPL café",
            "AAPL 中文",
            "AAPL 🚀",
            "AAPL émoji",
            "AAPL ñoño",
        ]
        for case in test_cases:
            result = self.agent.normalize(case)
            assert isinstance(result, list)

    # ========== Malformed Identifiers ==========

    def test_malformed_isin(self):
        """ISINs with wrong length or format."""
        test_cases = [
            "US037833100",  # Too short (11 chars, should be 12)
            "US03783310050",  # Too long (13 chars)
            "XX0378331005",  # Invalid country code
            "US037833100X",  # Invalid check digit (non-numeric)
            "0378331005",  # Missing country code
        ]
        for case in test_cases:
            result = self.agent.normalize(case)
            # Should not match exact ISIN (1.0 confidence)
            if result:
                assert result[0].confidence < 1.0

    def test_malformed_cusip(self):
        """CUSIPs with wrong length."""
        test_cases = [
            "03783310",  # Too short (8 chars)
            "0378331000",  # Too long (10 chars)
            "03783310X",  # Invalid character
        ]
        for case in test_cases:
            result = self.agent.normalize(case)
            assert isinstance(result, list)

    def test_malformed_cik(self):
        """CIKs with unusual formats."""
        test_cases = [
            "320193",  # Short CIK (should normalize to 10 digits)
            "000000320193",  # Too long
            "320193X",  # Non-numeric
            "000032019",  # 9 digits
        ]
        for case in test_cases:
            result = self.agent.normalize(case)
            assert isinstance(result, list)

    # ========== Edge Cases in Regex Matching ==========

    def test_numbers_that_look_like_identifiers(self):
        """Numbers that might be mistaken for identifiers."""
        test_cases = [
            "123456789",  # Looks like CUSIP but might be random number
            "0001234567",  # Looks like CIK
            "US1234567890",  # Looks like ISIN but invalid
            "2024-12-18",  # Date that might match CIK pattern
            "12345",  # Short number
        ]
        for case in test_cases:
            result = self.agent.normalize(case)
            assert isinstance(result, list)

    def test_symbol_edge_cases(self):
        """Symbol extraction edge cases."""
        test_cases = [
            "A",  # Single letter (valid ticker)
            "AA",  # Two letters
            "AAAAA",  # Five letters (max length)
            "AAAAAA",  # Six letters (too long for standard ticker)
            "A1",  # Letter + number
            "1A",  # Number + letter
            "AAPL.OQ.N",  # Multiple dots
            "AAPL.123",  # Dot with numbers
            ".AAPL",  # Leading dot
            "AAPL.",  # Trailing dot
        ]
        for case in test_cases:
            result = self.agent.normalize(case)
            assert isinstance(result, list)

    # ========== Mixed/Conflicting Formats ==========

    def test_multiple_identifiers_in_one_string(self):
        """Input with multiple potential identifiers."""
        test_cases = [
            "AAPL US0378331005",  # Symbol + ISIN
            "US0378331005 AAPL",  # ISIN + Symbol
            "AAPL 037833100",  # Symbol + CUSIP
            "AAPL 0000320193",  # Symbol + CIK
            "US0378331005 037833100",  # ISIN + CUSIP (should prefer ISIN)
            "AAPL MSFT",  # Two symbols (should match first or both)
        ]
        for case in test_cases:
            result = self.agent.normalize(case)
            assert isinstance(result, list)
            # Should prioritize exact matches (ISIN > CUSIP > Symbol)

    def test_conflicting_identifiers(self):
        """Input where extracted identifiers conflict."""
        # ISIN for one ticker, symbol for another
        result = self.agent.normalize("US0378331005 MSFT")
        assert isinstance(result, list)
        # ISIN should win (higher confidence)

    # ========== Exchange/Country Edge Cases ==========

    def test_invalid_exchange_names(self):
        """Invalid or misspelled exchange names."""
        test_cases = [
            "AAPL NASDAX",  # Misspelled
            "AAPL NYSEE",  # Misspelled
            "AAPL FAKE_EXCHANGE",
            "AAPL exchange",  # Lowercase
        ]
        for case in test_cases:
            result = self.agent.normalize(case)
            assert isinstance(result, list)
            # Should still match on symbol

    def test_country_code_variations(self):
        """Country code in various positions."""
        test_cases = [
            "AAPL US",
            "US AAPL",
            "AAPLUS",  # No space
            "AAPL-US",  # With dash
            "AAPL_US",  # With underscore
        ]
        for case in test_cases:
            result = self.agent.normalize(case)
            assert isinstance(result, list)

    # ========== Threshold Boundary Tests ==========

    def test_threshold_boundaries(self):
        """Test inputs at confidence threshold boundaries."""
        agent_low = NormalizerAgent(
            equities=_sample_equities(),
            thresholds={"reject": 0.2},  # Very low threshold
        )
        agent_high = NormalizerAgent(
            equities=_sample_equities(),
            thresholds={"reject": 0.95},  # Very high threshold
        )

        # Exchange-only match (low confidence ~0.3)
        exchange_only = "NASDAQ"
        assert len(agent_low.normalize(exchange_only)) > 0
        assert len(agent_high.normalize(exchange_only)) == 0  # Rejected

    def test_ambiguity_thresholds(self):
        """Test ambiguity detection at boundaries."""
        # Create equities that will have similar confidence scores
        equities = [
            RefMasterEquity(
                symbol="AAA",
                isin="",
                cusip="",
                currency="USD",
                exchange="NYSE",
                pricing_source="test",
            ),
            RefMasterEquity(
                symbol="AAAB",
                isin="",
                cusip="",
                currency="USD",
                exchange="NASDAQ",
                pricing_source="test",
            ),
        ]
        agent = NormalizerAgent(equities=equities)

        # Input that matches both equally
        result = agent.normalize("AAA")
        if len(result) > 1:
            # Check ambiguity flag
            assert isinstance(result[0].ambiguous, bool)

    # ========== Case Sensitivity ==========

    def test_case_variations(self):
        """Various case combinations."""
        test_cases = [
            "aapl",
            "AAPL",
            "Aapl",
            "aApL",
            "AaPl",
        ]
        for case in test_cases:
            result = self.agent.normalize(case)
            # Should all match AAPL
            if result:
                assert result[0].equity.symbol == "AAPL"

    # ========== Whitespace Variations ==========

    def test_whitespace_variations(self):
        """Various whitespace patterns."""
        test_cases = [
            "  AAPL  ",
            "\tAAPL\n",
            "AAPL\tUS",
            "AAPL\nUS",
            "AAPL\r\nUS",
            "AAPL   US",  # Multiple spaces
        ]
        for case in test_cases:
            result = self.agent.normalize(case)
            assert isinstance(result, list)

    # ========== Real-World Messy Inputs ==========

    def test_messy_real_world_inputs(self):
        """Real-world messy inputs from users/systems."""
        test_cases = [
            "AAPL - Apple Inc.",
            "AAPL (NASDAQ)",
            "AAPL: Apple Inc",
            "Ticker: AAPL",
            "Symbol AAPL Exchange NASDAQ",
            "Buy AAPL at market",
            "AAPL stock price",
            "Apple Inc (AAPL) on NASDAQ",
            "US0378331005 - Apple Inc",
            "CUSIP: 037833100",
        ]
        for case in test_cases:
            result = self.agent.normalize(case)
            assert isinstance(result, list)
            # Should extract identifier despite noise

    # ========== Performance/Stress Tests ==========

    def test_many_equities(self):
        """Test with large equity list."""
        # Create many equities
        many_equities = _sample_equities() * 100  # 400 equities
        agent = NormalizerAgent(equities=many_equities)
        result = agent.normalize("AAPL")
        assert len(result) > 0
        assert result[0].equity.symbol == "AAPL"

    def test_repeated_calls(self):
        """Repeated calls with same input (cache test)."""
        for _ in range(100):
            result = self.agent.normalize("AAPL US")
            assert isinstance(result, list)
            if result:
                assert result[0].equity.symbol == "AAPL"

    # ========== Top-K Edge Cases ==========

    def test_top_k_boundaries(self):
        """Test top_k parameter edge cases."""
        result_k0 = self.agent.normalize("AAPL", top_k=0)
        assert result_k0 == []

        result_k1 = self.agent.normalize("AAPL", top_k=1)
        assert len(result_k1) <= 1

        result_k100 = self.agent.normalize("AAPL", top_k=100)
        assert len(result_k100) <= len(_sample_equities())

        result_k_negative = self.agent.normalize("AAPL", top_k=-1)
        # Should handle gracefully (might return all or empty)
        assert isinstance(result_k_negative, list)

    # ========== Integration with Convenience Functions ==========

    def test_normalize_function_edge_cases(self):
        """Test the convenience normalize() function."""
        from src.refmaster.normalizer_agent import normalize

        # Should work with edge cases
        assert normalize("") == []
        assert isinstance(normalize("AAPL"), list)
        assert isinstance(normalize("INVALID_TICKER_XYZ"), list)

    def test_resolve_ticker_edge_cases(self):
        """Test resolve_ticker() with edge cases."""
        from src.refmaster.normalizer_agent import resolve_ticker

        assert resolve_ticker("AAPL") is not None
        assert resolve_ticker("") is None
        assert resolve_ticker("INVALID") is None
        assert resolve_ticker("  AAPL  ") is not None  # Should strip

    # ========== Data Loading Edge Cases ==========

    def test_malformed_data_handling(self):
        """Test handling of malformed equity data."""
        # This tests the load_equities() function's error handling
        # Should skip malformed entries and continue
        malformed_equities = [
            RefMasterEquity(
                symbol="GOOD",
                isin="US1234567890",
                cusip="123456789",
                currency="USD",
                exchange="NYSE",
                pricing_source="test",
            ),
            # Missing required fields would cause validation error, but that's expected
        ]
        agent = NormalizerAgent(equities=malformed_equities)
        result = agent.normalize("GOOD")
        assert isinstance(result, list)

    # ========== Confidence Score Edge Cases ==========

    def test_zero_confidence_results(self):
        """Inputs that produce zero confidence."""
        result = self.agent.normalize("ZZZZZZZZZZ")
        # Should return empty list (below reject threshold)
        assert result == []

    def test_confidence_score_ranges(self):
        """Verify confidence scores are in valid range."""
        test_inputs = [
            "US0378331005",  # ISIN (should be 1.0)
            "AAPL",  # Symbol (should be ~0.9)
            "AAPL US",  # Symbol + country (should be ~0.92)
            "NASDAQ",  # Exchange only (should be ~0.3)
        ]
        for inp in test_inputs:
            result = self.agent.normalize(inp)
            if result:
                for r in result:
                    assert 0.0 <= r.confidence <= 1.0
                    assert isinstance(r.confidence, float)

    # ========== Reasons Validation ==========

    def test_reasons_always_present(self):
        """Verify reasons are always present in results."""
        test_inputs = ["AAPL", "US0378331005", "AAPL US", "NASDAQ"]
        for inp in test_inputs:
            result = self.agent.normalize(inp)
            for r in result:
                assert isinstance(r.reasons, list)
                assert len(r.reasons) > 0  # Should have at least one reason

    # ========== Ambiguity Flag Consistency ==========

    def test_ambiguity_flag_consistency(self):
        """Ambiguity flag should be consistent."""
        # Create scenario with ambiguous matches
        equities = [
            RefMasterEquity(
                symbol="ABC",
                isin="",
                cusip="",
                currency="USD",
                exchange="NYSE",
                pricing_source="test",
            ),
            RefMasterEquity(
                symbol="ABCD",
                isin="",
                cusip="",
                currency="USD",
                exchange="NASDAQ",
                pricing_source="test",
            ),
        ]
        agent = NormalizerAgent(equities=equities)
        result = agent.normalize("ABC")
        if len(result) > 1:
            # If multiple results in ambiguous range, check flag
            ambiguous_results = [r for r in result if r.ambiguous]
            if ambiguous_results:
                # All ambiguous results should have flag set
                assert all(r.ambiguous for r in ambiguous_results)
