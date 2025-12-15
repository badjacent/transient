"""CLI entrypoint for DeskAgentOrchestrator."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.desk_agent.orchestrator import DeskAgentOrchestrator


def main() -> int:
    parser = argparse.ArgumentParser(description="Run desk agent scenarios")
    parser.add_argument("--scenario", help="Scenario name or path")
    parser.add_argument("--smoke-all", action="store_true", help="Run all scenarios sequentially")
    parser.add_argument("--output", help="Optional path to write report JSON")
    args = parser.parse_args()

    orch = DeskAgentOrchestrator()
    if args.smoke_all:
        summary = orch.smoke_all_scenarios()
        print(json.dumps(summary, indent=2))
        if args.output:
            Path(args.output).write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return 0 if summary.get("errors", 0) == 0 else 1

    if not args.scenario:
        parser.print_help()
        return 1
    report = orch.run_scenario(args.scenario)
    print(json.dumps(report, indent=2))
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
