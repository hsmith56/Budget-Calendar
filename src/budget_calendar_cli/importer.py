from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from budget_calendar_cli.models import (
    Account,
    BudgetData,
    RecurringPayment,
    ScheduledPayment,
    new_id,
)

WEEKDAYS = {
    "monday": 0,
    "mondays": 0,
    "tuesday": 1,
    "tuesdays": 1,
    "wednesday": 2,
    "wednesdays": 2,
    "thursday": 3,
    "thursdays": 3,
    "friday": 4,
    "fridays": 4,
    "saturday": 5,
    "saturdays": 5,
    "sunday": 6,
    "sundays": 6,
}

WORD_DAYS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
}


@dataclass
class ImportSummary:
    accounts: int
    scheduled_payments: int
    recurring_payments: int


def _split_columns(line: str) -> list[str]:
    return [part.strip() for part in re.split(r"\t+|\s{2,}", line.strip()) if part.strip()]


def _parse_amount(raw: str) -> float:
    return float(raw.replace("$", "").replace(",", ""))


def _parse_month_day(raw: str, year: int) -> date:
    month_text, day_text = raw.strip().split("/")
    return date(year, int(month_text), int(day_text))


def _next_weekday_on_or_after(start: date, weekday: int) -> date:
    delta = (weekday - start.weekday()) % 7
    return start + timedelta(days=delta)


def _parse_schedule(raw: str, reference_date: date) -> dict:
    text = raw.strip().lower()
    if text.startswith("biweekly"):
        weekday = None
        for name, value in WEEKDAYS.items():
            if name in text:
                weekday = value
                break
        if weekday is None:
            raise ValueError(f"Could not parse weekday from schedule: {raw}")
        anchor = _next_weekday_on_or_after(reference_date, weekday)
        return {
            "schedule_type": "biweekly_weekday",
            "days": [],
            "weekday": weekday,
            "anchor_date": anchor.isoformat(),
        }

    days = set()
    for number in re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)?\b", text):
        value = int(number)
        if 1 <= value <= 31:
            days.add(value)
    for word, value in WORD_DAYS.items():
        if re.search(rf"\b{word}\b", text):
            days.add(value)

    if not days:
        raise ValueError(f"Could not parse schedule: {raw}")

    return {
        "schedule_type": "monthly_day",
        "days": sorted(days),
        "weekday": None,
        "anchor_date": "",
    }


def _find_account_id_by_name(data: BudgetData, name: str) -> str | None:
    normalized = name.strip().lower()
    if normalized == "external":
        return None
    for account in data.accounts:
        if account.name.strip().lower() == normalized:
            return account.id
    raise ValueError(f"Unknown account referenced in import: {name}")


