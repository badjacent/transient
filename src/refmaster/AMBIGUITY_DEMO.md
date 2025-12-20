# Refmaster Ambiguity Handling - Demonstration Guide

## Overview

Refmaster detects ambiguity when multiple equity candidates have similar confidence scores in the "ambiguous" range (0.6-0.85). This is critical for downstream agents (OMS, Pricing) to warn users when a ticker match is uncertain.

## How Ambiguity Works

**Ambiguity Detection Logic**:

1. Results are scored and sorted by confidence (highest first)
2. If the **top result** has confidence ≤ `ambiguous_high` (0.85) AND
3. The **second result** has confidence ≥ `ambiguous_low` (0.6)
4. Then **all results** in the ambiguous range (≥ 0.6) are flagged with `ambiguous=True`

**Default Thresholds**:

- `ambiguous_low`: 0.6
- `ambiguous_high`: 0.85
- `reject`: 0.4 (below this, results are discarded)

## Demonstration Scenarios

### Scenario 1: Partial Symbol Match (Most Common Ambiguity)

**Setup**: Two equities with similar symbols where one is a substring of the other.

```python
from src.refmaster.normalizer_agent import NormalizerAgent
from src.refmaster.schema import RefMasterEquity

# Create ambiguous scenario
equities = [
    RefMasterEquity(
        symbol="ABC",
        isin="US0000000001",
        cusip="000000000",
        currency="USD",
        exchange="NYSE",
        pricing_source="test"
    ),
    RefMasterEquity(
        symbol="ABCD",
        isin="US0000000002",
        cusip="000000001",
        currency="USD",
        exchange="NASDAQ",
        pricing_source="test"
    ),
]

agent = NormalizerAgent(equities=equities)

# This input matches both (ABC is substring of ABCD)
result = agent.normalize("ABC")

print(f"Results: {len(result)}")
for r in result:
    print(f"  {r.equity.symbol}: confidence={r.confidence:.2f}, ambiguous={r.ambiguous}, reasons={r.reasons}")
```

**Expected Output**:

```
Results: 2
  ABC: confidence=0.90, ambiguous=False, reasons=['symbol_exact']
  ABCD: confidence=0.70, ambiguous=True, reasons=['symbol_in_text']
```

**What to Show**:

- Both results are returned
- The exact match (ABC) has higher confidence and is NOT ambiguous
- The partial match (ABCD) has lower confidence and IS ambiguous
- Both have confidence in the ambiguous range (0.6-0.85), so the lower one is flagged

---

### Scenario 2: Exchange-Only Match (Low Confidence Ambiguity)

**Setup**: Multiple equities on the same exchange, input only mentions exchange.

```python
equities = [
    RefMasterEquity(symbol="AAPL", isin="", cusip="", currency="USD", exchange="NASDAQ", pricing_source="test"),
    RefMasterEquity(symbol="MSFT", isin="", cusip="", currency="USD", exchange="NASDAQ", pricing_source="test"),
    RefMasterEquity(symbol="GOOGL", isin="", cusip="", currency="USD", exchange="NASDAQ", pricing_source="test"),
]

agent = NormalizerAgent(equities=equities, thresholds={"reject": 0.2})  # Lower reject to allow exchange-only

result = agent.normalize("NASDAQ")

print(f"Results: {len(result)}")
for r in result:
    print(f"  {r.equity.symbol}: confidence={r.confidence:.2f}, ambiguous={r.ambiguous}, reasons={r.reasons}")
```

**Expected Output**:

```
Results: 3
  AAPL: confidence=0.30, ambiguous=False, reasons=['exchange_only']
  MSFT: confidence=0.30, ambiguous=False, reasons=['exchange_only']
  GOOGL: confidence=0.30, ambiguous=False, reasons=['exchange_only']
```

**Note**: In this case, confidence (0.3) is below `ambiguous_low` (0.6), so ambiguity flag is NOT set. This demonstrates that ambiguity only applies when scores are in the 0.6-0.85 range.

---

### Scenario 3: Symbol Substring Ambiguity (Real-World Case)

**Setup**: Real tickers where one symbol contains another.

```python
equities = [
    RefMasterEquity(symbol="AA", isin="US0000000001", cusip="000000000", currency="USD", exchange="NYSE", pricing_source="test"),
    RefMasterEquity(symbol="AAA", isin="US0000000002", cusip="000000001", currency="USD", exchange="NASDAQ", pricing_source="test"),
    RefMasterEquity(symbol="AAAA", isin="US0000000003", cusip="000000002", currency="USD", exchange="AMEX", pricing_source="test"),
]

agent = NormalizerAgent(equities=equities)

# Input "AA" matches all three (AA is substring of AAA and AAAA)
result = agent.normalize("AA")

print(f"Input: 'AA'")
print(f"Results: {len(result)}")
for i, r in enumerate(result, 1):
    print(f"  {i}. {r.equity.symbol}: confidence={r.confidence:.2f}, ambiguous={r.ambiguous}, reasons={r.reasons}")
```

