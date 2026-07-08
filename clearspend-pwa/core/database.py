"""SQLite database — all schema + CRUD for ClearSpend PWA."""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, date


def _get_db_path() -> str:
    base = os.environ.get("CLEARSPEND_DATA_DIR", os.path.join(os.path.expanduser("~"), ".clearspend"))
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "clearspend.db")


class Database:
    _instance = None

    @classmethod
    def get(cls) -> "Database":
        if cls._instance is None:
            cls._instance = Database()
        return cls._instance

    @classmethod
    def reset(cls):
        """Drop singleton (for testing)."""
        cls._instance = None

    def __init__(self):
        path = _get_db_path()
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._create_tables()
        self._seed_categories()
        self._seed_classification_rules()

    # ------------------------------------------------------------------ schema
    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS transactions (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                amount              REAL    NOT NULL,
                type                TEXT    NOT NULL CHECK(type IN ('expense','income','transfer')),
                category            TEXT,
                description         TEXT,
                date                TEXT    NOT NULL,
                source              TEXT    DEFAULT 'manual',
                bank_account_id     INTEGER,
                plaid_transaction_id TEXT   DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS bank_accounts (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                bank_name             TEXT NOT NULL,
                account_name          TEXT,
                account_number_masked TEXT,
                access_token          TEXT,
                item_id               TEXT DEFAULT '',
                environment           TEXT DEFAULT 'sandbox',
                last_sync             TEXT
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

            CREATE TABLE IF NOT EXISTS goals (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL,
                target     REAL    NOT NULL,
                saved      REAL    NOT NULL DEFAULT 0,
                deadline   TEXT,
                category   TEXT    DEFAULT 'Other',
                completed  INTEGER NOT NULL DEFAULT 0,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS notifications_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                message    TEXT,
                created_at TEXT,
                read       INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS plaid_sync_cursors (
                bank_account_id INTEGER PRIMARY KEY,
                cursor TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (bank_account_id) REFERENCES bank_accounts(id)
            );

            CREATE TABLE IF NOT EXISTS events (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                name             TEXT NOT NULL,
                description      TEXT DEFAULT '',
                start_date       TEXT NOT NULL,
                end_date         TEXT NOT NULL,
                location_keyword TEXT DEFAULT '',
                color_index      INTEGER DEFAULT 0,
                created_at       TEXT
            );

            CREATE TABLE IF NOT EXISTS event_transactions (
                event_id       INTEGER NOT NULL,
                transaction_id INTEGER NOT NULL,
                PRIMARY KEY (event_id, transaction_id),
                FOREIGN KEY (event_id)       REFERENCES events(id)       ON DELETE CASCADE,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS classification_rules (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword  TEXT    NOT NULL COLLATE NOCASE,
                category TEXT    NOT NULL,
                type     TEXT    NOT NULL DEFAULT 'expense',
                source   TEXT    NOT NULL DEFAULT 'builtin',
                UNIQUE(keyword, source)
            );

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        self.conn.commit()

    # Built-in classification rules
    _BUILTIN_RULES = [
        ("e-transfer",          "Transfer",        "transfer"),
        ("interac",             "Transfer",        "transfer"),
        ("transfer to",         "Transfer",        "transfer"),
        ("transfer from",       "Transfer",        "income"),
        ("tfsa",                "Investment",      "transfer"),
        ("rrsp",                "Investment",      "transfer"),
        ("resp",                "Investment",      "transfer"),
        ("wealthsimple",        "Investment",      "transfer"),
        ("questrade",           "Investment",      "transfer"),
        ("fidelity",            "Investment",      "transfer"),
        ("robinhood",           "Investment",      "transfer"),
        ("rent",                "Rent / Housing",  "expense"),
        ("lease",               "Rent / Housing",  "expense"),
        ("mortgage",            "Rent / Housing",  "expense"),
        ("strata",              "Rent / Housing",  "expense"),
        ("payroll",             "Salary / Income", "income"),
        ("direct deposit",      "Salary / Income", "income"),
        ("salary",              "Salary / Income", "income"),
        ("paycheque",           "Salary / Income", "income"),
        ("paycheck",            "Salary / Income", "income"),
        ("netflix",             "Subscriptions",   "expense"),
        ("spotify",             "Subscriptions",   "expense"),
        ("apple.com/bill",      "Subscriptions",   "expense"),
        ("google play",         "Subscriptions",   "expense"),
        ("amazon prime",        "Subscriptions",   "expense"),
        ("disney+",             "Subscriptions",   "expense"),
        ("tim hortons",         "Food & Dining",   "expense"),
        ("starbucks",           "Food & Dining",   "expense"),
        ("mcdonalds",           "Food & Dining",   "expense"),
        ("uber eats",           "Food & Dining",   "expense"),
        ("doordash",            "Food & Dining",   "expense"),
        ("skip the dishes",     "Food & Dining",   "expense"),
        ("ttc",                 "Transportation",  "expense"),
        ("presto",              "Transportation",  "expense"),
        ("uber",                "Rides (Uber/Lyft)", "expense"),
        ("lyft",                "Rides (Uber/Lyft)", "expense"),
        ("bell canada",         "Utilities",       "expense"),
        ("rogers",              "Utilities",       "expense"),
        ("telus",               "Utilities",       "expense"),
        ("toronto hydro",       "Utilities",       "expense"),
        ("enbridge",            "Utilities",       "expense"),
        ("shoppers drug",       "Healthcare",      "expense"),
        ("goodlife",            "Healthcare",      "expense"),
        ("goodlife fitness",    "Healthcare",      "expense"),
        ("atm withdrawal",      "ATM / Cash",      "expense"),
        ("cash withdrawal",     "ATM / Cash",      "expense"),
    ]

    def _seed_classification_rules(self):
        self.conn.executemany(
            "INSERT OR IGNORE INTO classification_rules(keyword, category, type, source) VALUES(?,?,?,'builtin')",
            [(kw, cat, typ) for kw, cat, typ in self._BUILTIN_RULES],
        )
        self.conn.commit()

    def _seed_categories(self):
        defaults = [
            ("Food & Dining",      "utensils"),
            ("Transportation",     "car"),
            ("Entertainment",      "music"),
            ("Shopping",           "cart"),
            ("Utilities",          "zap"),
            ("Healthcare",         "heart"),
            ("ATM / Cash",         "banknote"),
            ("Restaurants",        "utensils"),
            ("Rides (Uber/Lyft)",  "car"),
            ("Nightlife / Bars",   "wine"),
            ("Subscriptions",      "repeat"),
            ("Salary / Income",    "briefcase"),
            ("Freelance",          "laptop"),
            ("Rent / Housing",     "home"),
            ("Investment",         "trending-up"),
            ("Transfer",           "arrow-right-left"),
            ("Travel",             "plane"),
            ("Other",              "circle"),
        ]
        self.conn.executemany(
            "INSERT OR IGNORE INTO categories(name, icon) VALUES (?, ?)", defaults
        )
        self.conn.commit()

    # --------------------------------------------------------- classification
    def classify_description(self, description: str) -> tuple[str, str] | None:
        if not description:
            return None
        desc_lower = description.lower()
        cur = self.conn.execute(
            """SELECT keyword, category, type FROM classification_rules
               ORDER BY CASE source WHEN 'user' THEN 0 ELSE 1 END, LENGTH(keyword) DESC"""
        )
        for row in cur.fetchall():
            keyword = (row[0] or "").lower()
            if keyword and keyword in desc_lower:
                return row[1], row[2]
        return None

    def save_user_rule(self, keyword: str, category: str, type_: str):
        self.conn.execute(
            """INSERT OR REPLACE INTO classification_rules(keyword, category, type, source)
               VALUES(?, ?, ?, 'user')""",
            (keyword.lower().strip(), category, type_),
        )
        self.conn.commit()

    def get_unclassified_transactions(self, bank_account_id: int | None = None) -> list[dict]:
        query = """SELECT * FROM transactions
                   WHERE (category IS NULL OR category = '' OR category = 'Other')
                   AND source != 'manual'"""
        params: list = []
        if bank_account_id is not None:
            query += " AND bank_account_id = ?"
            params.append(bank_account_id)
        query += " ORDER BY date DESC LIMIT 50"
        rows = self.conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def apply_classification_rules(self, bank_account_id: int | None = None) -> int:
        query = """SELECT id, description, category FROM transactions
                   WHERE source != 'manual'"""
        params: list = []
        if bank_account_id is not None:
            query += " AND bank_account_id = ?"
            params.append(bank_account_id)
        rows = self.conn.execute(query, params).fetchall()
        updated = 0
        for row in rows:
            result = self.classify_description(row[1] or "")
            if result:
                new_cat, new_type = result
                if new_cat != row[2]:
                    self.conn.execute(
                        "UPDATE transactions SET category=?, type=? WHERE id=?",
                        (new_cat, new_type, row[0]),
                    )
                    updated += 1
        if updated:
            self.conn.commit()
        return updated

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

    def update_transaction(self, transaction_id: int, amount: float, type_: str,
                           category: str, description: str, trans_date: str):
        self.conn.execute(
            """UPDATE transactions
               SET amount=?, type=?, category=?, description=?, date=?
               WHERE id=?""",
            (amount, type_, category, description, trans_date, transaction_id),
        )
        self.conn.commit()

    def delete_transaction(self, transaction_id: int):
        self.conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        self.conn.commit()

    def get_transaction(self, transaction_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM transactions WHERE id = ?", (transaction_id,)).fetchone()
        return dict(row) if row else None

    def get_transactions(self, year_month: str | None = None, type_: str | None = None,
                         category: str | None = None, search: str | None = None,
                         limit: int = 100, offset: int = 0) -> list[dict]:
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
        if search:
            query += " AND (description LIKE ? OR category LIKE ?)"
            params += [f"%{search}%", f"%{search}%"]
        query += " ORDER BY date DESC, id DESC LIMIT ? OFFSET ?"
        params += [limit, offset]
        cur = self.conn.execute(query, params)
        return [dict(r) for r in cur]

    def get_transaction_count(self, year_month: str | None = None) -> int:
        query = "SELECT COUNT(*) as c FROM transactions WHERE 1=1"
        params: list = []
        if year_month:
            query += " AND date LIKE ?"
            params.append(f"{year_month}%")
        return self.conn.execute(query, params).fetchone()["c"]

    def get_monthly_summary(self, year_month: str | None = None) -> dict:
        if year_month is None:
            year_month = datetime.now().strftime("%Y-%m")
        cur = self.conn.execute(
            "SELECT type, SUM(amount) as total FROM transactions "
            "WHERE date LIKE ? AND type IN ('income','expense') GROUP BY type",
            (f"{year_month}%",),
        )
        result: dict = {"month": year_month, "income": 0.0, "expense": 0.0}
        for row in cur:
            result[row["type"]] = round(row["total"] or 0.0, 2)
        result["balance"] = round(result["income"] - result["expense"], 2)
        return result

    def get_monthly_summaries(self, num_months: int = 6) -> list[dict]:
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
            s["label"] = date(y, m, 1).strftime("%b")
            results.append(s)
        return results

    def get_daily_spending(self, year_month: str) -> list[dict]:
        cur = self.conn.execute(
            """SELECT date, SUM(amount) as total
               FROM transactions
               WHERE type='expense' AND date LIKE ?
               GROUP BY date ORDER BY date""",
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
               GROUP BY category ORDER BY total DESC""",
            (f"{year_month}%",),
        )
        return [dict(r) for r in cur]

    # --------------------------------------------------------- categories
    def get_categories(self) -> list[dict]:
        cur = self.conn.execute("SELECT name, icon FROM categories ORDER BY name")
        return [dict(r) for r in cur]

    # --------------------------------------------------------- bank accounts
    def add_bank_account(self, bank_name: str, account_name: str,
                         account_number_masked: str, access_token: str = "",
                         item_id: str = "", environment: str = "sandbox") -> int:
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
        if not plaid_ids:
            return
        placeholders = ",".join("?" * len(plaid_ids))
        self.conn.execute(
            f"DELETE FROM transactions WHERE plaid_transaction_id IN ({placeholders})",
            plaid_ids,
        )
        self.conn.commit()

    # --------------------------------------------------------- budgets
    def set_budget(self, month: str, category: str, amount: float):
        self.conn.execute(
            "INSERT OR REPLACE INTO budgets(month, category, amount) VALUES (?, ?, ?)",
            (month, category, amount),
        )
        self.conn.commit()

    def delete_budget(self, month: str, category: str):
        self.conn.execute(
            "DELETE FROM budgets WHERE month = ? AND category = ?",
            (month, category),
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
        now = datetime.now()
        days_in_month = 30
        days_elapsed = min(now.day, days_in_month)
        result = []
        for cat, budget_amt in budgets.items():
            spent = breakdown.get(cat, 0.0)
            pct = min(spent / budget_amt, 1.0) if budget_amt > 0 else 0.0
            forecast = (spent / days_elapsed * days_in_month) if days_elapsed > 0 else 0.0
            result.append({
                "category": cat,
                "budget": budget_amt,
                "spent": round(spent, 2),
                "remaining": round(budget_amt - spent, 2),
                "pct": round(pct, 3),
                "forecast": round(forecast, 2),
            })
        return result

    def copy_budgets(self, from_month: str, to_month: str) -> int:
        existing = self.get_budgets(to_month)
        if existing:
            return 0
        prev = self.get_budgets(from_month)
        for b in prev:
            self.set_budget(to_month, b["category"], b["amount"])
        return len(prev)

    # --------------------------------------------------------- trends
    def get_recurring_transactions(self) -> list[dict]:
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

    # --------------------------------------------------------- goals
    def add_goal(self, name: str, target: float, saved: float = 0.0,
                 deadline: str | None = None, category: str = "Other") -> int:
        cur = self.conn.execute(
            """INSERT INTO goals(name, target, saved, deadline, category, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, target, saved, deadline, category, datetime.now().isoformat()),
        )
        self.conn.commit()
        return cur.lastrowid

    def get_goals(self) -> list[dict]:
        cur = self.conn.execute(
            "SELECT * FROM goals ORDER BY completed ASC, created_at DESC"
        )
        return [dict(r) for r in cur]

    def get_goal(self, goal_id: int) -> dict | None:
        row = self.conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,)).fetchone()
        return dict(row) if row else None

    def deposit_goal(self, goal_id: int, amount: float) -> dict | None:
        cur = self.conn.execute("SELECT * FROM goals WHERE id = ?", (goal_id,))
        row = cur.fetchone()
        if not row:
            return None
        new_saved = row["saved"] + amount
        completed = 1 if new_saved >= row["target"] else 0
        self.conn.execute(
            "UPDATE goals SET saved = ?, completed = ? WHERE id = ?",
            (new_saved, completed, goal_id),
        )
        self.conn.commit()
        return dict(row) | {"saved": new_saved, "completed": completed}

    def delete_goal(self, goal_id: int):
        self.conn.execute("DELETE FROM goals WHERE id = ?", (goal_id,))
        self.conn.commit()

    # --------------------------------------------------------- events
    EVENT_COLORS = ["#3399ff", "#33cc73", "#ff8c1a", "#d93370", "#8c4de6", "#1abfbf"]

    def create_event(self, name: str, description: str, start_date: str,
                     end_date: str, location_keyword: str = "",
                     color_index: int = 0) -> int:
        cur = self.conn.execute(
            """INSERT INTO events(name, description, start_date, end_date,
               location_keyword, color_index, created_at)
               VALUES(?,?,?,?,?,?,?)""",
            (name, description, start_date, end_date,
             location_keyword.lower().strip(), color_index,
             datetime.now().isoformat()),
        )
        self.conn.commit()
        event_id = cur.lastrowid
        if location_keyword:
            self._auto_assign_event(event_id, start_date, end_date, location_keyword)
        return event_id

    def _auto_assign_event(self, event_id: int, start_date: str,
                           end_date: str, keyword: str):
        kw = keyword.lower().strip()
        rows = self.conn.execute(
            "SELECT id, description FROM transactions WHERE date BETWEEN ? AND ?",
            (start_date, end_date),
        ).fetchall()
        for row in rows:
            if kw in (row[1] or "").lower():
                self.conn.execute(
                    "INSERT OR IGNORE INTO event_transactions VALUES(?,?)",
                    (event_id, row[0]),
                )
        self.conn.commit()

    def get_events(self) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM events ORDER BY start_date DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_event(self, event_id: int) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM events WHERE id=?", (event_id,)
        ).fetchone()
        return dict(row) if row else None

    def delete_event(self, event_id: int):
        self.conn.execute("DELETE FROM event_transactions WHERE event_id=?", (event_id,))
        self.conn.execute("DELETE FROM events WHERE id=?", (event_id,))
        self.conn.commit()

    def get_event_transactions(self, event_id: int) -> list[dict]:
        rows = self.conn.execute(
            """SELECT t.* FROM transactions t
               JOIN event_transactions et ON et.transaction_id = t.id
               WHERE et.event_id = ?
               ORDER BY t.date DESC""",
            (event_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_event_summary(self, event_id: int) -> dict:
        rows = self.get_event_transactions(event_id)
        total = sum(r["amount"] for r in rows if r["type"] == "expense")
        income = sum(r["amount"] for r in rows if r["type"] == "income")
        by_cat: dict[str, float] = {}
        for r in rows:
            if r["type"] == "expense":
                by_cat[r["category"] or "Other"] = by_cat.get(r["category"] or "Other", 0) + r["amount"]
        return {"total": round(total, 2), "income": round(income, 2),
                "count": len(rows), "by_category": by_cat}

    def add_transaction_to_event(self, event_id: int, transaction_id: int):
        self.conn.execute(
            "INSERT OR IGNORE INTO event_transactions VALUES(?,?)",
            (event_id, transaction_id),
        )
        self.conn.commit()

    def remove_transaction_from_event(self, event_id: int, transaction_id: int):
        self.conn.execute(
            "DELETE FROM event_transactions WHERE event_id=? AND transaction_id=?",
            (event_id, transaction_id),
        )
        self.conn.commit()

    # --------------------------------------------------------- settings (key-value)
    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str):
        self.conn.execute(
            "INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)",
            (key, value),
        )
        self.conn.commit()

    # --------------------------------------------------------- export / backup
    def export_to_dict(self) -> dict:
        return {
            "transactions": self.get_transactions(limit=100000),
            "bank_accounts": self.get_bank_accounts(),
            "budgets": [dict(r) for r in self.conn.execute("SELECT * FROM budgets").fetchall()],
            "goals": self.get_goals(),
            "events": self.get_events(),
            "exported_at": datetime.now().isoformat(),
            "schema_version": 2,
        }

    def import_from_dict(self, data: dict):
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

    # --------------------------------------------------------- demo data
    def seed_demo_data(self):
        import random
        now = datetime.now()
        year = now.year
        month = now.month

        months = []
        for offset in range(3):
            m = month - offset
            y = year
            while m <= 0:
                m += 12
                y -= 1
            months.append(f"{y:04d}-{m:02d}")

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

        rng = random.Random(42)
        for ym in months:
            y, m = map(int, ym.split("-"))
            n_expenses = rng.randint(10, 14)
            for _ in range(n_expenses):
                cat, desc, lo, hi = rng.choice(expense_items)
                amount = round(rng.uniform(lo, hi), 2)
                day = rng.randint(1, 28)
                tx_date = f"{y:04d}-{m:02d}-{day:02d}"
                self.add_transaction(amount=amount, type_="expense", category=cat,
                                     description=desc, trans_date=tx_date, source="demo")
            for inc_cat, inc_desc, inc_lo, inc_hi in income_items:
                if rng.random() < 0.85:
                    amount = round(rng.uniform(inc_lo, inc_hi), 2)
                    day = 1 if "Paycheck" in inc_desc else rng.randint(5, 25)
                    tx_date = f"{y:04d}-{m:02d}-{day:02d}"
                    self.add_transaction(amount=amount, type_="income", category=inc_cat,
                                         description=inc_desc, trans_date=tx_date, source="demo")

        current_ym = months[0]
        budget_limits = [
            ("Food & Dining", 200.00), ("Restaurants", 150.00),
            ("Transportation", 100.00), ("Rides (Uber/Lyft)", 50.00),
            ("Entertainment", 60.00), ("Shopping", 120.00),
            ("Nightlife / Bars", 80.00), ("ATM / Cash", 100.00),
            ("Subscriptions", 40.00),
        ]
        for cat, amt in budget_limits:
            self.set_budget(current_ym, cat, amt)
