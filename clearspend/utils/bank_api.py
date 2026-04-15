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
class GenericBankAPI(BankAPI):
    """Stub for Plaid/Flinks-style integration for other Canadian banks.

    Supported institutions (when real keys are provided):
    - TD Bank, RBC, BMO, CIBC, National Bank via Flinks API
    - Any Plaid-supported institution (US/CA)
    """

    def __init__(self, api_key: str = "", institution_id: str = ""):
        self.api_key = api_key
        self.institution_id = institution_id
        self._access_token: str | None = None

    def connect(self, public_token: str = "", **_) -> dict:
        # TODO: exchange public_token via Flinks/Plaid API
        return {"success": False, "error": "Generic bank API not configured yet."}

    def get_accounts(self) -> list[dict]:
        return []

    def get_transactions(self, account_id: str, from_date: str | None = None) -> list[dict]:
        return []


# ---------------------------------------------------------------------------
# Factory
def get_bank_api(bank_name: str, **kwargs) -> BankAPI:
    mapping = {
        "scotiabank": ScotiabankAPI,
        "generic": GenericBankAPI,
    }
    cls = mapping.get(bank_name.lower(), GenericBankAPI)
    return cls(**kwargs)
