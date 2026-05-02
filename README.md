# Budget Calendar

A small `uv`-managed CLI budget planner for:

- viewing accounts
- adding payout accounts
- updating balances
- setting daily-compounding interest rates on accounts
- assigning simple account type labels like checking, savings, brokerage, credit, cash, or other
- adding one-time scheduled payments
- adding recurring payments
- adding recurring transfers between accounts
- importing onboarding text files
- opening a browser calendar view with the daily running main-account balance

## Setup

```bash
uv sync
```

If you add libraries later, use:

```bash
uv add <package>
```

## Run

```bash
uv run budget-calendar
```

Or:

```bash
uv run python BudgetCalendar.py
```

## Data location

```text
./.budget_calendar/data.json
```

Calendar HTML files are written to:

```text
./.budget_calendar/
```

## Onboarding import

Use menu option `8. Import onboarding text file`.

A template is included at:

```text
examples/onboarding-template.txt
```

Supported patterns include:

- `21st every month`
- `1st every month`
- `first and 15`
- `10th and 25th`
- `Biweekly mondays`
- recurring transfer rows with `name amount schedule from to [note]`

Example:

```text
MAIN ACCOUNT
Chase Checking    5000.00    5/2

PAYOUT ACCOUNTS
Vio Savings    12000.00    5/2

PAYMENTS
Credit Card    -850.00    5/26
Bonus Payment    500.00    5/5

RECURRING BILLS
Student Loan    -149.50    21st every month
Cleaning    -110.00    Biweekly mondays
Rent payment    -2000.00    1st every month

RECURRING INCOME
Payroll A    1488.20    first and 15
Payroll B    3380.00    10th and 25th

RECURRING TRANSFERS    FROM    TO
Chase to Vio    2100.00    5th every month    Chase Checking    Vio Savings    Monthly savings transfer
```
