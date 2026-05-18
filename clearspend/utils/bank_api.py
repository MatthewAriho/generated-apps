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
    """Plaid integration via server proxy.

    Non-sandbox calls go through a Flask proxy server that holds Plaid
    credentials.  Sandbox test-connect still calls Plaid directly.
    """

    SANDBOX_URL = "https://sandbox.plaid.com"

    def __init__(self, server_url: str = "", api_key: str = "",
                 client_id: str = "", secret: str = "",
                 environment: str = "sandbox", **_):
        self.server_url = server_url.rstrip("/") if server_url else ""
        self.api_key = api_key
        self.client_id = client_id
        self.secret = secret
        self.environment = environment
        self._accounts: list[dict] = []

    # ---- server proxy helpers ----

    def _server_post(self, path: str, payload: dict | None = None) -> dict:
        import json
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError

        url = f"{self.server_url}{path}"
        body = json.dumps(payload or {}).encode()
        req = Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        if self.api_key:
            req.add_header("X-API-Key", self.api_key)
        try:
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urlopen(req, timeout=20, context=ctx) as resp:
                return json.loads(resp.read())
        except HTTPError as e:
            try:
                err = json.loads(e.read())
                msg = err.get("description", err.get("error", str(e)))
            except Exception:
                msg = str(e)
            raise PlaidAPIError("SERVER", str(getattr(e, "code", 0)), msg)

    def _plaid_post(self, endpoint: str, payload: dict) -> dict:
        """Direct Plaid call (sandbox only)."""
        import json
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError

        url = f"{self.SANDBOX_URL}{endpoint}"
        body = json.dumps(payload).encode()
        req = Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except HTTPError as e:
            try:
                err = json.loads(e.read())
                raise PlaidAPIError(
                    err.get("error_type", "UNKNOWN"),
                    err.get("error_code", "UNKNOWN"),
                    err.get("error_message", str(e)),
                )
            except PlaidAPIError:
                raise
            except Exception:
                raise PlaidAPIError("HTTP_ERROR", str(getattr(e, "code", 0)), str(e))

    # ---- Link flow (via server) ----

    def create_link_token(self) -> dict:
        """Ask server to create a Hosted Link token. Returns { url }."""
        return self._server_post("/api/link-token")

    # ---- BankAPI interface (via server) ----

    def connect(self, public_token: str = "", **_) -> dict:
        """Exchange public_token via server proxy."""
        if not public_token:
            return {"success": False, "error": "No public_token provided."}
        try:
            return self._server_post("/api/exchange-token", {
                "public_token": public_token,
            })
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_transactions(self, access_token: str = "", cursor: str = "",
                         **_) -> dict:
        """Fetch transactions via server proxy. Server handles pagination.
        Returns dict with added (list), removed (list), cursor (str)."""
        resp = self._server_post("/api/transactions-sync", {
            "access_token": access_token,
            "cursor": cursor,
        })
        for t in resp.get("added", []):
            plaid_cat = t.get("category", "Other")
            t["category"] = _MAP_PLAID_CATEGORY.get(plaid_cat, plaid_cat)
            t.setdefault("source", "plaid")
            t.setdefault("bank_account_id", None)
        return resp

    # ---- Sandbox (direct Plaid call) ----

    def create_sandbox_token(self, institution_id: str = "ins_109508") -> str:
        """Sandbox only: create a public_token without the Link UI."""
        payload = {
            "client_id": self.client_id,
            "secret": self.secret,
            "institution_id": institution_id,
            "initial_products": ["transactions"],
        }
        resp = self._plaid_post("/sandbox/public_token/create", payload)
        return resp.get("public_token", "")


# ---------------------------------------------------------------------------
# Factory
def get_bank_api(bank_name: str, **kwargs) -> BankAPI:
    mapping = {
        "scotiabank": ScotiabankAPI,
        "plaid": PlaidAPI,
    }
    cls = mapping.get(bank_name.lower(), PlaidAPI)
    return cls(**kwargs)
