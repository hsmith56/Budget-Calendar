from __future__ import annotations

import json
import os
import threading
import webbrowser
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from plaid.api import plaid_api
from plaid.configuration import Configuration
from plaid.api_client import ApiClient
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.liabilities_get_request import LiabilitiesGetRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_recurring_get_request import TransactionsRecurringGetRequest

from budget_calendar_cli.models import Account, RecurringPayment, new_id
from budget_calendar_cli.storage import save_data


def classify_plaid_account(plaid_account: dict) -> str:
    plaid_type = str(plaid_account.get("type") or "").lower()
    subtype = str(plaid_account.get("subtype") or "other").lower()
    if plaid_type == "credit" or "credit" in subtype:
        return "credit"
    if "mortgage" in subtype:
        return "mortgage"
    if plaid_type == "loan" or "loan" in subtype:
        return "loan"
    if subtype in {"401k", "ira", "brokerage"}:
        return "brokerage"
    if subtype in {"cd", "money market"}:
        return "savings"
    if subtype in {"hsa", "cash management"}:
        return "cash"
    if subtype in {"checking", "savings", "cash"}:
        return subtype
    return "other"


def _amount_from_stream(stream: dict) -> float:
    amount = stream.get("average_amount") or stream.get("last_amount") or stream.get("amount") or 0.0
    if isinstance(amount, dict):
        amount = amount.get("amount") or 0.0
    return abs(float(amount or 0.0))


def _day_from_stream(stream: dict) -> int:
    date_text = stream.get("last_date") or stream.get("first_date") or ""
    try:
        return max(1, min(31, int(str(date_text).split("-")[-1])))
    except ValueError:
        return 1


def _account_by_plaid_id(data, plaid_account_id: str):
    return next((account for account in data.accounts if account.plaid_account_id == plaid_account_id), None)


def pull_plaid_enrichment(data) -> dict:
    client = _plaid_client()
    tokens = sorted({account.plaid_access_token for account in data.accounts if account.plaid_access_token})
    summary = {
        "tokens": len(tokens),
        "recurring_streams": 0,
        "recurring_payments_added": 0,
        "liability_items": 0,
        "investment_holdings": 0,
        "errors": [],
    }
    if not tokens:
        return summary

    data.plaid_recurring_transactions = {}
    data.plaid_liabilities = {}
    data.plaid_investments = {}
    existing_keys = {
        (payment.name.lower(), round(payment.amount, 2), tuple(payment.days), payment.source_account_id, payment.destination_account_id)
        for payment in data.recurring_payments
    }

    for access_token in tokens:
        token_key = access_token[-8:]
        try:
            recurring = client.transactions_recurring_get(
                TransactionsRecurringGetRequest(access_token=access_token)
            ).to_dict()
            data.plaid_recurring_transactions[token_key] = recurring
            streams = recurring.get("outflow_streams", []) + recurring.get("inflow_streams", [])
            summary["recurring_streams"] += len(streams)
            for stream in streams:
                account = _account_by_plaid_id(data, stream.get("account_id", ""))
                amount = _amount_from_stream(stream)
                day = _day_from_stream(stream)
                name = stream.get("merchant_name") or stream.get("description") or "Plaid recurring transaction"
                is_income = stream in recurring.get("inflow_streams", [])
                source = None if is_income else (account.id if account else data.main_account_id)
                destination = (account.id if account else data.main_account_id) if is_income else None
                key = (name.lower(), round(amount, 2), (day,), source, destination)
                if key in existing_keys:
                    continue
                data.recurring_payments.append(
                    RecurringPayment(
                        id=new_id(),
                        name=name,
                        amount=amount,
                        schedule_type="monthly_day",
                        days=[day],
                        source_account_id=source,
                        destination_account_id=destination,
                        note="Imported from Plaid recurring transactions",
                        active=True,
                    )
                )
                existing_keys.add(key)
                summary["recurring_payments_added"] += 1
        except Exception as exc:
            summary["errors"].append(f"recurring:{token_key}:{exc}")

        try:
            liabilities = client.liabilities_get(
                LiabilitiesGetRequest(access_token=access_token)
            ).to_dict()
            data.plaid_liabilities[token_key] = liabilities
            obj = liabilities.get("liabilities", {})
            summary["liability_items"] += sum(len(obj.get(name, [])) for name in ("credit", "mortgage", "student"))
        except Exception as exc:
            error_text = str(exc)
            if "ADDITIONAL_CONSENT_REQUIRED" in error_text:
                summary["errors"].append(f"liabilities:{token_key}:additional consent required; choose Update Plaid permissions")
            else:
                summary["errors"].append(f"liabilities:{token_key}:{exc}")

        try:
            investments = client.investments_holdings_get(
                InvestmentsHoldingsGetRequest(access_token=access_token)
            ).to_dict()
            data.plaid_investments[token_key] = investments
            summary["investment_holdings"] += len(investments.get("holdings", []))
        except Exception as exc:
            error_text = str(exc)
            if "ADDITIONAL_CONSENT_REQUIRED" in error_text:
                summary["errors"].append(f"investments:{token_key}:additional consent required; choose Update Plaid permissions")
            else:
                summary["errors"].append(f"investments:{token_key}:{exc}")

    save_data(data)
    return summary