**Expected Output**:

```
Input: 'AA'
Results: 3
  1. AA: confidence=0.90, ambiguous=False, reasons=['symbol_exact']
  2. AAA: confidence=0.70, ambiguous=True, reasons=['symbol_in_text']
  3. AAAA: confidence=0.70, ambiguous=True, reasons=['symbol_in_text']
```

**What to Show**:

- Exact match (AA) has highest confidence and is NOT ambiguous
- Partial matches (AAA, AAAA) have lower confidence (0.70) in ambiguous range
- Both partial matches are flagged as ambiguous
- This is the correct behavior: user should be warned about ambiguity

---

### Scenario 4: Company Name Ambiguity

**Setup**: Company names that partially match multiple equities.

```python
equities = [
    RefMasterEquity(symbol="AMZN", isin="", cusip="", currency="USD", exchange="NASDAQ", pricing_source="test"),
    RefMasterEquity(symbol="AMZNX", isin="", cusip="", currency="USD", exchange="NYSE", pricing_source="test"),
]

agent = NormalizerAgent(equities=equities, thresholds={"reject": 0.2})

# Company name that might match both
result = agent.normalize("Amazon Inc NASDAQ")

print(f"Input: 'Amazon Inc NASDAQ'")
print(f"Results: {len(result)}")
for r in result:
    print(f"  {r.equity.symbol}: confidence={r.confidence:.2f}, ambiguous={r.ambiguous}, reasons={r.reasons}")
```

**Expected Output**:

```
Input: 'Amazon Inc NASDAQ'
Results: 2
  AMZN: confidence=0.95, ambiguous=False, reasons=['symbol_in_text', 'exchange_match']
  AMZNX: confidence=0.70, ambiguous=True, reasons=['symbol_in_text']
```

**What to Show**:

- Exchange match boosts confidence for AMZN (0.95 > 0.85, so NOT ambiguous)
- AMZNX has lower confidence (0.70) in ambiguous range
- Exchange matching helps disambiguate

---

### Scenario 5: CIK Ambiguity (Rare but Possible)

**Setup**: CIKs that are similar or partial matches.

```python
equities = [
    RefMasterEquity(symbol="TICK1", isin="", cusip="", cik="0000123456", currency="USD", exchange="NYSE", pricing_source="test"),
    RefMasterEquity(symbol="TICK2", isin="", cusip="", cik="0000123457", currency="USD", exchange="NASDAQ", pricing_source="test"),
]

agent = NormalizerAgent(equities=equities)

# Partial CIK match (if input is malformed)
result = agent.normalize("123456")  # Missing leading zeros

print(f"Input: '123456'")
print(f"Results: {len(result)}")
for r in result:
    print(f"  {r.equity.symbol}: confidence={r.confidence:.2f}, ambiguous={r.ambiguous}, reasons={r.reasons}")
```

**Note**: CIK exact matches have very high confidence (0.95), so they rarely trigger ambiguity. This scenario is more theoretical.

---

## Interactive Demonstration Script

Save this as `demo_ambiguity.py`:

