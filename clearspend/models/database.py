"""SQLite database singleton - all schema + CRUD for BudgetApp."""
from __future__ import annotations
import os
import sqlite3
from datetime import datetime, date


def _get_db_path() -> str:
    from kivy.utils import platform
    if platform == "android":
        try:
            from android.storage import app_storage_path  # type: ignore
            base = app_storage_path()
        except Exception:
            base = os.path.expanduser("~")
    else:
        base = os.path.join(os.path.expanduser("~"), ".budgetapp")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "budget.db")


class Database:
    _instance = None

    @classmethod
    def get(cls) -> "Database":
        if cls._instance is None:
            cls._instance = Database()
        return cls._instance

    def __init__(self):
        path = _get_db_path()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()
        self._seed_categories()

    # ------------------------------------------------------------------ schema
    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                amount          REAL    NOT NULL,
                type            TEXT    NOT NULL CHECK(type IN ('expense','income')),
                category        TEXT,
                description     TEXT,
                date            TEXT    NOT NULL,
                source          TEXT    DEFAULT 'manual',
                bank_account_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS bank_accounts (
                id                   INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_name            TEXT NOT NULL,
                account_name         TEXT,
                account_number_masked TEXT,
                access_token         TEXT,
                last_sync            TEXT
            );

            CREATE TABLE IF NOT EXISTS categories (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                icon TEXT
            );

            CREATE TABLE IF NOT EXISTS budgets (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                month    TEXT    NOT NULL,
                category TEXT,
                amount   REAL    NOT NULL,
                UNIQUE(month, category)
            );

            CREATE TABLE IF NOT EXISTS notifications_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                message    TEXT,
                created_at TEXT,
                read       INTEGER DEFAULT 0
            );
        """)
        self.conn.commit()

    def _seed_categories(self):
        defaults = [
            ("Food & Dining",      "food"),
            ("Transportation",     "car"),
            ("Entertainment",      "music"),
            ("Shopping",           "cart"),
            ("Utilities",          "lightning-bolt"),
            ("Healthcare",         "hospital-box"),
            ("ATM / Cash",         "cash"),
            ("Restaurants",        "silverware-fork-knife"),
            ("Rides (Uber/Lyft)",  "taxi"),
            ("Nightlife / Bars",   "glass-cocktail"),
            ("Subscriptions",      "refresh"),
            ("Salary / Income",    "briefcase"),
            ("Freelance",          "laptop"),
            ("Other",              "dots-horizontal"),
        ]
        self.conn.executemany(
            "INSERT OR IGNORE INTO categories(name, icon) VALUES (?, ?)", defaults
        )
        self.conn.commit()

    # --------------------------------------------------------- transactions
    def add_transaction(
        self,
        amount: float,
        type_: str,
        category: str,
        description: str,
        trans_date: str | None = None,
        source: str = "manual",
        bank_account_id: int | None = None,
    ) -> int:
        if trans_date is None:
            trans_date = date.today().isoformat()
        cur = self.conn.execute(
            """INSERT INTO transactions
               (amount, type, category, description, date, source, bank_account_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (amount, type_, category, description, trans_date, source, bank_account_id),
        )
        self.conn.commit()
        return cur.lastrowid

    def delete_transaction(self, transaction_id: int):
        self.conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        self.conn.commit()

    def get_transactions(
        self,
        year_month: str | None = None,
        type_: str | None = None,
        category: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict]:
        query = "SELECT * FROM transactions WHERE 1=1"
        params: list = []
        if year_month:
            query += " AND date LIKE ?"
            params.append(f"{year_month}%")
        if type_:
            query += " AND type = ?"
            params.append(type_)
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY date DESC, id DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        cur = self.conn.execute(query, params)
        return [dict(r) for r in cur]

    def get_monthly_summary(self, year_month: str | None = None) -> dict:
        if year_month is None:
            year_month = datetime.now().strftime("%Y-%m")
        cur = self.conn.execute(
            "SELECT type, SUM(amount) as total FROM transactions "
            "WHERE date LIKE ? GROUP BY type",
            (f"{year_month}%",),
        )
        result: dict = {"income": 0.0, "expense": 0.0}
        for row in cur:
            result[row["type"]] = round(row["total"] or 0.0, 2)
        result["balance"] = round(result["income"] - result["expense"], 2)
        return result

    def get_category_breakdown(self, year_month: str | None = None) -> list[dict]:
        if year_month is None:
            year_month = datetime.now().strftime("%Y-%m")
        cur = self.conn.execute(
            """SELECT category, SUM(amount) as total
               FROM transactions
               WHERE type='expense' AND date LIKE ?
               GROUP BY category
               ORDER BY total DESC""",
            (f"{year_month}%",),
        )
        return [dict(r) for r in cur]

    # --------------------------------------------------------- categories
    def get_categories(self) -> list[dict]:
        cur = self.conn.execute("SELECT name, icon FROM categories ORDER BY name")
        return [dict(r) for r in cur]

    # --------------------------------------------------------- bank accounts
    def add_bank_account(
        self,
        bank_name: str,
        account_name: str,
        account_number_masked: str,
        access_token: str = "",
    ) -> int:
        cur = self.conn.execute(
            """INSERT INTO bank_accounts
               (bank_name, account_name, account_number_masked, access_token, last_sync)
               VALUES (?, ?, ?, ?, ?)""",
            (bank_name, account_name, account_number_masked, access_token,
             datetime.now().isoformat()),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_bank_accounts(self) -> list[dict]:
        cur = self.conn.execute("SELECT * FROM bank_accounts ORDER BY id DESC")
        return [dict(r) for r in cur]

    def update_bank_sync_time(self, account_id: int):
        self.conn.execute(
            "UPDATE bank_accounts SET last_sync = ? WHERE id = ?",
            (datetime.now().isoformat(), account_id),
        )
        self.conn.commit()

    # --------------------------------------------------------- budgets (V1.5)
    def set_budget(self, month: str, category: str, amount: float):
        self.conn.execute(
            "INSERT OR REPLACE INTO budgets(month, category, amount) VALUES (?, ?, ?)",
            (month, category, amount),
        )
        self.conn.commit()

    def get_budgets(self, month: str | None = None) -> list[dict]:
        if month is None:
            month = datetime.now().strftime("%Y-%m")
        cur = self.conn.execute("SELECT * FROM budgets WHERE month = ?", (month,))
        return [dict(r) for r in cur]

    def get_budget_status(self, month: str | None = None) -> list[dict]:
        if month is None:
            month = datetime.now().strftime("%Y-%m")
        budgets = {b["category"]: b["amount"] for b in self.get_budgets(month)}
        breakdown = {r["category"]: r["total"] for r in self.get_category_breakdown(month)}
        result = []
        for cat, budget_amt in budgets.items():
            spent = breakdown.get(cat, 0.0)
            pct = min(spent / budget_amt, 1.0) if budget_amt > 0 else 0.0
            result.append({
                "category": cat,
                "budget": budget_amt,
                "spent": spent,
                "remaining": round(budget_amt - spent, 2),
                "pct": pct,
            })
        return result

    # --------------------------------------------------------- trends (V1)
    def get_recurring_transactions(self) -> list[dict]:
        """Find descriptions appearing in 2+ distinct months (recurring detection)."""
        cur = self.conn.execute(
            """SELECT description, category,
                      COUNT(DISTINCT strftime('%Y-%m', date)) AS month_count,
                      AVG(amount) AS avg_amount,
                      MAX(date) AS last_date
               FROM transactions
               WHERE type='expense'
                 AND description IS NOT NULL
                 AND TRIM(description) != ''
               GROUP BY LOWER(TRIM(description))
               HAVING month_count >= 2
               ORDER BY month_count DESC, avg_amount DESC
               LIMIT 20"""
        )
        return [dict(r) for r in cur]

    # --------------------------------------------------------- export / backup
    def export_to_dict(self) -> dict:
        return {
            "transactions": self.get_transactions(limit=100000),
            "bank_accounts": self.get_bank_accounts(),
            "exported_at": datetime.now().isoformat(),
            "schema_version": 1,
        }

    def import_from_dict(self, data: dict):
        """Restore transactions from a backup dict (skips duplicates by date+amount+description)."""
        for t in data.get("transactions", []):
            existing = self.conn.execute(
                "SELECT id FROM transactions WHERE date=? AND amount=? AND description=? LIMIT 1",
                (t.get("date"), t.get("amount"), t.get("description")),
            ).fetchone()
            if not existing:
                self.add_transaction(
                    amount=t["amount"],
                    type_=t["type"],
                    category=t.get("category", "Other"),
                    description=t.get("description", ""),
                    trans_date=t.get("date"),
                    source=t.get("source", "restore"),
                )