def refresh_plaid_accounts(data) -> tuple[int, int]:
    client = _plaid_client()
    tokens = sorted({account.plaid_access_token for account in data.accounts if account.plaid_access_token})
    if not tokens:
        return 0, 0

    today = date.today().isoformat()
    updated = 0
    missing = 0
    accounts_by_plaid_id = {
        account.plaid_account_id: account
        for account in data.accounts
        if account.plaid_account_id
    }

    for access_token in tokens:
        balances = client.accounts_balance_get(
            AccountsBalanceGetRequest(access_token=access_token)
        ).to_dict()
        for plaid_account in balances.get("accounts", []):
            plaid_account_id = plaid_account.get("account_id", "")
            account = accounts_by_plaid_id.get(plaid_account_id)
            if account is None:
                missing += 1
                continue
            current = plaid_account.get("balances", {}).get("current")
            if current is None:
                current = 0.0
            account.balance = float(current)
            account.as_of_date = today
            account.account_type = classify_plaid_account(plaid_account)
            if plaid_account.get("name"):
                account.name = plaid_account["name"]
            updated += 1

    save_data(data)
    return updated, missing

PLAID_HOSTS = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}


def _plaid_client() -> plaid_api.PlaidApi:
    client_id = os.getenv("PLAID_CLIENT_ID")
    secret = os.getenv("PLAID_SECRET")
    env = os.getenv("PLAID_ENV", "sandbox").lower()
    if not client_id or not secret:
        raise RuntimeError("Set PLAID_CLIENT_ID and PLAID_SECRET env vars first.")
    if env not in PLAID_HOSTS:
        raise RuntimeError("PLAID_ENV must be sandbox, development, or production.")
    config = Configuration(
        host=PLAID_HOSTS[env],
        api_key={"clientId": client_id, "secret": secret},
    )
    return plaid_api.PlaidApi(ApiClient(config))


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _html_page() -> bytes:
    return b"""<!doctype html>
<html>
<head><meta charset="utf-8"><title>Plaid Link</title></head>
<body>
  <h1>Link bank account</h1>
  <button id="link">Open Plaid Link</button>
  <pre id="status"></pre>
  <script src="https://cdn.plaid.com/link/v2/stable/link-initialize.js"></script>
  <script>
    const status = document.getElementById('status');
    const log = (msg) => status.textContent += msg;
    document.getElementById('link').onclick = async () => {
      log('Creating link token...');
      const tokenRes = await fetch('/create_link_token', {method: 'POST'});
      const tokenJson = await tokenRes.json();
      if (!tokenRes.ok) { log(tokenJson.error || 'Failed'); return; }
      Plaid.create({
        token: tokenJson.link_token,
        onSuccess: async (public_token, metadata) => {
          log('Exchanging public token...');
          const res = await fetch('/exchange_public_token', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({public_token, metadata})
          });
          const payload = await res.json();
          if (!res.ok) { log(payload.error || 'Failed'); return; }
          log('Linked ' + payload.added + ' account(s). You can close this tab.');
        },
        onExit: (err) => { if (err) log(err.error_message || JSON.stringify(err)); }
      }).open();
    };
  </script>
</body>
</html>
"""


