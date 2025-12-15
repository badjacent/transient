"""CLI for refmaster normalization."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.refmaster.normalizer_agent import batch_normalize, export_equities


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Refmaster normalize identifiers")
    parser.add_argument("identifiers", nargs="*", help="Identifiers to normalize (e.g., 'AAPL US')")
    parser.add_argument("--batch-file", help="Path to file with one identifier per line")
    parser.add_argument("--top-k", type=int, default=5, help="Number of candidates to return")
    parser.add_argument("--export", help="Export loaded equities to path (csv/json)")
    args = parser.parse_args(argv)

    if args.export:
        fmt = "json" if Path(args.export).suffix.lower() == ".json" else "csv"
        out = export_equities(args.export, fmt=fmt)
        print(f"Exported equities to {out}")
        return 0

    inputs = list(args.identifiers or [])
    if args.batch_file:
        path = Path(args.batch_file)
        if not path.exists():
            print(f"batch file not found: {path}", file=sys.stderr)
            return 1
        inputs.extend([line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()])
    if not inputs:
        parser.print_help()
        return 1
    results = batch_normalize(inputs, top_k=args.top_k)
    for ident, matches in results.items():
        print(f"{ident}:")
        if not matches:
            print("  unknown")
            continue
        for res in matches:
            eq = res.equity
            print(f"  {eq.symbol} conf={res.confidence:.2f} ambiguous={res.ambiguous} exchange={eq.exchange}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
