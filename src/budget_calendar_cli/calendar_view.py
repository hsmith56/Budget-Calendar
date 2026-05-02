from __future__ import annotations

import calendar
import html
import threading
import webbrowser
from dataclasses import dataclass, field
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional
from urllib.parse import parse_qs, urlencode, urlparse

from budget_calendar_cli.models import BudgetData, RecurringPayment, ScheduledPayment
from budget_calendar_cli.storage import load_data

ACCOUNT_TYPE_META = {
    "checking": {"icon": "🏦", "class_name": "checking"},
    "savings": {"icon": "💰", "class_name": "savings"},
    "brokerage": {"icon": "📈", "class_name": "brokerage"},
    "credit": {"icon": "💳", "class_name": "credit"},
    "cash": {"icon": "💵", "class_name": "cash"},
    "other": {"icon": "📁", "class_name": "other"},
}


@dataclass
class DaySummary:
    day: int
    running_balance: float | None
    events: list[str]
    note: str = ""
    account_balances: list[tuple[str, str, float | None]] = field(default_factory=list)
    interest_earned_today: list[tuple[str, str, float]] = field(default_factory=list)
    interest_earned_month: list[tuple[str, str, float]] = field(default_factory=list)


@dataclass
class MonthSimulation:
    year: int
    month: int
    opening_balance: float
    opening_as_of_date: str = ""
    start_day: int = 1
    has_loaded_history: bool = True
    days: dict[int, DaySummary] = field(default_factory=dict)
    closing_main_balance: float | None = None
    minimum_main_balance: float | None = None
    maximum_main_balance: float | None = None
    monthly_interest_totals: list[tuple[str, str, float]] = field(default_factory=list)
    total_monthly_interest: float = 0.0


_SERVER: ThreadingHTTPServer | None = None
_SERVER_THREAD: threading.Thread | None = None
_SERVER_PORT: int | None = None
_SERVER_LOCK = threading.Lock()


def _account_name(data: BudgetData, account_id: Optional[str]) -> str:
    if account_id is None:
        return "External"
    account = data.get_account(account_id)
    return account.name if account else "Unknown"


def _event_text(data: BudgetData, payment: ScheduledPayment | RecurringPayment) -> str:
    source = _account_name(data, payment.source_account_id)
    destination = _account_name(data, payment.destination_account_id)
    note = f" — {payment.note}" if payment.note else ""
    return f"{payment.name}: ${payment.amount:,.2f} {source} → {destination}{note}"


def _recurring_matches(payment: RecurringPayment, current_date: date) -> bool:
    if payment.schedule_type == "biweekly_weekday":
        if payment.weekday is None or not payment.anchor_date:
            return False
        anchor = date.fromisoformat(payment.anchor_date)
        if current_date < anchor or current_date.weekday() != payment.weekday:
            return False
        return (current_date - anchor).days % 14 == 0
    return current_date.day in payment.days


def _account_snapshot_date(account, year: int, month: int) -> date:
    if account.as_of_date:
        return date.fromisoformat(account.as_of_date)
    return date(year, month, 1)


