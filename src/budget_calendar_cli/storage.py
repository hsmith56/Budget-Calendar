from __future__ import annotations

import json
from pathlib import Path

from budget_calendar_cli.models import BudgetData

DATA_DIR = Path.cwd() / ".budget_calendar"
DATA_FILE = DATA_DIR / "data.json"


def ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_data() -> BudgetData:
    ensure_storage()
    if not DATA_FILE.exists():
        data = BudgetData.default()
        save_data(data)
        return data
    with DATA_FILE.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return BudgetData.from_dict(payload)


def save_data(data: BudgetData) -> None:
    ensure_storage()
    with DATA_FILE.open("w", encoding="utf-8") as handle:
        json.dump(data.to_dict(), handle, indent=2)