```python
#!/usr/bin/env python3
"""Interactive demonstration of refmaster ambiguity handling."""

from src.refmaster.normalizer_agent import NormalizerAgent
from src.refmaster.schema import RefMasterEquity


def demo_ambiguity():
    """Demonstrate ambiguity detection with real examples."""

    # Scenario: Symbol substring ambiguity
    print("=" * 60)
    print("SCENARIO 1: Symbol Substring Ambiguity")
    print("=" * 60)

    equities = [
        RefMasterEquity(
            symbol="ABC",
            isin="US0000000001",
            cusip="000000000",
            currency="USD",
            exchange="NYSE",
            pricing_source="test"
        ),
        RefMasterEquity(
            symbol="ABCD",
            isin="US0000000002",
            cusip="000000001",
            currency="USD",
            exchange="NASDAQ",
            pricing_source="test"
        ),
    ]

    agent = NormalizerAgent(equities=equities)

    test_inputs = ["ABC", "ABCD", "ABC US"]

    for inp in test_inputs:
        print(f"\nInput: '{inp}'")
        result = agent.normalize(inp)
        print(f"  Results: {len(result)}")
        for i, r in enumerate(result, 1):
            ambiguous_marker = " ⚠️ AMBIGUOUS" if r.ambiguous else ""
            print(f"    {i}. {r.equity.symbol:6s} | conf={r.confidence:.2f} | {', '.join(r.reasons)}{ambiguous_marker}")

    # Scenario: Exchange-only ambiguity
    print("\n" + "=" * 60)
    print("SCENARIO 2: Exchange-Only Match (Low Confidence)")
    print("=" * 60)

    equities2 = [
        RefMasterEquity(symbol="AAPL", isin="", cusip="", currency="USD", exchange="NASDAQ", pricing_source="test"),
        RefMasterEquity(symbol="MSFT", isin="", cusip="", currency="USD", exchange="NASDAQ", pricing_source="test"),
        RefMasterEquity(symbol="GOOGL", isin="", cusip="", currency="USD", exchange="NASDAQ", pricing_source="test"),
    ]

    agent2 = NormalizerAgent(equities=equities2, thresholds={"reject": 0.2})

    print("\nInput: 'NASDAQ'")
    result = agent2.normalize("NASDAQ")
    print(f"  Results: {len(result)}")
    for i, r in enumerate(result, 1):
        ambiguous_marker = " ⚠️ AMBIGUOUS" if r.ambiguous else ""
        print(f"    {i}. {r.equity.symbol:6s} | conf={r.confidence:.2f} | {', '.join(r.reasons)}{ambiguous_marker}")
    print("  Note: Confidence (0.30) is below ambiguous_low (0.60), so no ambiguity flag")

    # Scenario: Real-world data
    print("\n" + "=" * 60)
    print("SCENARIO 3: Real Refmaster Data")
    print("=" * 60)

    from src.refmaster.normalizer_agent import normalize

    # Test with actual refmaster data
    test_cases = [
        "AAPL",
        "AAPL US",
        "AAPL.OQ",
        "US0378331005",  # AAPL ISIN
        "Apple Inc NASDAQ",
    ]

    for inp in test_cases:
        result = normalize(inp, top_k=3)
        print(f"\nInput: '{inp}'")
        if result:
            print(f"  Top match: {result[0].equity.symbol} (conf={result[0].confidence:.2f}, ambiguous={result[0].ambiguous})")
            if result[0].ambiguous:
                print(f"  ⚠️  WARNING: Ambiguous match detected!")
                print(f"  Alternative candidates:")
                for r in result[1:]:
                    print(f"    - {r.equity.symbol} (conf={r.confidence:.2f})")
        else:
            print("  No matches found")


if __name__ == "__main__":
    demo_ambiguity()
```

Run it:

```bash
python3 demo_ambiguity.py
```

---

## Key Points to Demonstrate

### 1. **Ambiguity Flag is Set Correctly**

- ✅ When multiple results have confidence in 0.6-0.85 range
- ✅ Only results in that range are flagged (not the top one if it's > 0.85)
- ✅ Empty results (below reject threshold) are not ambiguous (they're just rejected)

### 2. **Confidence Hierarchy**

Show the confidence scoring:

- **ISIN exact**: 1.0 (never ambiguous)
- **CUSIP/CIK exact**: 0.95 (rarely ambiguous)
- **Symbol exact**: 0.9 (rarely ambiguous)
- **Symbol + exchange/country**: 0.92-0.95 (rarely ambiguous)
- **Symbol substring**: 0.7 (often ambiguous)
- **Exchange only**: 0.3 (below ambiguous range, but can be ambiguous if threshold lowered)

### 3. **Downstream Impact**

Show how OMS agent uses ambiguity:

```python
from src.oms import OMSAgent

oms = OMSAgent()
result = oms.run({
    "ticker": "ABC",  # Ambiguous input
    "quantity": 100,
    "price": 150.00,
    "currency": "USD",
    "counterparty": "MS",
    "trade_dt": "2025-12-17",
    "settle_dt": "2025-12-19"
})

# Check for ambiguity warning
for issue in result.get("issues", []):
    if "ambiguous" in issue.get("message", "").lower():
        print(f"⚠️  Ambiguity detected: {issue['message']}")
```

---

## Quick Test Commands

```python
# Test ambiguity detection
from src.refmaster.normalizer_agent import NormalizerAgent
from src.refmaster.schema import RefMasterEquity

equities = [
    RefMasterEquity(symbol="ABC", isin="", cusip="", currency="USD", exchange="NYSE", pricing_source="test"),
    RefMasterEquity(symbol="ABCD", isin="", cusip="", currency="USD", exchange="NASDAQ", pricing_source="test"),
]

agent = NormalizerAgent(equities=equities)
result = agent.normalize("ABC")

# Check ambiguity
print(f"Top result: {result[0].equity.symbol}, ambiguous={result[0].ambiguous}")
if len(result) > 1:
    print(f"Second result: {result[1].equity.symbol}, ambiguous={result[1].ambiguous}")
```

---

## What Makes a Good Ambiguity Demo

1. **Clear Visual Output**: Show confidence scores side-by-side
2. **Multiple Scenarios**: Different types of ambiguity (substring, exchange-only, etc.)
3. **Real-World Examples**: Use actual ticker patterns that could occur
4. **Downstream Impact**: Show how OMS/Pricing agents handle ambiguous results
5. **Threshold Tuning**: Demonstrate how changing thresholds affects ambiguity detection

The key is showing that refmaster **surfaces uncertainty** rather than silently picking one, allowing downstream systems to warn users appropriately.
