#!/usr/bin/env python3
"""Interactive demonstration of refmaster ambiguity handling."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.refmaster.normalizer_agent import NormalizerAgent, normalize
from src.refmaster.schema import RefMasterEquity


def demo_ambiguity():
    """Demonstrate ambiguity detection with real examples."""

    # Scenario 1: Symbol substring ambiguity
    print("=" * 70)
    print("SCENARIO 1: Symbol Substring Ambiguity")
    print("=" * 70)
    print(
        "When input matches multiple equities (e.g., 'ABC' matches both 'ABC' and 'ABCD')"
    )
    print()

    equities = [
        RefMasterEquity(
            symbol="ABC",
            isin="US0000000001",
            cusip="000000000",
            currency="USD",
            exchange="NYSE",
            pricing_source="test",
        ),
        RefMasterEquity(
            symbol="ABCD",
            isin="US0000000002",
            cusip="000000001",
            currency="USD",
            exchange="NASDAQ",
            pricing_source="test",
        ),
    ]

    agent = NormalizerAgent(equities=equities)

    test_inputs = ["ABC", "ABCD", "ABC US"]

    for inp in test_inputs:
        print(f"Input: '{inp}'")
        result = agent.normalize(inp)
        print(f"  Results: {len(result)}")
        for i, r in enumerate(result, 1):
            ambiguous_marker = " ⚠️ AMBIGUOUS" if r.ambiguous else ""
            print(
                f"    {i}. {r.equity.symbol:6s} | conf={r.confidence:.2f} | {', '.join(r.reasons)}{ambiguous_marker}"
            )
        print()

    # Scenario 2: Exchange-only match (low confidence, but can be ambiguous)
    print("=" * 70)
    print("SCENARIO 2: Exchange-Only Match")
    print("=" * 70)
    print("When input only mentions exchange (e.g., 'NASDAQ'), multiple equities match")
    print()

    equities2 = [
        RefMasterEquity(
            symbol="AAPL",
            isin="",
            cusip="",
            currency="USD",
            exchange="NASDAQ",
            pricing_source="test",
        ),
        RefMasterEquity(
            symbol="MSFT",
            isin="",
            cusip="",
            currency="USD",
            exchange="NASDAQ",
            pricing_source="test",
        ),
        RefMasterEquity(
            symbol="GOOGL",
            isin="",
            cusip="",
            currency="USD",
            exchange="NASDAQ",
            pricing_source="test",
        ),
    ]

    # Lower reject threshold to allow exchange-only matches
    agent2 = NormalizerAgent(equities=equities2, thresholds={"reject": 0.2})

    print("Input: 'NASDAQ'")
    result = agent2.normalize("NASDAQ")
    print(f"  Results: {len(result)}")
    for i, r in enumerate(result, 1):
        ambiguous_marker = " ⚠️ AMBIGUOUS" if r.ambiguous else ""
        print(
            f"    {i}. {r.equity.symbol:6s} | conf={r.confidence:.2f} | {', '.join(r.reasons)}{ambiguous_marker}"
        )
    print(
        "  Note: Confidence (0.30) is below ambiguous_low (0.60), so no ambiguity flag"
    )
    print("  (Ambiguity only applies when confidence is in 0.6-0.85 range)")
    print()

    # Scenario 3: Real-world data from refmaster
    print("=" * 70)
    print("SCENARIO 3: Real Refmaster Data")
    print("=" * 70)
    print("Testing with actual refmaster_data.json")
    print()

    test_cases = [
        "AAPL",
        "AAPL US",
        "AAPL.OQ",
        "US0378331005",  # AAPL ISIN
        "Apple Inc NASDAQ",
    ]

    for inp in test_cases:
        result = normalize(inp, top_k=3)
        print(f"Input: '{inp}'")
        if result:
            top = result[0]
            ambiguous_marker = " ⚠️ AMBIGUOUS" if top.ambiguous else ""
            print(
                f"  Top match: {top.equity.symbol} (conf={top.confidence:.2f}, ambiguous={top.ambiguous}){ambiguous_marker}"
            )
            if top.ambiguous:
                print(f"  ⚠️  WARNING: Ambiguous match detected!")
                print(f"  Alternative candidates:")
                for r in result[1:]:
                    print(
                        f"    - {r.equity.symbol} (conf={r.confidence:.2f}, ambiguous={r.ambiguous})"
                    )
            elif len(result) > 1:
                print(f"  Alternative candidates:")
                for r in result[1:]:
                    print(
                        f"    - {r.equity.symbol} (conf={r.confidence:.2f}, ambiguous={r.ambiguous})"
                    )
        else:
            print("  No matches found")
        print()

    # Scenario 4: Ambiguity threshold boundaries
    print("=" * 70)
    print("SCENARIO 4: Ambiguity Threshold Boundaries")
    print("=" * 70)
    print("Demonstrating how threshold changes affect ambiguity detection")
    print()

    # Create equities with scores in ambiguous range
    equities3 = [
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
        RefMasterEquity(
            symbol="AAAC",
            isin="",
            cusip="",
            currency="USD",
            exchange="AMEX",
            pricing_source="test",
        ),
    ]

    # Default thresholds
    agent_default = NormalizerAgent(equities=equities3)
    print("Default thresholds (ambiguous_low=0.6, ambiguous_high=0.85):")
    result = agent_default.normalize("AAA")
    if result:
        print(f"  Input 'AAA' -> {len(result)} results")
        for r in result[:2]:
            print(
                f"    {r.equity.symbol}: conf={r.confidence:.2f}, ambiguous={r.ambiguous}"
            )
    print()

    # Narrower ambiguity range
    agent_narrow = NormalizerAgent(
        equities=equities3, thresholds={"ambiguous_low": 0.7, "ambiguous_high": 0.8}
    )
    print("Narrower ambiguity range (ambiguous_low=0.7, ambiguous_high=0.8):")
    result = agent_narrow.normalize("AAA")
    if result:
        print(f"  Input 'AAA' -> {len(result)} results")
        for r in result[:2]:
            print(
                f"    {r.equity.symbol}: conf={r.confidence:.2f}, ambiguous={r.ambiguous}"
            )
    print()

    # Summary
    print("=" * 70)
    print("KEY TAKEAWAYS")
    print("=" * 70)
    print(
        "1. Ambiguity is flagged when multiple results have confidence in 0.6-0.85 range"
    )
    print(
        "2. Exact matches (ISIN, CUSIP, CIK, exact symbol) have high confidence (>0.85) and are NOT ambiguous"
    )
    print(
        "3. Partial matches (substring, exchange-only) have lower confidence and CAN be ambiguous"
    )
    print("4. Downstream agents (OMS, Pricing) should warn users when ambiguous=True")
    print("5. Thresholds can be tuned to adjust sensitivity")


if __name__ == "__main__":
    demo_ambiguity()