def import_onboarding_text(text: str, default_year: int | None = None) -> tuple[BudgetData, ImportSummary]:
    year = default_year or date.today().year
    current_section = ""
    generic_accounts: list[tuple[str, float, str]] = []
    main_accounts: list[tuple[str, float, str]] = []
    payout_accounts: list[tuple[str, float, str]] = []
    payments: list[tuple[str, float, str]] = []
    recurring_bills: list[tuple[str, float, str]] = []
    recurring_income: list[tuple[str, float, str]] = []
    recurring_transfers: list[tuple[str, float, str, str, str, str]] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        columns = _split_columns(line)
        normalized = " ".join(columns).lower()

        if "balance" in normalized and "as of" in normalized:
            current_section = "accounts"
            continue
        if normalized == "main account":
            current_section = "main_accounts"
            continue
        if normalized in {"payout accounts", "savings"}:
            current_section = "payout_accounts"
            continue
        if normalized == "payments":
            current_section = "payments"
            continue
        if normalized == "recurring bills":
            current_section = "recurring_bills"
            continue
        if normalized == "recurring income":
            current_section = "recurring_income"
            continue
        if normalized.startswith("recurring transfer") or normalized.startswith("recurring transfers"):
            current_section = "recurring_transfers"
            continue

        if current_section in {"accounts", "main_accounts", "payout_accounts"}:
            if len(columns) < 3:
                continue
            name = " ".join(columns[:-2])
            balance = _parse_amount(columns[-2])
            as_of = _parse_month_day(columns[-1], year).isoformat()
            row = (name, balance, as_of)
            if current_section == "main_accounts":
                main_accounts.append(row)
            elif current_section == "payout_accounts":
                payout_accounts.append(row)
            else:
                generic_accounts.append(row)
            continue

        if current_section == "payments":
            if len(columns) < 3:
                continue
            name = " ".join(columns[:-2])
            amount = _parse_amount(columns[-2])
            when = _parse_month_day(columns[-1], year).isoformat()
            payments.append((name, amount, when))
            continue

        if current_section in {"recurring_bills", "recurring_income"}:
            if len(columns) < 3:
                continue
            name = " ".join(columns[:-2])
            amount = _parse_amount(columns[-2])
            schedule = columns[-1]
            row = (name, amount, schedule)
            if current_section == "recurring_bills":
                recurring_bills.append(row)
            else:
                recurring_income.append(row)
            continue

        if current_section == "recurring_transfers":
            if len(columns) < 5:
                continue
            name = columns[0]
            amount = _parse_amount(columns[1])
            schedule = columns[2]
            from_account = columns[3]
            to_account = columns[4]
            note = columns[5] if len(columns) > 5 else ""
            recurring_transfers.append(
                (name, amount, schedule, from_account, to_account, note)
            )

    data = BudgetData(accounts=[], scheduled_payments=[], recurring_payments=[], main_account_id="")

    if main_accounts:
        main_name, main_balance, main_as_of = main_accounts[0]
        main_account = Account(
            id=new_id(),
            name=main_name,
            kind="main",
            balance=main_balance,
            as_of_date=main_as_of,
            account_type="checking",
        )
        data.accounts.append(main_account)
        data.main_account_id = main_account.id
        for name, balance, as_of in payout_accounts + generic_accounts:
            data.accounts.append(
                Account(
                    id=new_id(),
                    name=name,
                    kind="payout",
                    balance=balance,
                    as_of_date=as_of,
                    account_type="savings",
                )
            )
    else:
        if not generic_accounts and not payout_accounts:
            raise ValueError("No accounts were found in the onboarding text.")
        combined = generic_accounts + payout_accounts
        main_name, main_balance, main_as_of = combined[0]
        main_account = Account(
            id=new_id(),
            name=main_name,
            kind="main",
            balance=main_balance,
            as_of_date=main_as_of,
            account_type="checking",
        )
        data.accounts.append(main_account)
        data.main_account_id = main_account.id
        for name, balance, as_of in combined[1:]:
            data.accounts.append(
                Account(
                    id=new_id(),
                    name=name,
                    kind="payout",
                    balance=balance,
                    as_of_date=as_of,
                    account_type="savings",
                )
            )

    reference_date = date.fromisoformat(main_account.as_of_date) if main_account.as_of_date else date(year, 1, 1)

    for name, amount, when in payments:
        if amount < 0:
            source_account_id = data.main_account_id
            destination_account_id = None
        else:
            source_account_id = None
            destination_account_id = data.main_account_id
        data.scheduled_payments.append(
            ScheduledPayment(
                id=new_id(),
                name=name,
                amount=abs(amount),
                date=when,
                source_account_id=source_account_id,
                destination_account_id=destination_account_id,
                note="Imported onboarding payment",
            )
        )

    for name, amount, schedule in recurring_bills:
        parsed_schedule = _parse_schedule(schedule, reference_date)
        data.recurring_payments.append(
            RecurringPayment(
                id=new_id(),
                name=name,
                amount=abs(amount),
                source_account_id=data.main_account_id,
                destination_account_id=None,
                note="Imported recurring bill",
                **parsed_schedule,
            )
        )

    for name, amount, schedule in recurring_income:
        parsed_schedule = _parse_schedule(schedule, reference_date)
        data.recurring_payments.append(
            RecurringPayment(
                id=new_id(),
                name=name,
                amount=abs(amount),
                source_account_id=None,
                destination_account_id=data.main_account_id,
                note="Imported recurring income",
                **parsed_schedule,
            )
        )

    for name, amount, schedule, from_account, to_account, note in recurring_transfers:
        parsed_schedule = _parse_schedule(schedule, reference_date)
        data.recurring_payments.append(
            RecurringPayment(
                id=new_id(),
                name=name,
                amount=abs(amount),
                source_account_id=_find_account_id_by_name(data, from_account),
                destination_account_id=_find_account_id_by_name(data, to_account),
                note=note or "Imported recurring transfer",
                **parsed_schedule,
            )
        )

    return data, ImportSummary(
        accounts=len(data.accounts),
        scheduled_payments=len(data.scheduled_payments),
        recurring_payments=len(data.recurring_payments),
    )


def import_onboarding_file(path: str | Path, default_year: int | None = None) -> tuple[BudgetData, ImportSummary]:
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    return import_onboarding_text(text, default_year=default_year)
