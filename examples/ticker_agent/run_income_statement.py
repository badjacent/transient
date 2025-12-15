"""Example script that queries the ticker agent for a multi-year revenue summary."""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.ticker_agent import ticker_agent  # noqa: E402


def main() -> None:
   #  prompt = "Summarize the last 4 years of revenue for NVDA."
    prompt = "Give me a quick explanation of TSLA fundamentals and risk trends before my investor call in 10 min."
    result = ticker_agent.run(prompt)

    print("Question:", prompt)
    print("\nResult (JSON):")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
