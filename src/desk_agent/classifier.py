"""LLM-based intent classifier using intent definitions as context."""

from __future__ import annotations

import json
import os
from typing import List, Tuple

import requests

from src.desk_agent.intents_loader import IntentDef, load_intent_definitions


def _get_llm_api_key() -> str:
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise ValueError("LLM_API_KEY not set in environment.")
    return api_key


def _get_llm_endpoint() -> str:
    endpoint = os.getenv("LLM_API_URL")
    if not endpoint:
        raise ValueError("LLM_API_URL not set in environment.")
    return endpoint


def _call_llm_chat(messages: List[dict], model: str = "generic-llm") -> str:
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
    return data["choices"][0]["message"]["content"]


def classify_question(
    question: str,
    intents: List[IntentDef] | None = None,
    model: str = "generic-llm",
) -> Tuple[str, float, dict]:
    """
    Ask an LLM to pick the best intent for a question.
    
    Returns (intent_name, confidence, slots_dict)
    """
    intent_defs = intents or load_intent_definitions()
    intent_json = json.dumps({"intents": intent_defs}, separators=(",", ":"))
    system_prompt = (
        "You are an intent classifier. Given a question and a list of intents with slots, "
        "return JSON: {\"intent\": name, \"confidence\": float 0-1, \"slots\": {…}}. "
        "Only use provided intents. If none fit, use generic_unhandled and copy details into slots.other."
    )
    user_prompt = (
        f"Question: {question}\n"
        f"Available intents: {intent_json}\n"
        "Return JSON only."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    raw = _call_llm_chat(messages, model=model)
    parsed = json.loads(raw)
    return parsed.get("intent", "generic_unhandled"), float(parsed.get("confidence", 0)), parsed.get("slots", {})