def _format_balance(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"${value:,.2f}"


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _daily_interest_amount(balance: float, annual_rate_percent: float) -> float:
    if annual_rate_percent <= 0:
        return 0.0
    return balance * ((annual_rate_percent / 100.0) / 365.0)


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    absolute = year * 12 + (month - 1) + delta
    shifted_year = absolute // 12
    shifted_month = absolute % 12 + 1
    return shifted_year, shifted_month


def _account_badge(name: str, account_type: str) -> str:
    meta = ACCOUNT_TYPE_META.get(account_type, ACCOUNT_TYPE_META["other"])
    return (
        f'<span class="account-badge {html.escape(meta["class_name"])}">'
        f'{html.escape(meta["icon"])} {html.escape(name)} ({html.escape(account_type)})'
        f"</span>"
    )


def _summary_card(title: str, value: str, accent: str = "") -> str:
    class_name = f"summary-card {accent}".strip()
    return (
        f'<div class="{class_name}">'
        f'<div class="summary-label">{html.escape(title)}</div>'
        f'<div class="summary-value">{html.escape(value)}</div>'
        f"</div>"
    )


def simulate_month(
    data: BudgetData,
    year: int,
    month: int,
    opening_balance: Optional[float] = None,
) -> MonthSimulation:
    target_start = date(year, month, 1)
    target_end = date(year, month, calendar.monthrange(year, month)[1])
    main_account = data.get_main_account()
    main_snapshot = _account_snapshot_date(main_account, year, month)

    if target_end < _month_start(main_snapshot):
        days = {
            day: DaySummary(
                day=day,
                running_balance=None,
                events=[],
                note="No loaded historical data for this month.",
                account_balances=[
                    (account.name, account.account_type, None) for account in data.accounts
                ],
            )
            for day in range(1, target_end.day + 1)
        }
        return MonthSimulation(
            year=year,
            month=month,
            opening_balance=main_account.balance if opening_balance is None else opening_balance,
            opening_as_of_date=main_snapshot.isoformat(),
            start_day=main_snapshot.day,
            has_loaded_history=False,
            days=days,
        )

    snapshot_dates: dict[str, date] = {}
    opening_balances: dict[str, float] = {}
    current_balances: dict[str, float | None] = {}
    monthly_interest_by_account: dict[str, float] = {
        account.id: 0.0 for account in data.accounts
    }

    for account in data.accounts:
        snapshot_dates[account.id] = _account_snapshot_date(account, year, month)
        balance = account.balance
        if account.id == main_account.id and opening_balance is not None:
            balance = opening_balance
        opening_balances[account.id] = balance
        current_balances[account.id] = None

    simulation_start = min(min(snapshot_dates.values()), target_start)
    summaries: dict[int, DaySummary] = {}
    current_date = simulation_start
    snapshot_month_start = _month_start(main_snapshot)

    while current_date <= target_end:
        for account in data.accounts:
            if current_date == snapshot_dates[account.id]:
                current_balances[account.id] = opening_balances[account.id]

        events: list[str] = []

        if (
            current_date.year == snapshot_month_start.year
            and current_date.month == snapshot_month_start.month
        ):
            for payment in sorted(
                data.scheduled_payments,
                key=lambda item: (item.date, item.name.lower()),
            ):
                if not payment.active or payment.date != current_date.isoformat():
                    continue
                if (
                    payment.source_account_id is not None
                    and current_balances.get(payment.source_account_id) is not None
                ):
                    current_balances[payment.source_account_id] -= payment.amount
                if (
                    payment.destination_account_id is not None
                    and current_balances.get(payment.destination_account_id) is not None
                ):
                    current_balances[payment.destination_account_id] += payment.amount
                if target_start <= current_date <= target_end:
                    events.append(_event_text(data, payment))

        for payment in sorted(
            data.recurring_payments,
            key=lambda item: (item.name.lower(), item.amount),
        ):
            if not payment.active or not _recurring_matches(payment, current_date):
                continue
            if (
                payment.source_account_id is not None
                and current_balances.get(payment.source_account_id) is not None
            ):
                current_balances[payment.source_account_id] -= payment.amount
            if (
                payment.destination_account_id is not None
                and current_balances.get(payment.destination_account_id) is not None
            ):
                current_balances[payment.destination_account_id] += payment.amount
            if target_start <= current_date <= target_end:
                events.append(_event_text(data, payment))

        interest_events: list[str] = []
        interest_today: list[tuple[str, str, float]] = []
        for account in data.accounts:
            current_balance = current_balances.get(account.id)
            snapshot_date = snapshot_dates[account.id]
            if (
                current_balance is None
                or account.interest_rate <= 0
                or current_date <= snapshot_date
            ):
                continue
            interest_amount = _daily_interest_amount(
                current_balance, account.interest_rate
            )
            current_balances[account.id] += interest_amount
            if target_start <= current_date <= target_end:
                monthly_interest_by_account[account.id] += interest_amount
                interest_today.append(
                    (account.name, account.account_type, interest_amount)
                )
                interest_events.append(
                    f"{account.name} interest: ${interest_amount:,.2f} at {account.interest_rate:.2f}%"
                )

        if target_start <= current_date <= target_end:
            note = ""
            if current_date < main_snapshot:
                note = "No loaded historical data for this day."
            summaries[current_date.day] = DaySummary(
                day=current_date.day,
                running_balance=current_balances.get(main_account.id),
                events=events + interest_events,
                note=note,
                account_balances=[
                    (account.name, account.account_type, current_balances.get(account.id))
                    for account in data.accounts
                ],
                interest_earned_today=interest_today,
                interest_earned_month=[
                    (
                        account.name,
                        account.account_type,
                        monthly_interest_by_account[account.id],
                    )
                    for account in data.accounts
                    if monthly_interest_by_account[account.id] > 0
                ],
            )

        current_date += timedelta(days=1)

    main_values = [
        summary.running_balance
        for _, summary in sorted(summaries.items())
        if summary.running_balance is not None
    ]
    monthly_interest_totals = [
        (account.name, account.account_type, monthly_interest_by_account[account.id])
        for account in data.accounts
        if monthly_interest_by_account[account.id] > 0
    ]

    return MonthSimulation(
        year=year,
        month=month,
        opening_balance=opening_balances[main_account.id],
        opening_as_of_date=main_snapshot.isoformat(),
        start_day=main_snapshot.day,
        has_loaded_history=True,
        days=summaries,
        closing_main_balance=main_values[-1] if main_values else None,
        minimum_main_balance=min(main_values) if main_values else None,
        maximum_main_balance=max(main_values) if main_values else None,
        monthly_interest_totals=monthly_interest_totals,
        total_monthly_interest=sum(value for _, _, value in monthly_interest_totals),
    )


def _month_href(year: int, month: int, opening_balance: Optional[float]) -> str:
    params = {"year": year, "month": month}
    if opening_balance is not None:
        params["opening"] = opening_balance
    return f"/calendar?{urlencode(params)}"


def build_calendar_html(
    simulation: MonthSimulation,
    opening_balance: Optional[float] = None,
) -> str:
    cal = calendar.Calendar(firstweekday=6)
    month_name = calendar.month_name[simulation.month]
    weeks = cal.monthdatescalendar(simulation.year, simulation.month)

    prev_year, prev_month = _shift_month(simulation.year, simulation.month, -1)
    next_year, next_month = _shift_month(simulation.year, simulation.month, 1)
    prev_href = _month_href(prev_year, prev_month, opening_balance)
    next_href = _month_href(next_year, next_month, opening_balance)

    rows: list[str] = []
    for week in weeks:
        cells: list[str] = []
        for current_date in week:
            in_month = current_date.month == simulation.month
            classes = "day-cell" if in_month else "day-cell muted"
            if in_month:
                summary = simulation.days[current_date.day]
                balance_html = "N/A"
                balance_class = "balance na"
                if summary.running_balance is not None:
                    balance_html = f"${summary.running_balance:,.2f}"
                    balance_class = "balance"
                    if summary.running_balance < 0:
                        balance_class = "balance negative"

                items = summary.events[:]
                if summary.note:
                    items.insert(0, summary.note)
                events = "".join(f"<li>{html.escape(item)}</li>" for item in items)
                if not events:
                    events = "<li>No scheduled items</li>"

                balances = "".join(
                    "<li><span>"
                    + _account_badge(name, account_type)
                    + "</span><strong>"
                    + html.escape(_format_balance(value))
                    + "</strong></li>"
                    for name, account_type, value in summary.account_balances
                )
                interest_today = "".join(
                    "<li><span>"
                    + _account_badge(name, account_type)
                    + "</span><strong>$"
                    + html.escape(f"{value:,.2f}")
                    + "</strong></li>"
                    for name, account_type, value in summary.interest_earned_today
                ) or "<li><span>No interest earned today</span></li>"
                interest_month = "".join(
                    "<li><span>"
                    + _account_badge(name, account_type)
                    + "</span><strong>$"
                    + html.escape(f"{value:,.2f}")
                    + "</strong></li>"
                    for name, account_type, value in summary.interest_earned_month
                ) or "<li><span>No interest earned this month</span></li>"

                cell = f"""
                <td class=\"{classes}\">
                    <div class=\"day-number\">{current_date.day}</div>
                    <div class=\"{balance_class}\">{balance_html}</div>
                    <ul class=\"events\">{events}</ul>
                    <div class=\"detail-card\">
                        <div class=\"detail-title\">{current_date.strftime('%A, %B')} {current_date.day}</div>
                        <div class=\"detail-subtitle\">End-of-day account balances</div>
                        <ul class=\"balance-list\">{balances}</ul>
                        <div class=\"detail-subtitle section-gap\">Interest earned today</div>
                        <ul class=\"balance-list\">{interest_today}</ul>
                        <div class=\"detail-subtitle section-gap\">Interest earned month-to-date</div>
                        <ul class=\"balance-list\">{interest_month}</ul>
                    </div>
                </td>
                """
            else:
                cell = f"<td class=\"{classes}\"></td>"
            cells.append(cell)
        rows.append(f"<tr>{''.join(cells)}</tr>")

    meta = f"Main balance snapshot: ${simulation.opening_balance:,.2f} as of {simulation.opening_as_of_date}"
    if not simulation.has_loaded_history:
        meta += " — historical data is not loaded for this month"
    else:
        meta += " — future months are projected from recurring payments and daily account interest"
    meta += " — hover over a date to view balances for all accounts"

    summary_cards = "".join(
        [
            _summary_card("Opening main balance", _format_balance(simulation.opening_balance)),
            _summary_card("Closing main balance", _format_balance(simulation.closing_main_balance)),
            _summary_card("Lowest main balance", _format_balance(simulation.minimum_main_balance), "warning"),
            _summary_card("Highest main balance", _format_balance(simulation.maximum_main_balance), "success"),
            _summary_card("Projected interest this month", f"${simulation.total_monthly_interest:,.2f}", "interest"),
        ]
    )

    interest_summary = "".join(
        "<li><span>"
        + _account_badge(name, account_type)
        + "</span><strong>$"
        + html.escape(f"{value:,.2f}")
        + "</strong></li>"
        for name, account_type, value in simulation.monthly_interest_totals
    ) or "<li><span>No projected interest this month</span></li>"

    return f"""
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>{html.escape(month_name)} {simulation.year} Budget Calendar</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; padding: 24px; background: #f4f7fb; color: #1f2937; }}
    .nav {{ display: flex; justify-content: space-between; align-items: center; gap: 16px; margin: 0 0 20px; }}
    .nav-link {{ color: #1d4ed8; text-decoration: none; font-weight: 600; }}
    .nav-link:hover {{ text-decoration: underline; }}
    .nav-title {{ font-size: 22px; font-weight: 700; }}
    .meta {{ margin-bottom: 20px; color: #4b5563; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; margin-bottom: 16px; }}
    .summary-card {{ background: white; border: 1px solid #dbe2ea; border-radius: 12px; padding: 14px; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06); }}
    .summary-card.warning {{ border-color: #fbbf24; }}
    .summary-card.success {{ border-color: #34d399; }}
    .summary-card.interest {{ border-color: #38bdf8; }}
    .summary-label {{ font-size: 12px; color: #64748b; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.03em; }}
    .summary-value {{ font-size: 22px; font-weight: 700; }}
    .interest-panel {{ background: white; border: 1px solid #dbe2ea; border-radius: 12px; padding: 16px; box-shadow: 0 6px 18px rgba(15, 23, 42, 0.06); margin-bottom: 20px; }}
    .interest-panel h2 {{ margin: 0 0 12px; font-size: 16px; }}
    table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
    th {{ background: #111827; color: white; padding: 10px; font-size: 14px; }}
    td {{ border: 1px solid #d1d5db; vertical-align: top; height: 170px; padding: 10px; background: white; overflow: visible; }}
    .day-cell {{ position: relative; overflow: visible; }}
    .muted {{ background: #eef2f7; }}
    .day-number {{ font-weight: bold; margin-bottom: 8px; }}
    .balance {{ font-size: 18px; font-weight: bold; margin-bottom: 8px; color: #0f766e; }}
    .balance.negative {{ color: #b91c1c; }}
    .balance.na {{ color: #64748b; }}
    .events {{ margin: 0; padding-left: 18px; font-size: 13px; line-height: 1.4; }}
    .detail-card {{ position: absolute; left: 10px; top: 40px; width: 320px; max-width: min(320px, calc(100vw - 32px)); max-height: min(70vh, 560px); overflow: auto; background: #111827; color: white; border-radius: 10px; padding: 12px; box-shadow: 0 18px 40px rgba(0, 0, 0, 0.28); opacity: 0; visibility: hidden; transform: translateY(8px); transition: opacity 0.15s ease, transform 0.15s ease, visibility 0.15s ease; z-index: 50; }}
    .day-cell:hover .detail-card, .day-cell:focus-within .detail-card {{ opacity: 1; visibility: visible; transform: translateY(0); }}
    .detail-card.flip-x {{ left: auto; right: 10px; }}
    .detail-card.flip-y {{ top: auto; bottom: 40px; }}
    .detail-title {{ font-weight: 700; margin-bottom: 4px; }}
    .detail-subtitle {{ font-size: 12px; color: #cbd5e1; margin-bottom: 10px; }}
    .detail-subtitle.section-gap {{ margin-top: 12px; }}
    .balance-list {{ list-style: none; padding: 0; margin: 0; }}
    .balance-list li {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; padding: 6px 0; border-top: 1px solid rgba(255,255,255,0.1); }}
    .balance-list li:first-child {{ border-top: 0; }}
    .balance-list strong {{ white-space: nowrap; }}
    .account-badge {{ display: inline-flex; align-items: center; gap: 6px; border-radius: 999px; padding: 4px 8px; font-size: 12px; font-weight: 600; }}
    .account-badge.checking {{ background: #dbeafe; color: #1d4ed8; }}
    .account-badge.savings {{ background: #dcfce7; color: #15803d; }}
    .account-badge.brokerage {{ background: #ede9fe; color: #7c3aed; }}
    .account-badge.credit {{ background: #fee2e2; color: #b91c1c; }}
    .account-badge.cash {{ background: #fef3c7; color: #b45309; }}
    .account-badge.other {{ background: #e5e7eb; color: #374151; }}
  </style>
</head>
<body>
  <div class=\"nav\">
    <a class=\"nav-link\" href=\"{html.escape(prev_href)}\">← Previous month</a>
    <div class=\"nav-title\">{html.escape(month_name)} {simulation.year}</div>
    <a class=\"nav-link\" href=\"{html.escape(next_href)}\">Next month →</a>
  </div>
  <div class=\"meta\">{html.escape(meta)}</div>
  <section class=\"summary-grid\">{summary_cards}</section>
  <section class=\"interest-panel\">
    <h2>Projected interest by account for this month</h2>
    <ul class=\"balance-list\">{interest_summary}</ul>
  </section>
  <table>
    <thead>
      <tr>
        <th>Sunday</th>
        <th>Monday</th>
        <th>Tuesday</th>
        <th>Wednesday</th>
        <th>Thursday</th>
        <th>Friday</th>
        <th>Saturday</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  <script>
    (function () {{
      const cells = document.querySelectorAll('.day-cell');
      function positionCard(cell) {{
        const card = cell.querySelector('.detail-card');
        if (!card) return;
        card.classList.remove('flip-x', 'flip-y');
        const rect = card.getBoundingClientRect();
        if (rect.right > window.innerWidth - 12) {{
          card.classList.add('flip-x');
        }}
        if (rect.bottom > window.innerHeight - 12) {{
          card.classList.add('flip-y');
        }}
      }}
      cells.forEach((cell) => {{
        cell.addEventListener('mouseenter', () => requestAnimationFrame(() => positionCard(cell)));
        cell.addEventListener('focusin', () => requestAnimationFrame(() => positionCard(cell)));
        cell.addEventListener('mouseleave', () => {{
          const card = cell.querySelector('.detail-card');
          if (card) card.classList.remove('flip-x', 'flip-y');
        }});
      }});
      window.addEventListener('resize', () => {{
        document.querySelectorAll('.detail-card').forEach((card) => card.classList.remove('flip-x', 'flip-y'));
      }});
    }})();
  </script>
</body>
</html>
"""


def _server_handler_factory():
    class CalendarHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path not in {"/", "/calendar"}:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found")
                return

            query = parse_qs(parsed.query)
            today = date.today()
            year = int(query.get("year", [today.year])[0])
            month = int(query.get("month", [today.month])[0])
            opening_raw = query.get("opening", [None])[0]
            opening_balance = (
                float(opening_raw) if opening_raw not in {None, ""} else None
            )

            data = load_data()
            simulation = simulate_month(data, year, month, opening_balance)
            payload = build_calendar_html(
                simulation, opening_balance=opening_balance
            )

            encoded = payload.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args) -> None:
            return

    return CalendarHandler


def ensure_calendar_server() -> str:
    global _SERVER, _SERVER_THREAD, _SERVER_PORT
    with _SERVER_LOCK:
        if _SERVER is not None and _SERVER_PORT is not None:
            return f"http://127.0.0.1:{_SERVER_PORT}"

        handler = _server_handler_factory()
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        port = server.server_address[1]
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        _SERVER = server
        _SERVER_THREAD = thread
        _SERVER_PORT = port
        return f"http://127.0.0.1:{port}"


def open_calendar_in_browser(
    data: BudgetData,
    year: int,
    month: int,
    opening_balance: Optional[float] = None,
) -> str:
    base_url = ensure_calendar_server()
    params = {"year": year, "month": month}
    if opening_balance is not None:
        params["opening"] = opening_balance
    target = f"{base_url}/calendar?{urlencode(params)}"
    webbrowser.open(target)
    return target
