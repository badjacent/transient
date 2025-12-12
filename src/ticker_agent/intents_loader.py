"""Load intent definitions from a data file (JSON)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, TypedDict


class IntentDef(TypedDict):
    name: str
    description: str
    slots: List[str]
    seeds: List[str]


def _default_intents_path() -> Path:
    """Resolve the default intents data file path."""
    return Path(__file__).resolve().parent / "intents_data.json"


def load_intent_definitions(data_path: str | Path | None = None) -> List[IntentDef]:
    """Load intent definitions from a JSON file."""
    path = Path(data_path) if data_path else _default_intents_path()
    data = json.loads(path.read_text(encoding="utf-8"))
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
