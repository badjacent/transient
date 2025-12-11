"""LLM-assisted intent schema builder from seed questions.

This module prepares a prompt with seed questions, asks an LLM to propose
intents and slots, and parses the JSON reply into IntentDef structures.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

import requests
from dotenv import load_dotenv

from src.desk_agent.intents_loader import IntentDef

load_dotenv()


DEFAULT_SYSTEM_PROMPT = (
    "You are an intent schema builder for a financial desk agent. "
    "Given user seed questions, propose a small list of intents with slot names. "
    "Respond ONLY with JSON: {\"intents\": [{\"name\": str, \"description\": str, "
    "\"slots\": [str...], \"seeds\": [str...]}]}."
)


def _get_llm_api_key() -> str:
    api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("LLM_API_KEY/OPENAI_API_KEY not set in environment.")
    return api_key


def _get_llm_endpoint() -> str:
    endpoint = os.getenv("LLM_API_URL") or os.getenv("OPENAI_API_URL")
    if not endpoint:
        # Default to OpenAI chat completions endpoint
        endpoint = "https://api.openai.com/v1/chat/completions"
    return endpoint


def _call_llm_chat(messages: List[dict], model: str) -> str:
    """Thin wrapper around a chat completion API."""
    api_key = _get_llm_api_key()
    endpoint = _get_llm_endpoint()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
    }
    resp = requests.post(endpoint, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    choice = data["choices"][0]["message"]["content"]
    return choice


def _parse_intents_json(raw_text: str) -> List[IntentDef]:
    """Parse LLM JSON output into intent definitions."""
    data = json.loads(raw_text)
    intents = data.get("intents", [])
    return [
        IntentDef(
            name=item["name"],
            description=item.get("description", ""),
            slots=item.get("slots", []),
            seeds=item.get("seeds", []),
        )
        for item in intents
        if isinstance(item, dict) and "name" in item
    ]


def build_intents_from_seeds(seeds: List[str], model: str) -> List[IntentDef]:
    """Ask an LLM to propose intents/slots from seed questions."""
    user_prompt = (
        "Seed questions:\n"
        + "\n".join(f"- {q}" for q in seeds)
        + "\nReturn JSON only with intents, descriptions, slots, and the seeds they map to."
    )
    messages = [
        {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    raw = _call_llm_chat(messages, model=model)
    return _parse_intents_json(raw)


def write_intents_file(intents: List[IntentDef], output_path: str | Path) -> None:
    """Persist intents to a JSON data file."""
    payload = {"intents": intents}
    Path(output_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _default_seeds() -> List[str]:
    """Seed questions, including synthetic variants per intent."""
    financials_seeds = [
        "Summarize the last 4 years of revenue for this ticker.",
        "Show me the revenue trend over the past four fiscal years for the company mentioned.",
        "How has revenue changed year over year for the last four years for this equity?",
        "Give me revenue totals for each of the past four fiscal years for the requested ticker.",
        "Summarize revenue growth across the previous four reporting years for the company.",
        "Provide a 4-year revenue history for the specified ticker.",
        "List revenue for each of the last four years and note any growth/decline for this stock.",
        "What are the revenue figures for the past four annual periods for the named company?",
        "Pull the last four fiscal-year revenues for the referenced ticker and summarize.",
        "Show revenue progression for the most recent four years for this equity.",
        "Compare revenue across the last four fiscal years for the company in question.",
    ]
    vol_seeds = [
        "Compare realized vol over the last 90 days to the implied vol at issuance of this convertible.",
        "Check realized equity vol for the past 90 days versus the convert's issuance implied vol; use a placeholder if implied is missing.",
        "How does 90d realized vol on the underlying compare to implied at the convertible launch?",
        "Contrast trailing 90-day realized vol with implied vol when the convert priced.",
        "Benchmark 90d realized stock vol versus implied vol at issuance for the convertible; allow fallback if implied is unavailable.",
    ]
    perf_seeds = [
        "Summarize 1M, 3M, and YTD returns for this ticker.",
        "Give me recent performance for the stock over the last month, quarter, and year to date.",
        "Show trailing returns (1M/3M/YTD) for the specified equity.",
        "How has this ticker performed over the past month, quarter, and YTD?",
        "Report short-term returns (1M, 3M, YTD) for the company mentioned.",
    ]
    dividend_seeds = [
        "What is the dividend yield, next ex-date, and payout for this ticker?",
        "Show the upcoming dividend schedule and trailing 12-month yield for the stock.",
        "Give me dividend details: yield, last payment, next ex-dividend date for this company.",
        "Provide dividend info including yield, frequency, and next key dates for the ticker.",
        "Summarize dividend history and the next expected payment for the underlying.",
    ]
    return financials_seeds + vol_seeds + perf_seeds + dividend_seeds


def main() -> None:
    seeds = _default_seeds()
    model = os.getenv("LLM_MODEL") or os.getenv("OPENAI_MODEL")
    if not model:
        raise ValueError("Set LLM_MODEL or OPENAI_MODEL to select an LLM/model name.")
    intents = build_intents_from_seeds(seeds, model=model)
    write_intents_file(intents, Path(__file__).resolve().parent / "intents_data.json")
    print(f"Wrote {len(intents)} intents to intents_data.json based on {len(seeds)} seeds.")


if __name__ == "__main__":
    main()
