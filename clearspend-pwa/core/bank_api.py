"""Bank API abstraction layer — Plaid integration + Scotiabank mock."""
from __future__ import annotations

import json
import random
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timedelta


class BankAPI:
    def connect(self, **credentials) -> dict:
        raise NotImplementedError

    def get_accounts(self) -> list[dict]:
        raise NotImplementedError

    def get_transactions(self, **kwargs) -> dict | list[dict]:
        raise NotImplementedError


class ScotiabankAPI(BankAPI):
    """Mock Scotiabank API — returns realistic fixture data."""

    _MOCK_EXPENSE_PATTERNS = [
        ("Tim Hortons",         "Food & Dining",      4.85,  1.50),
        ("Metro Grocery",       "Food & Dining",     92.50, 30.00),
        ("Shoppers Drug Mart",  "Healthcare",        28.40, 15.00),
        ("TTC Fare",            "Transportation",     3.25,  0.50),
        ("Netflix",             "Subscriptions",     16.99,  0.00),
        ("Spotify",             "Subscriptions",     10.99,  0.00),
        ("LCBO",                "Nightlife / Bars",  42.15, 20.00),
        ("Uber",                "Rides (Uber/Lyft)", 18.50,  8.00),
        ("Uber Eats",           "Food & Dining",     35.20, 12.00),
        ("Restaurant Terroni",  "Restaurants",       75.00, 25.00),
        ("ATM Withdrawal",      "ATM / Cash",       100.00, 50.00),
        ("Amazon.ca",           "Shopping",          52.40, 30.00),
        ("H&M",                 "Shopping",          65.00, 20.00),
        ("Bell Canada",         "Utilities",         85.00,  5.00),
        ("Toronto Hydro",       "Utilities",         95.00, 15.00),
        ("Goodlife Fitness",    "Healthcare",        49.99,  0.00),
        ("Cineplex",            "Entertainment",     25.00,  5.00),
        ("Steam Purchase",      "Entertainment",     29.99, 15.00),
    ]

    def __init__(self):
        self.access_token: str | None = None
        self._accounts: list[dict] = []

    def connect(self, username: str = "", password: str = "", **_) -> dict:
        self.access_token = "mock_scotia_token_" + str(random.randint(10000, 99999))
        self._accounts = [
            {"id": "acc_chq_001", "name": "Everyday Chequing", "number": "****1234",
             "balance": round(random.uniform(800, 4000), 2), "type": "chequing"},
            {"id": "acc_sav_002", "name": "MomentumPLUS Savings", "number": "****5678",
             "balance": round(random.uniform(5000, 20000), 2), "type": "savings"},
        ]
        return {"success": True, "accounts": self._accounts}

    def get_accounts(self) -> list[dict]:
        return self._accounts

    def get_transactions(self, account_id: str = "acc_chq_001",
                         from_date: str | None = None, **_) -> list[dict]:
        today = datetime.now()
        txns: list[dict] = []
        count = random.randint(15, 25)
        for _ in range(count):
            name, cat, base_amt, variance = random.choice(self._MOCK_EXPENSE_PATTERNS)
            amt = round(base_amt + random.uniform(-variance, variance), 2)
            days_ago = random.randint(0, 30)
            txns.append({"description": name, "category": cat, "amount": max(0.01, amt),
                         "type": "expense", "date": (today - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
                         "source": "scotiabank", "bank_account_id": None})
        for i, days in enumerate([7, 21]):
            txns.append({"description": "Payroll Direct Deposit", "category": "Salary / Income",
                         "amount": round(random.uniform(2800, 3500), 2), "type": "income",
                         "date": (today - timedelta(days=days)).strftime("%Y-%m-%d"),
                         "source": "scotiabank", "bank_account_id": None})
        if from_date:
            txns = [t for t in txns if t["date"] >= from_date]
        return sorted(txns, key=lambda x: x["date"], reverse=True)


# Plaid category mapping
_MAP_PLAID_CATEGORY = {
    "FOOD_AND_DRINK": "Food & Dining",
    "TRANSPORTATION": "Transportation",
    "ENTERTAINMENT": "Entertainment",
    "GENERAL_MERCHANDISE": "Shopping",
    "SHOPPING": "Shopping",
    "MEDICAL": "Healthcare",
    "PERSONAL_CARE": "Healthcare",
    "RENT_AND_UTILITIES": "Utilities",
    "INCOME": "Salary / Income",
    "TRANSFER_IN": "Salary / Income",
    "TRANSFER_OUT": "ATM / Cash",
    "TRAVEL": "Transportation",
    "LOAN_PAYMENTS": "Utilities",
    "BANK_FEES": "Other",
    "HOME_IMPROVEMENT": "Shopping",
    "GENERAL_SERVICES": "Other",
    "GOVERNMENT_AND_NON_PROFIT": "Other",
}


class PlaidAPIError(Exception):
    def __init__(self, error_type: str, error_code: str, message: str):
        self.error_type = error_type
        self.error_code = error_code
        super().__init__(f"Plaid {error_type}/{error_code}: {message}")


class PlaidAPI(BankAPI):
    """Plaid integration via server proxy."""

    SANDBOX_URL = "https://sandbox.plaid.com"

    def __init__(self, server_url: str = "", api_key: str = "",
                 client_id: str = "", secret: str = "",
                 environment: str = "sandbox", **_):
        self.server_url = server_url.rstrip("/") if server_url else ""
        self.api_key = api_key
        self.client_id = client_id
        self.secret = secret
        self.environment = environment

    def _server_post(self, path: str, payload: dict | None = None) -> dict:
        url = f"{self.server_url}{path}"
        body = json.dumps(payload or {}).encode()
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        if self.api_key:
            req.add_header("X-API-Key", self.api_key)
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                return json.loads(resp.read())
        except urllib.error.HTTPError as e:
            try:
                err = json.loads(e.read())
                msg = err.get("description", err.get("error", str(e)))
            except Exception:
                msg = str(e)
            raise PlaidAPIError("SERVER", str(getattr(e, "code", 0)), msg)

    def create_link_token(self) -> dict:
        return self._server_post("/api/link-token")

    def complete_link(self, session_id: str) -> dict:
        try:
            return self._server_post("/api/complete-link", {"session_id": session_id})
        except Exception as e:
            return {"success": False, "error": str(e)}

    def connect(self, public_token: str = "", **_) -> dict:
        if not public_token:
            return {"success": False, "error": "No public_token provided."}
        try:
            return self._server_post("/api/exchange-token", {"public_token": public_token})
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_transactions(self, access_token: str = "", cursor: str = "", **_) -> dict:
        resp = self._server_post("/api/transactions-sync", {
            "access_token": access_token, "cursor": cursor,
        })
        for t in resp.get("added", []):
            plaid_cat = t.get("category", "Other")
            t["category"] = _MAP_PLAID_CATEGORY.get(plaid_cat, plaid_cat)
            t.setdefault("source", "plaid")
            t.setdefault("bank_account_id", None)
        return resp


def get_bank_api(bank_name: str, **kwargs) -> BankAPI:
    mapping = {"scotiabank": ScotiabankAPI, "plaid": PlaidAPI}
    cls = mapping.get(bank_name.lower(), PlaidAPI)
    return cls(**kwargs)
