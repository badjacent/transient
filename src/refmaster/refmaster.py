"""Reference master loader."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from src.data_tools.schemas import Equity


class RefMaster:
    """Loads and holds a list of equities from refmaster_data.json."""

    def __init__(self, data_path: str | Path | None = None) -> None:
        path = Path(data_path) if data_path else Path(__file__).parent / "refmaster_data.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        equities = data.get("equities", [])
        self.equities: List[Equity] = [Equity(**eq) for eq in equities if isinstance(eq, dict)]

    def symbols(self) -> List[str]:
        return [eq.symbol for eq in self.equities]
