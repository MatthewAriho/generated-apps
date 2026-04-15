"""Bank API abstraction layer.

V0.1: ScotiabankAPI is fully mocked - real implementation requires OAuth2
business registration at developer.scotiabank.com.  GenericBankAPI is a
stub for future Plaid-style integration.
"""
from __future__ import annotations
import random
from datetime import datetime, timedelta


class BankAPI:
    """Abstract base for all bank integrations."""

    def connect(self, **credentials) -> dict:
        raise NotImplementedError

    def get_accounts(self) -> list[dict]:
        raise NotImplementedError

    def get_transactions(self, account_id: str, from_date: str | None = None) -> list[dict]:
        raise NotImplementedError


# ---------------------------------------------------------------------------
class ScotiabankAPI(BankAPI):
    """Mock Scotiabank API - returns realistic fixture data.

    NOTE: Production use requires registering at developer.scotiabank.com
    and implementing proper OAuth 2.0 with PKCE flow.  The BASE_URL below
    is a placeholder and will return 404 without valid credentials.
    """

    BASE_URL = "https://api.scotiabank.com/retail/v1"  # requires business OAuth

    # Typical category patterns seen in Scotiabank transactions
    _MOCK_EXPENSE_PATTERNS = [
        ("Tim Hortons",              "Food & Dining",      4.85,   1.50),
        ("Metro Grocery",            "Food & Dining",     92.50,  30.00),
        ("Shoppers Drug Mart",       "Healthcare",        28.40,  15.00),
        ("TTC Fare",                 "Transportation",     3.25,   0.50),
        ("Netflix",                  "Subscriptions",     16.99,   0.00),
        ("Spotify",                  "Subscriptions",     10.99,   0.00),
        ("LCBO",                     "Nightlife / Bars",  42.15,  20.00),
        ("Uber",                     "Rides (Uber/Lyft)", 18.50,   8.00),
        ("Uber Eats",                "Food & Dining",     35.20,  12.00),
        ("Restaurant Terroni",       "Restaurants",       75.00,  25.00),
        ("ATM Withdrawal",           "ATM / Cash",       100.00,  50.00),
        ("Amazon.ca",                "Shopping",          52.40,  30.00),
        ("H&M",                      "Shopping",          65.00,  20.00),
        ("Bell Canada",              "Utilities",         85.00,   5.00),
        ("Toronto Hydro",            "Utilities",         95.00,  15.00),
        ("Goodlife Fitness",         "Healthcare",        49.99,   0.00),
        ("Cineplex",                 "Entertainment",     25.00,   5.00),
        ("Steam Purchase",           "Entertainment",     29.99,  15.00),
    ]

    def __init__(self):
        self.access_token: str | None = None
        self._accounts: list[dict] = []

    def connect(self, username: str = "", password: str = "", **_) -> dict:
        """Simulate OAuth2 token exchange (mock)."""
        self.access_token = "mock_scotia_token_" + str(random.randint(10000, 99999))
        self._accounts = [
            {
                "id": "acc_chq_001",
                "name": "Everyday Chequing",
                "number": "****1234",
                "balance": round(random.uniform(800, 4000), 2),
                "type": "chequing",
                "currency": "CAD",
            },
            {
                "id": "acc_sav_002",
                "name": "MomentumPLUS Savings",
                "number": "****5678",
                "balance": round(random.uniform(5000, 20000), 2),
                "type": "savings",
                "currency": "CAD",
            },
        ]
        return {"success": True, "accounts": self._accounts}

    def get_accounts(self) -> list[dict]:
        return self._accounts

    def get_transactions(
        self, account_id: str = "acc_chq_001", from_date: str | None = None
    ) -> list[dict]:
        """Return mock transactions for the past 30 days."""
        today = datetime.now()
        txns: list[dict] = []

        # Generate ~15-25 random expenses
        count = random.randint(15, 25)
        for _ in range(count):
            name, cat, base_amt, variance = random.choice(self._MOCK_EXPENSE_PATTERNS)
            amt = round(base_amt + random.uniform(-variance, variance), 2)
            days_ago = random.randint(0, 30)
            txns.append({
                "description": name,
                "category": cat,
                "amount": max(0.01, amt),
                "type": "expense",
                "date": (today - timedelta(days=days_ago)).strftime("%Y-%m-%d"),
                "source": "scotiabank",
                "bank_account_id": None,
            })

        # Two pay deposits
        for i, days in enumerate([7, 21]):
            txns.append({
                "description": "Payroll Direct Deposit",
                "category": "Salary / Income",
                "amount": round(random.uniform(2800, 3500), 2),
                "type": "income",
                "date": (today - timedelta(days=days)).strftime("%Y-%m-%d"),
                "source": "scotiabank",
                "bank_account_id": None,
            })

        # Filter by from_date if provided
        if from_date:
            txns = [t for t in txns if t["date"] >= from_date]

        return sorted(txns, key=lambda x: x["date"], reverse=True)


