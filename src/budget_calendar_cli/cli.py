from __future__ import annotations

from datetime import date
from pathlib import Path

from budget_calendar_cli.calendar_view import open_calendar_in_browser
from budget_calendar_cli.importer import import_onboarding_file
from budget_calendar_cli.models import Account, RecurringPayment, ScheduledPayment, new_id
from budget_calendar_cli.storage import DATA_FILE, load_data, save_data

WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

ACCOUNT_TYPES = ["checking", "savings", "brokerage", "credit", "cash", "other"]


def prompt_text(label: str, allow_blank: bool = False) -> str:
    while True:
        value = input(label).strip()
        if value or allow_blank:
            return value
        print("Please enter a value.")


def prompt_float(
    label: str,
    allow_blank: bool = False,
    default: float | None = None,
) -> float | None:
    while True:
        raw = input(label).strip()
        if not raw and allow_blank:
            return default
        try:
            return float(raw)
        except ValueError:
            print("Please enter a valid number.")


def prompt_int(
    label: str,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    while True:
        raw = input(label).strip()
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if minimum is not None and value < minimum:
            print(f"Please enter a number >= {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Please enter a number <= {maximum}.")
            continue
        return value


def prompt_int_default(
    label: str,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    while True:
        raw = input(label).strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if minimum is not None and value < minimum:
            print(f"Please enter a number >= {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Please enter a number <= {maximum}.")
            continue
        return value


def format_money(amount: float) -> str:
    return f"${amount:,.2f}"


def format_interest_rate(rate: float) -> str:
    return f"{rate:.2f}%"


def prompt_account_type(default: str = "savings") -> str:
    print("\nAccount type")
    for index, label in enumerate(ACCOUNT_TYPES, start=1):
        marker = " (default)" if label == default else ""
        print(f"{index}. {label}{marker}")
    choice = input("Choose account type [blank for default]: ").strip()
    if not choice:
        return default
    try:
        index = int(choice)
    except ValueError:
        print("Invalid choice.")
        return prompt_account_type(default)
    if index < 1 or index > len(ACCOUNT_TYPES):
        print("Invalid choice.")
        return prompt_account_type(default)
    return ACCOUNT_TYPES[index - 1]


def format_account_line(account, is_main: bool) -> str:
    marker = " (main)" if is_main else ""
    as_of = f" as of {account.as_of_date}" if account.as_of_date else ""
    interest = ""
    if account.interest_rate > 0:
        interest = f" | interest {format_interest_rate(account.interest_rate)} {account.interest_compounding}"
    return f"{account.name}{marker} [{account.account_type}] - {format_money(account.balance)}{as_of}{interest}"


def print_accounts(data) -> None:
    print("\nAccounts")
    print("-" * 60)
    for index, account in enumerate(data.accounts, start=1):
        print(f"{index}. {format_account_line(account, account.id == data.main_account_id)}")
    print()


def choose_account(data, prompt: str, include_external: bool = False):
    options = []
    if include_external:
        options.append((None, "External"))
    for account in data.accounts:
        options.append((account.id, f"{account.name} [{account.account_type}]"))

    print(f"\n{prompt}")
    for index, (_, label) in enumerate(options, start=1):
        print(f"{index}. {label}")

    choice = prompt_int("Choose an option: ", minimum=1, maximum=len(options))
    return options[choice - 1][0]


def add_payout_account(data) -> None:
    print("\nAdd payout account")
    name = prompt_text("Account name: ")
    balance = prompt_float("Starting balance: ")
    as_of = prompt_text("As-of date (YYYY-MM-DD, optional): ", allow_blank=True)
    account_type = prompt_account_type(default="savings")
    interest_rate = prompt_float(
        "Annual interest rate % (optional, blank for 0): ",
        allow_blank=True,
        default=0.0,
    )
    data.accounts.append(
        Account(
            id=new_id(),
            name=name,
            kind="payout",
            balance=balance or 0.0,
            as_of_date=as_of,
            interest_rate=interest_rate or 0.0,
            interest_compounding="daily",
            account_type=account_type,
        )
    )
    save_data(data)
    print(f"Added payout account '{name}'.")


def update_account_balance(data) -> None:
    print_accounts(data)
    account_id = choose_account(data, "Update which account?")
    account = data.get_account(account_id)
    if account is None:
        print("Account not found.")
        return
    new_balance = prompt_float(f"New balance for {account.name}: ")
    as_of = prompt_text("As-of date (YYYY-MM-DD, optional): ", allow_blank=True)
    account.balance = new_balance or 0.0
    if as_of:
        account.as_of_date = as_of
    save_data(data)
    print(f"Updated {account.name} to {format_money(account.balance)}.")


def set_account_interest_rate(data) -> None:
    print("\nSet account type / interest")
    print_accounts(data)
    account_id = choose_account(data, "Set interest rate for which account?")
    account = data.get_account(account_id)
    if account is None:
        print("Account not found.")
        return
    account.account_type = prompt_account_type(default=account.account_type)
    rate = prompt_float(
        f"Annual interest rate % for {account.name} [current {format_interest_rate(account.interest_rate)}]: ",
        allow_blank=True,
        default=account.interest_rate,
    )
    if rate is None or rate < 0:
        print("Interest rate must be zero or greater.")
        return
    account.interest_rate = rate
    account.interest_compounding = "daily"
    save_data(data)
    print(
        f"Updated {account.name} to type '{account.account_type}' with interest {format_interest_rate(account.interest_rate)} daily compounding."
    )


def add_scheduled_payment(data) -> None:
    print("\nAdd one-time scheduled payment")
    name = prompt_text("Name: ")
    amount = prompt_float("Amount: ")
    when = prompt_text("Date (YYYY-MM-DD): ")
    source_account_id = choose_account(
        data, "Select source account", include_external=True
    )
    destination_account_id = choose_account(
        data, "Select destination account", include_external=True
    )
    note = prompt_text("Note (optional): ", allow_blank=True)

    if source_account_id is None and destination_account_id is None:
        print("A scheduled payment cannot be External -> External.")
        return
    if source_account_id == destination_account_id and source_account_id is not None:
        print("Source and destination cannot be the same account.")
        return
    if (amount or 0.0) < 0:
        print("Amount must be zero or greater.")
        return

    data.scheduled_payments.append(
        ScheduledPayment(
            id=new_id(),
            name=name,
            amount=amount or 0.0,
            date=when,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            note=note,
            active=True,
        )
    )
    save_data(data)
    print(f"Added scheduled payment '{name}'.")


def list_scheduled_payments(data) -> None:
    print("\nScheduled payments")
    print("-" * 60)
    if not data.scheduled_payments:
        print("No scheduled payments configured.\n")
        return

    payments = sorted(data.scheduled_payments, key=lambda item: (item.date, item.name.lower()))
    for index, payment in enumerate(payments, start=1):
        source = data.get_account(payment.source_account_id)
        destination = data.get_account(payment.destination_account_id)
        source_name = source.name if source else "External"
        destination_name = destination.name if destination else "External"
        note = f" | {payment.note}" if payment.note else ""
        print(
            f"{index}. {payment.date}: {payment.name} - {format_money(payment.amount)} "
            f"({source_name} -> {destination_name}){note}"
        )
    print()


def prompt_recurring_schedule() -> tuple[str, list[int], int | None, str]:
    print("\nSchedule type")
    print("1. Monthly day(s)")
    print("2. Biweekly weekday")
    choice = prompt_int("Choose an option: ", minimum=1, maximum=2)

    if choice == 1:
        raw = prompt_text("Day(s) of month, comma separated (example: 1,15): ")
        try:
            days = sorted({int(part.strip()) for part in raw.split(",") if part.strip()})
        except ValueError:
            print("Invalid day list.")
            return prompt_recurring_schedule()
        if not days or any(day < 1 or day > 31 for day in days):
            print("Days must be between 1 and 31.")
            return prompt_recurring_schedule()
        return "monthly_day", days, None, ""

    weekday_text = prompt_text("Weekday (monday-sunday): ").lower()
    weekday = WEEKDAYS.get(weekday_text)
    if weekday is None:
        print("Invalid weekday.")
        return prompt_recurring_schedule()
    anchor_date = prompt_text("Anchor date (YYYY-MM-DD): ")
    return "biweekly_weekday", [], weekday, anchor_date


def add_recurring_payment(data) -> None:
    print("\nAdd recurring payment or transfer")
    name = prompt_text("Name: ")
    amount = prompt_float("Amount: ")
    schedule_type, days, weekday, anchor_date = prompt_recurring_schedule()
    source_account_id = choose_account(
        data, "Select source account", include_external=True
    )
    destination_account_id = choose_account(
        data, "Select destination account", include_external=True
    )
    note = prompt_text("Note (optional): ", allow_blank=True)

    if source_account_id is None and destination_account_id is None:
        print("A recurring payment cannot be External -> External.")
        return
    if source_account_id == destination_account_id and source_account_id is not None:
        print("Source and destination cannot be the same account.")
        return
    if (amount or 0.0) < 0:
        print("Amount must be zero or greater.")
        return

    data.recurring_payments.append(
        RecurringPayment(
            id=new_id(),
            name=name,
            amount=amount or 0.0,
            schedule_type=schedule_type,
            days=days,
            weekday=weekday,
            anchor_date=anchor_date,
            source_account_id=source_account_id,
            destination_account_id=destination_account_id,
            note=note,
            active=True,
        )
    )
    save_data(data)
    print(f"Added recurring payment '{name}'.")


def list_recurring_payments(data) -> None:
    print("\nRecurring payments and transfers")
    print("-" * 60)
    if not data.recurring_payments:
        print("No recurring payments configured.\n")
        return

    payments = sorted(data.recurring_payments, key=lambda item: item.name.lower())
    for index, payment in enumerate(payments, start=1):
        source = data.get_account(payment.source_account_id)
        destination = data.get_account(payment.destination_account_id)
        source_name = source.name if source else "External"
        destination_name = destination.name if destination else "External"
        status = "active" if payment.active else "inactive"
        note = f" | {payment.note}" if payment.note else ""
        print(
            f"{index}. {payment.name} - {format_money(payment.amount)} "
            f"[{payment.schedule_label()}] ({source_name} -> {destination_name}) "
            f"[{status}]{note}"
        )
    print()


def import_onboarding(data) -> None:
    print("\nImport onboarding text file")
    print("Expected format example: examples/onboarding-template.txt")
    path = prompt_text("Path to onboarding text file: ")
    source = Path(path)
    if not source.exists():
        print("File not found.")
        return
    year = prompt_int_default(
        f"Year for MM/DD entries [{date.today().year}]: ",
        default=date.today().year,
        minimum=1900,
        maximum=9999,
    )
    confirm = prompt_text("Replace current data? (y/n): ").lower()
    if confirm != "y":
        print("Import cancelled.")
        return
    imported_data, summary = import_onboarding_file(source, default_year=year)
    save_data(imported_data)
    print(
        f"Imported {summary.accounts} account(s), {summary.scheduled_payments} scheduled payment(s), "
        f"and {summary.recurring_payments} recurring payment(s)."
    )


def open_calendar(data) -> None:
    today = date.today()
    print("\nOpen calendar in browser")
    year = prompt_int_default(
        f"Year [{today.year}]: ",
        default=today.year,
        minimum=1900,
        maximum=9999,
    )
    month = prompt_int_default(
        f"Month [{today.month}]: ",
        default=today.month,
        minimum=1,
        maximum=12,
    )
    main_balance = data.get_main_account().balance
    opening_balance = prompt_float(
        f"Opening main balance [{format_money(main_balance)}]: ",
        allow_blank=True,
        default=main_balance,
    )
    target = open_calendar_in_browser(data, year, month, opening_balance)
    print(f"Opened calendar: {target}")


def print_menu() -> None:
    print("Budget Calendar CLI")
    print("-" * 60)
    print("1. View accounts")
    print("2. Add payout account")
    print("3. Update account balance")
    print("4. Set account type / interest")
    print("5. Add one-time scheduled payment")
    print("6. View scheduled payments")
    print("7. Add recurring payment or transfer")
    print("8. View recurring payments and transfers")
    print("9. Import onboarding text file")
    print("10. Open calendar view in browser")
    print("11. Exit")


def main() -> None:
    data = load_data()
    print(f"Data file: {DATA_FILE}")

    while True:
        print()
        print_menu()
        choice = prompt_int("Choose an option: ", minimum=1, maximum=11)

        if choice == 1:
            print_accounts(data)
        elif choice == 2:
            add_payout_account(data)
        elif choice == 3:
            update_account_balance(data)
        elif choice == 4:
            set_account_interest_rate(data)
        elif choice == 5:
            add_scheduled_payment(data)
        elif choice == 6:
            list_scheduled_payments(data)
        elif choice == 7:
            add_recurring_payment(data)
        elif choice == 8:
            list_recurring_payments(data)
        elif choice == 9:
            import_onboarding(data)
        elif choice == 10:
            open_calendar(data)
        else:
            print("Goodbye.")
            return

        data = load_data()
