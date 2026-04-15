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
        self._migrate_v2()
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

    def _migrate_v2(self):
        """Add Plaid-related columns if they do not exist yet."""
        def _has_column(table: str, column: str) -> bool:
            cur = self.conn.execute(f"PRAGMA table_info({table})")
            return any(row[1] == column for row in cur.fetchall())

        if not _has_column("bank_accounts", "item_id"):
            self.conn.execute("ALTER TABLE bank_accounts ADD COLUMN item_id TEXT DEFAULT ''")
        if not _has_column("bank_accounts", "environment"):
            self.conn.execute("ALTER TABLE bank_accounts ADD COLUMN environment TEXT DEFAULT 'sandbox'")
        if not _has_column("transactions", "plaid_transaction_id"):
            self.conn.execute("ALTER TABLE transactions ADD COLUMN plaid_transaction_id TEXT DEFAULT ''")

        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS plaid_sync_cursors (
                bank_account_id INTEGER PRIMARY KEY,
                cursor TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (bank_account_id) REFERENCES bank_accounts(id)
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
        plaid_transaction_id: str = "",
    ) -> int:
        if trans_date is None:
            trans_date = date.today().isoformat()
        cur = self.conn.execute(
            """INSERT INTO transactions
               (amount, type, category, description, date, source,
                bank_account_id, plaid_transaction_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (amount, type_, category, description, trans_date, source,
             bank_account_id, plaid_transaction_id),
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

    def get_monthly_summaries(self, num_months: int = 6) -> list[dict]:
        """Return income/expense summaries for the last N months."""
        results = []
        now = datetime.now()
        for offset in range(num_months - 1, -1, -1):
            m = now.month - offset
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            ym = f"{y:04d}-{m:02d}"
            s = self.get_monthly_summary(ym)
            s["month"] = ym
            s["label"] = date(y, m, 1).strftime("%b")
            results.append(s)
        return results

    def get_daily_spending(self, year_month: str) -> list[dict]:
        """Return day-by-day expense totals for a month."""
        cur = self.conn.execute(
            """SELECT date, SUM(amount) as total
               FROM transactions
               WHERE type='expense' AND date LIKE ?
               GROUP BY date
               ORDER BY date""",
            (f"{year_month}%",),
        )
        return [dict(r) for r in cur]

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
        item_id: str = "",
        environment: str = "sandbox",
    ) -> int:
        cur = self.conn.execute(
            """INSERT INTO bank_accounts
               (bank_name, account_name, account_number_masked, access_token,
                last_sync, item_id, environment)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (bank_name, account_name, account_number_masked, access_token,
             datetime.now().isoformat(), item_id, environment),
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

    # --------------------------------------------------------- plaid sync cursors
    def get_plaid_cursor(self, bank_account_id: int) -> str:
        cur = self.conn.execute(
            "SELECT cursor FROM plaid_sync_cursors WHERE bank_account_id = ?",
            (bank_account_id,),
        )
        row = cur.fetchone()
        return row["cursor"] if row else ""

    def set_plaid_cursor(self, bank_account_id: int, cursor: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO plaid_sync_cursors(bank_account_id, cursor) VALUES (?, ?)",
            (bank_account_id, cursor),
        )
        self.conn.commit()

    def delete_transactions_by_plaid_id(self, plaid_ids: list[str]):
        """Remove transactions that Plaid reports as deleted."""
        if not plaid_ids:
            return
        placeholders = ",".join("?" * len(plaid_ids))
        self.conn.execute(
            f"DELETE FROM transactions WHERE plaid_transaction_id IN ({placeholders})",
            plaid_ids,
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

    # --------------------------------------------------------- demo data
    def seed_demo_data(self):
        """Insert realistic demo transactions across 3 months + budgets."""
        import random
        now = datetime.now()
        year = now.year
        month = now.month

        # Build 3 months of year-month strings: current, prev, prev-prev
        months = []
        for offset in range(3):
            m = month - offset
            y = year
            while m <= 0:
                m += 12
                y -= 1
            months.append(f"{y:04d}-{m:02d}")

        # Demo transactions
        expense_items = [
            ("Food & Dining",      "Grocery run",          35.00, 85.00),
            ("Restaurants",        "Lunch with team",      15.00, 55.00),
            ("Restaurants",        "Dinner out",           25.00, 70.00),
            ("Transportation",    "Gas fillup",           40.00, 75.00),
            ("Rides (Uber/Lyft)", "Uber to downtown",     12.00, 28.00),
            ("Entertainment",     "Movie tickets",        14.00, 22.00),
            ("Shopping",          "Amazon order",         20.00, 90.00),
            ("Utilities",         "Electric bill",        60.00, 95.00),
            ("Utilities",         "Internet bill",        55.00, 65.00),
            ("ATM / Cash",        "ATM withdrawal",       40.00, 100.00),
            ("Subscriptions",     "Netflix",              15.99, 15.99),
            ("Subscriptions",     "Spotify",               9.99,  9.99),
            ("Nightlife / Bars",  "Friday drinks",        30.00, 65.00),
            ("Healthcare",        "Pharmacy",             12.00, 45.00),
            ("Food & Dining",     "Coffee shop",           4.50,  7.50),
            ("Shopping",          "Clothing store",        35.00, 80.00),
        ]

        income_items = [
            ("Salary / Income",   "Paycheck",           2200.00, 2800.00),
            ("Freelance",         "Side project",        200.00,  600.00),
        ]

        rng = random.Random(42)  # deterministic seed

        for ym in months:
            y, m = map(int, ym.split("-"))
            # Add 10-14 random expense transactions per month
            n_expenses = rng.randint(10, 14)
            for _ in range(n_expenses):
                cat, desc, lo, hi = rng.choice(expense_items)
                amount = round(rng.uniform(lo, hi), 2)
                day = rng.randint(1, 28)
                tx_date = f"{y:04d}-{m:02d}-{day:02d}"
                self.add_transaction(
                    amount=amount,
                    type_="expense",
                    category=cat,
                    description=desc,
                    trans_date=tx_date,
                    source="demo",
                )

            # Add 1-2 income transactions per month
            for inc_cat, inc_desc, inc_lo, inc_hi in income_items:
                if rng.random() < 0.85:  # 85% chance each income appears
                    amount = round(rng.uniform(inc_lo, inc_hi), 2)
                    day = 1 if "Paycheck" in inc_desc else rng.randint(5, 25)
                    tx_date = f"{y:04d}-{m:02d}-{day:02d}"
                    self.add_transaction(
                        amount=amount,
                        type_="income",
                        category=inc_cat,
                        description=inc_desc,
                        trans_date=tx_date,
                        source="demo",
                    )

        # Set budgets for current month
        current_ym = months[0]
        budget_limits = [
            ("Food & Dining",     200.00),
            ("Restaurants",       150.00),
            ("Transportation",    100.00),
            ("Rides (Uber/Lyft)",  50.00),
            ("Entertainment",      60.00),
            ("Shopping",          120.00),
            ("Nightlife / Bars",   80.00),
            ("ATM / Cash",        100.00),
            ("Subscriptions",      40.00),
        ]
        for cat, amt in budget_limits:
            self.set_budget(current_ym, cat, amt)

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