# ---------------------------------------------------------------------------
# Plaid category -> app category mapping
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
    """Raised when Plaid returns an error response."""
    def __init__(self, error_type: str, error_code: str, message: str):
        self.error_type = error_type
        self.error_code = error_code
        super().__init__(f"Plaid {error_type}/{error_code}: {message}")


class PlaidAPI(BankAPI):
    """Plaid integration for connecting to US/CA bank accounts.

    Supports sandbox, development, and production environments.
    Uses the Plaid API v2 with /transactions/sync for incremental updates.
    """

    ENVIRONMENTS = {
        "sandbox":     "https://sandbox.plaid.com",
        "development": "https://development.plaid.com",
        "production":  "https://production.plaid.com",
    }

    REDIRECT_URI = "clearspend://plaid-callback"

    def __init__(self, client_id: str = "", secret: str = "",
                 environment: str = "sandbox", **_):
        self.client_id = client_id
        self.secret = secret
        self.environment = environment
        self._accounts: list[dict] = []

    def _base_url(self) -> str:
        return self.ENVIRONMENTS.get(self.environment, self.ENVIRONMENTS["sandbox"])

    def _post(self, endpoint: str, payload: dict) -> dict:
        """POST JSON to Plaid API. Returns parsed response dict."""
        import json
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError

        url = f"{self._base_url()}{endpoint}"
        body = json.dumps(payload).encode("utf-8")
        req = Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")

        try:
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as e:
            try:
                err = json.loads(e.read().decode("utf-8"))
                raise PlaidAPIError(
                    err.get("error_type", "UNKNOWN"),
                    err.get("error_code", "UNKNOWN"),
                    err.get("error_message", str(e)),
                )
            except (json.JSONDecodeError, PlaidAPIError):
                raise
            except Exception:
                raise PlaidAPIError("HTTP_ERROR", str(e.code), str(e))

    def _auth_payload(self) -> dict:
        """Base payload with client credentials."""
        return {"client_id": self.client_id, "secret": self.secret}

    # ---------------------------------------------------------------- Link flow
    def create_link_token(self, user_id: str = "clearspend_user",
                          redirect_uri: str = "") -> dict:
        """Create a Link token for opening Plaid Link in browser."""
        payload = {
            **self._auth_payload(),
            "user": {"client_user_id": user_id},
            "client_name": "ClearSpend",
            "products": ["transactions"],
            "country_codes": ["US", "CA"],
            "language": "en",
        }
        if redirect_uri:
            payload["redirect_uri"] = redirect_uri
        return self._post("/link/token/create", payload)

    def exchange_public_token(self, public_token: str) -> dict:
        """Exchange a public_token from Link for a permanent access_token."""
        payload = {**self._auth_payload(), "public_token": public_token}
        return self._post("/item/public_token/exchange", payload)

    # ---------------------------------------------------------------- Sandbox helper
    def create_sandbox_token(self, institution_id: str = "ins_109508") -> str:
        """Sandbox only: create a public_token without the Link UI.
        Default institution is First Platypus Bank (Plaid sandbox)."""
        payload = {
            **self._auth_payload(),
            "institution_id": institution_id,
            "initial_products": ["transactions"],
        }
        resp = self._post("/sandbox/public_token/create", payload)
        return resp.get("public_token", "")

    # ---------------------------------------------------------------- BankAPI interface
    def connect(self, public_token: str = "", **_) -> dict:
        """Exchange public_token, fetch accounts, return normalized result."""
        if not public_token:
            return {"success": False, "error": "No public_token provided."}
        try:
            exchange = self.exchange_public_token(public_token)
            access_token = exchange.get("access_token", "")
            item_id = exchange.get("item_id", "")

            accounts = self.get_accounts(access_token=access_token)
            return {
                "success": True,
                "accounts": accounts,
                "access_token": access_token,
                "item_id": item_id,
            }
        except PlaidAPIError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_accounts(self, access_token: str = "", **_) -> list[dict]:
        """Fetch accounts for the given access_token."""
        payload = {**self._auth_payload(), "access_token": access_token}
        resp = self._post("/accounts/get", payload)
        accounts = []
        for acc in resp.get("accounts", []):
            mask = acc.get("mask", "****")
            accounts.append({
                "id": acc.get("account_id", ""),
                "name": acc.get("name", "Account"),
                "number": f"****{mask}" if mask else "****",
                "balance": acc.get("balances", {}).get("current", 0.0),
                "type": acc.get("subtype", acc.get("type", "checking")),
                "currency": acc.get("balances", {}).get("iso_currency_code", "CAD"),
            })
        self._accounts = accounts
        return accounts

    def get_transactions(self, account_id: str = "", from_date: str | None = None,
                         access_token: str = "", cursor: str = "",
                         **_) -> dict:
        """Fetch transactions via /transactions/sync (incremental).

        Returns dict with keys: added (list[dict]), removed (list[str]),
        cursor (str), has_more (bool).
        """
        all_added: list[dict] = []
        all_removed: list[str] = []
        current_cursor = cursor
        has_more = True

        while has_more:
            payload = {
                **self._auth_payload(),
                "access_token": access_token,
                "cursor": current_cursor,
                "count": 100,
            }
            resp = self._post("/transactions/sync", payload)

            for t in resp.get("added", []):
                # Plaid: amount > 0 = debit (expense), amount < 0 = credit (income)
                raw_amount = t.get("amount", 0)
                tx_type = "expense" if raw_amount > 0 else "income"
                amount = abs(raw_amount)

                # Map Plaid category to app category
                pfc = t.get("personal_finance_category", {})
                plaid_cat = pfc.get("primary", "")
                app_cat = _MAP_PLAID_CATEGORY.get(plaid_cat, "Other")

                all_added.append({
                    "description": (t.get("name") or t.get("merchant_name") or "")[:100],
                    "category": app_cat,
                    "amount": round(amount, 2),
                    "type": tx_type,
                    "date": t.get("date", ""),
                    "source": "plaid",
                    "bank_account_id": None,
                    "plaid_transaction_id": t.get("transaction_id", ""),
                })

            for t in resp.get("removed", []):
                tid = t.get("transaction_id", "")
                if tid:
                    all_removed.append(tid)

            current_cursor = resp.get("next_cursor", current_cursor)
            has_more = resp.get("has_more", False)

        return {
            "added": all_added,
            "removed": all_removed,
            "cursor": current_cursor,
            "has_more": False,
        }

    def get_link_url(self, link_token: str) -> str:
        """Build the Plaid Link URL to open in a browser."""
        base = "https://cdn.plaid.com/link/v2/stable/link.html"
        return f"{base}?isWebview=true&token={link_token}"


# ---------------------------------------------------------------------------
# Factory
def get_bank_api(bank_name: str, **kwargs) -> BankAPI:
    mapping = {
        "scotiabank": ScotiabankAPI,
        "plaid": PlaidAPI,
    }
    cls = mapping.get(bank_name.lower(), PlaidAPI)
    return cls(**kwargs)