def update_plaid_permissions(data) -> None:
    client = _plaid_client()
    access_token = next((account.plaid_access_token for account in data.accounts if account.plaid_access_token), "")
    if not access_token:
        print("No Plaid account linked yet.")
        return
    done = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            return

        def do_GET(self) -> None:
            if self.path != "/":
                _json_response(self, 404, {"error": "Not found"})
                return
            body = _html_page()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            try:
                if self.path == "/create_link_token":
                    request = LinkTokenCreateRequest(
                        client_name="Budget Calendar",
                        country_codes=[CountryCode("US")],
                        language="en",
                        user=LinkTokenCreateRequestUser(client_user_id="local-user"),
                        access_token=access_token,
                        additional_consented_products=[Products("liabilities"), Products("investments")],
                    )
                    response = client.link_token_create(request).to_dict()
                    _json_response(self, 200, {"link_token": response["link_token"]})
                    return

                if self.path == "/exchange_public_token":
                    _json_response(self, 200, {"added": 0})
                    done.set()
                    return

                _json_response(self, 404, {"error": "Not found"})
            except Exception as exc:
                _json_response(self, 500, {"error": str(exc)})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}/"
    print(f"Opening Plaid permission update: {url}")
    webbrowser.open(url)
    done.wait(timeout=300)
    server.shutdown()
    if done.is_set():
        print("Plaid permissions updated. Run Pull Plaid data again.")
    else:
        print("Plaid permission update timed out or cancelled.")


def link_plaid_accounts(data) -> None:
    client = _plaid_client()
    done = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            return

        def do_GET(self) -> None:
            if self.path != "/":
                _json_response(self, 404, {"error": "Not found"})
                return
            body = _html_page()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self) -> None:
            try:
                if self.path == "/create_link_token":
                    request = LinkTokenCreateRequest(
                        products=[Products("transactions"), Products("liabilities"), Products("investments")],
                        client_name="Budget Calendar",
                        country_codes=[CountryCode("US")],
                        language="en",
                        user=LinkTokenCreateRequestUser(client_user_id="local-user"),
                    )
                    response = client.link_token_create(request).to_dict()
                    _json_response(self, 200, {"link_token": response["link_token"]})
                    return

                if self.path == "/exchange_public_token":
                    length = int(self.headers.get("Content-Length", "0"))
                    payload = json.loads(self.rfile.read(length) or b"{}")
                    exchange = client.item_public_token_exchange(
                        ItemPublicTokenExchangeRequest(public_token=payload["public_token"])
                    ).to_dict()
                    access_token = exchange["access_token"]
                    item_id = exchange["item_id"]
                    balances = client.accounts_balance_get(
                        AccountsBalanceGetRequest(access_token=access_token)
                    ).to_dict()
                    added = 0
                    for plaid_account in balances.get("accounts", []):
                        account_type = classify_plaid_account(plaid_account)
                        current = plaid_account.get("balances", {}).get("current") or 0.0
                        account = Account(
                            id=new_id(),
                            name=plaid_account.get("name") or "Plaid Account",
                            kind="payout",
                            balance=float(current),
                            as_of_date=date.today().isoformat(),
                            account_type=account_type,
                            plaid_access_token=access_token,
                            plaid_item_id=item_id,
                            plaid_account_id=plaid_account.get("account_id", ""),
                        )
                        data.accounts.append(account)
                        added += 1
                    save_data(data)
                    _json_response(self, 200, {"added": added})
                    done.set()
                    return

                _json_response(self, 404, {"error": "Not found"})
            except Exception as exc:
                _json_response(self, 500, {"error": str(exc)})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}/"
    print(f"Opening Plaid Link: {url}")
    print("Access token will be stored in .budget_calendar/data.json. Keep this file private.")
    webbrowser.open(url)
    done.wait(timeout=300)
    server.shutdown()
    if done.is_set():
        print("Plaid account link complete.")
    else:
        print("Plaid account link timed out or cancelled.")
