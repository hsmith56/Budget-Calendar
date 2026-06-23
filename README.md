<a id="readme-top"></a>

<div align="center">
  <h3 align="center">Budget Calendar</h3>

  <p align="center">
    CLI budget planner for account balances, scheduled payments, recurring transfers, Plaid-linked accounts, and projected monthly cash flow.
    <br />
    <a href="https://github.com/hsmith56/Budget-Calendar"><strong>View repository »</strong></a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li><a href="#about-the-project">About The Project</a></li>
    <li><a href="#built-with">Built With</a></li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
    <li><a href="#data-storage">Data Storage</a></li>
    <li><a href="#plaid-setup">Plaid Setup</a></li>
    <li><a href="#onboarding-import">Onboarding Import</a></li>
    <li><a href="#development">Development</a></li>
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

Budget Calendar stores local budget data in JSON, then uses that data to forecast daily balances, net worth, recurring payments, transfers, and daily-compounding account interest. It includes an interactive terminal menu plus browser-based calendar and net-worth views.

### Features

- Manage main, payout, checking, savings, brokerage, credit, loan, mortgage, cash, and other accounts
- Track one-time scheduled payments
- Track recurring monthly and biweekly payments
- Track recurring transfers between accounts
- Project daily running main-account balance
- Project account balances, net worth, liabilities, and monthly interest
- Open browser calendar and net-worth views
- Import onboarding text files from a simple template
- Link Plaid accounts, refresh balances, and import Plaid recurring transaction/liability/investment data

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- BUILT WITH -->
## Built With

[![Python][python-shield]][python-url]
[![uv][uv-shield]][uv-url]
[![Plaid][plaid-shield]][plaid-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- GETTING STARTED -->
## Getting Started

### Prerequisites

- Python 3.11+
- `uv`

Install `uv` if needed:

```bash
pip install uv
```

### Installation

Clone repository:

```bash
git clone https://github.com/hsmith56/Budget-Calendar.git
cd Budget-Calendar
```

Install dependencies:

```bash
uv sync
```

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- USAGE -->
## Usage

Start CLI:

```bash
uv run budget-calendar
```

Alternative entry point:

```bash
uv run python BudgetCalendar.py
```

Menu options:

1. View accounts
2. Add payout account
3. Update account balance
4. Set account type / interest
5. Add one-time scheduled payment
6. View scheduled payments
7. Add recurring payment or transfer
8. View recurring payments and transfers
9. Import onboarding text file
10. Open calendar view in browser
11. Link Plaid account
12. Pull Plaid data
13. Update Plaid permissions
14. View net worth
15. Exit

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- DATA STORAGE -->
## Data Storage

Budget data is stored locally:

```text
./.budget_calendar/data.json
```

Generated calendar/server assets live under:

```text
./.budget_calendar/
```

> Plaid access tokens are stored in `.budget_calendar/data.json`. Keep this file private and do not commit it.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- PLAID SETUP -->
## Plaid Setup

Plaid features require environment variables:

```bash
PLAID_CLIENT_ID=<your-client-id>
PLAID_SECRET=<your-secret>
PLAID_ENV=sandbox
```

`PLAID_ENV` can be `sandbox`, `development`, or `production`.

Use CLI option `11. Link Plaid account` after setting credentials. Use option `12. Pull Plaid data` to refresh balances and import supported enrichment data.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ONBOARDING IMPORT -->
## Onboarding Import

Use menu option `9. Import onboarding text file`.

Template:

```text
examples/onboarding-template.txt
```

Supported schedule patterns include:

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

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- DEVELOPMENT -->
## Development

Run CLI from source:

```bash
uv run budget-calendar
```

Add dependencies:

```bash
uv add <package>
```

Build package artifacts:

```bash
uv build
```

No test command is currently defined in `pyproject.toml`.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- LICENSE -->
## License

Copyright © 2021 hsmith56.

This project may not be copied or distributed without express permission. See [`license`](license).

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

hsmith56 - hsmith56@pm.me

Project Link: [https://github.com/hsmith56/Budget-Calendar](https://github.com/hsmith56/Budget-Calendar)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
## Acknowledgments

- README structure inspired by [Best-README-Template](https://github.com/othneildrew/Best-README-Template)
- [uv](https://docs.astral.sh/uv/)
- [Plaid Python](https://github.com/plaid/plaid-python)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- MARKDOWN LINKS & IMAGES -->
[python-shield]: https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white
[python-url]: https://www.python.org/
[uv-shield]: https://img.shields.io/badge/uv-package%20manager-2B0231?style=for-the-badge
[uv-url]: https://docs.astral.sh/uv/
[plaid-shield]: https://img.shields.io/badge/Plaid-Python-00D54B?style=for-the-badge
[plaid-url]: https://github.com/plaid/plaid-python
