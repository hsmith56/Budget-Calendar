from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
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


def _json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    return str(value)


def save_data(data: BudgetData) -> None:
    ensure_storage()
    temp_file = DATA_FILE.with_suffix(".json.tmp")
    with temp_file.open("w", encoding="utf-8") as handle:
        json.dump(data.to_dict(), handle, indent=2, default=_json_default)
    temp_file.replace(DATA_FILE)
