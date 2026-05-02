from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional
import uuid


def new_id() -> str:
    return uuid.uuid4().hex[:8]


def default_account_type(kind: str) -> str:
    return "checking" if kind == "main" else "savings"


@dataclass
class Account:
    id: str
    name: str
    kind: str
    balance: float = 0.0
    as_of_date: str = ""
    interest_rate: float = 0.0
    interest_compounding: str = "daily"
    account_type: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "Account":
        return cls(
            id=payload["id"],
            name=payload["name"],
            kind=payload["kind"],
            balance=float(payload.get("balance", 0.0)),
            as_of_date=payload.get("as_of_date", ""),
            interest_rate=float(payload.get("interest_rate", 0.0)),
            interest_compounding=payload.get("interest_compounding", "daily"),
            account_type=payload.get("account_type", default_account_type(payload["kind"])),
        )


@dataclass
class ScheduledPayment:
    id: str
    name: str
    amount: float
    date: str
    source_account_id: Optional[str] = None
    destination_account_id: Optional[str] = None
    note: str = ""
    active: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "ScheduledPayment":
        return cls(
            id=payload["id"],
            name=payload["name"],
            amount=float(payload["amount"]),
            date=payload["date"],
            source_account_id=payload.get("source_account_id"),
            destination_account_id=payload.get("destination_account_id"),
            note=payload.get("note", ""),
            active=bool(payload.get("active", True)),
        )


@dataclass
class RecurringPayment:
    id: str
    name: str
    amount: float
    schedule_type: str = "monthly_day"
    days: list[int] = field(default_factory=list)
    weekday: Optional[int] = None
    anchor_date: str = ""
    source_account_id: Optional[str] = None
    destination_account_id: Optional[str] = None
    note: str = ""
    active: bool = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict) -> "RecurringPayment":
        days = payload.get("days", [])
        if not days and "day" in payload:
            days = [int(payload["day"])]
        return cls(
            id=payload["id"],
            name=payload["name"],
            amount=float(payload["amount"]),
            schedule_type=payload.get("schedule_type", "monthly_day"),
            days=[int(day) for day in days],
            weekday=(
                int(payload["weekday"])
                if payload.get("weekday") is not None
                else None
            ),
            anchor_date=payload.get("anchor_date", ""),
            source_account_id=payload.get("source_account_id"),
            destination_account_id=payload.get("destination_account_id"),
            note=payload.get("note", ""),
            active=bool(payload.get("active", True)),
        )

    def schedule_label(self) -> str:
        if self.schedule_type == "biweekly_weekday" and self.weekday is not None:
            names = [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
            ]
            weekday_name = names[self.weekday]
            anchor = f", anchor {self.anchor_date}" if self.anchor_date else ""
            return f"Every other {weekday_name}{anchor}"
        if self.days:
            rendered = ", ".join(str(day) for day in self.days)
            return f"Monthly on day(s): {rendered}"
        return "Unknown schedule"


@dataclass
class BudgetData:
    accounts: list[Account] = field(default_factory=list)
    scheduled_payments: list[ScheduledPayment] = field(default_factory=list)
    recurring_payments: list[RecurringPayment] = field(default_factory=list)
    main_account_id: str = ""

    @classmethod
    def default(cls) -> "BudgetData":
        main = Account(
            id=new_id(),
            name="Main Bank",
            kind="main",
            balance=0.0,
            account_type="checking",
        )
        return cls(
            accounts=[main],
            scheduled_payments=[],
            recurring_payments=[],
            main_account_id=main.id,
        )

    def to_dict(self) -> dict:
        return {
            "accounts": [account.to_dict() for account in self.accounts],
            "scheduled_payments": [payment.to_dict() for payment in self.scheduled_payments],
            "recurring_payments": [payment.to_dict() for payment in self.recurring_payments],
            "main_account_id": self.main_account_id,
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "BudgetData":
        data = cls(
            accounts=[Account.from_dict(item) for item in payload.get("accounts", [])],
            scheduled_payments=[
                ScheduledPayment.from_dict(item)
                for item in payload.get("scheduled_payments", [])
            ],
            recurring_payments=[
                RecurringPayment.from_dict(item)
                for item in payload.get("recurring_payments", [])
            ],
            main_account_id=payload.get("main_account_id", ""),
        )
        if not data.accounts:
            return cls.default()
        if not data.main_account_id or not any(
            account.id == data.main_account_id for account in data.accounts
        ):
            main = next((account for account in data.accounts if account.kind == "main"), None)
            if main is None:
                main = Account(
                    id=new_id(),
                    name="Main Bank",
                    kind="main",
                    balance=0.0,
                    account_type="checking",
                )
                data.accounts.insert(0, main)
            data.main_account_id = main.id
        return data

    def get_account(self, account_id: Optional[str]) -> Optional[Account]:
        if account_id is None:
            return None
        for account in self.accounts:
            if account.id == account_id:
                return account
        return None

    def get_main_account(self) -> Account:
        account = self.get_account(self.main_account_id)
        if account is None:
            raise ValueError("Main account is missing.")
        return account

    def payout_accounts(self) -> list[Account]:
        return [account for account in self.accounts if account.kind == "payout"]
