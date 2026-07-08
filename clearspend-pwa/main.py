"""ClearSpend PWA — FastAPI backend."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from core.database import Database
from core.classifier import auto_classify, classify_keyword, CATEGORIES
from core.tips import generate_tips
from core.bank_api import get_bank_api, ScotiabankAPI
from core.cloud_sync import CloudSync

_BASE = Path(__file__).resolve().parent
_STATIC = _BASE / "static"

app = FastAPI()

_cloud_sync = CloudSync()


def _db() -> Database:
    return Database.get()


# ------------------------------------------------------------------ static
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


@app.get("/")
async def index():
    return FileResponse(str(_STATIC / "index.html"))


@app.get("/manifest.json")
async def manifest():
    return FileResponse(
        str(_STATIC / "manifest.json"),
        media_type="application/manifest+json",
    )


@app.get("/sw.js")
async def service_worker():
    return FileResponse(
        str(_STATIC / "sw.js"),
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )


# ------------------------------------------------------------------ health
@app.get("/api/health")
async def health():
    return {"status": "ok", "app": "clearspend"}


# ------------------------------------------------------------------ dashboard
@app.get("/api/dashboard")
async def dashboard():
    db = _db()
    now = datetime.now()
    ym = now.strftime("%Y-%m")
    summary = db.get_monthly_summary(ym)
    trend = db.get_monthly_summaries(6)
    breakdown = db.get_category_breakdown(ym)
    recent = db.get_transactions(year_month=ym, limit=5)
    tips = generate_tips(db)

    # Previous month comparison
    pm = now.month - 1
    py = now.year
    if pm <= 0:
        pm = 12
        py -= 1
    prev = db.get_monthly_summary(f"{py:04d}-{pm:02d}")
    delta_pct = 0.0
    if prev["expense"] > 0:
        delta_pct = round((summary["expense"] - prev["expense"]) / prev["expense"] * 100, 1)

    return {
        "month": ym,
        "month_label": now.strftime("%B %Y"),
        "summary": summary,
        "prev_summary": prev,
        "delta_pct": delta_pct,
        "trend": trend,
        "breakdown": breakdown,
        "recent": recent,
        "tips": tips,
    }


# ------------------------------------------------------------------ transactions
@app.get("/api/transactions")
async def get_transactions(month: str | None = None, type: str | None = None,
                           category: str | None = None, search: str | None = None,
                           limit: int = 50, offset: int = 0):
    db = _db()
    txns = db.get_transactions(year_month=month, type_=type, category=category,
                               search=search, limit=limit, offset=offset)
    count = db.get_transaction_count(year_month=month)
    return {"transactions": txns, "total": count}


@app.get("/api/transactions/{txn_id}")
async def get_transaction(txn_id: int):
    db = _db()
    txn = db.get_transaction(txn_id)
    if not txn:
        raise HTTPException(404, "Transaction not found")
    return txn


@app.post("/api/transactions")
async def add_transaction(req: Request):
    data = await req.json()
    db = _db()
    amount = float(data.get("amount", 0))
    if amount <= 0:
        raise HTTPException(400, "Amount must be positive")
    type_ = data.get("type", "expense")
    if type_ not in ("expense", "income", "transfer"):
        raise HTTPException(400, "Invalid type")
    category = data.get("category", "")
    description = data.get("description", "")

    # Auto-classify if no category
    if not category or category == "Other":
        api_key = db.get_setting("gemini_api_key")
        category = auto_classify(description, api_key=api_key)

    trans_date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    txn_id = db.add_transaction(
        amount=amount, type_=type_, category=category,
        description=description, trans_date=trans_date,
    )
    return {"id": txn_id, "category": category}


@app.put("/api/transactions/{txn_id}")
async def update_transaction(txn_id: int, req: Request):
    data = await req.json()
    db = _db()
    txn = db.get_transaction(txn_id)
    if not txn:
        raise HTTPException(404, "Transaction not found")
    db.update_transaction(
        txn_id,
        amount=float(data.get("amount", txn["amount"])),
        type_=data.get("type", txn["type"]),
        category=data.get("category", txn["category"]),
        description=data.get("description", txn["description"]),
        trans_date=data.get("date", txn["date"]),
    )
    return {"ok": True}


@app.delete("/api/transactions/{txn_id}")
async def delete_transaction(txn_id: int):
    _db().delete_transaction(txn_id)
    return {"ok": True}


@app.post("/api/transactions/classify")
async def classify_transaction(req: Request):
    data = await req.json()
    description = data.get("description", "")
    api_key = _db().get_setting("gemini_api_key")
    category = auto_classify(description, api_key=api_key)
    return {"category": category}


# ------------------------------------------------------------------ categories
@app.get("/api/categories")
async def get_categories():
    return {"categories": _db().get_categories()}


# ------------------------------------------------------------------ budgets
@app.get("/api/budgets")
async def get_budgets(month: str | None = None):
    db = _db()
    if month is None:
        month = datetime.now().strftime("%Y-%m")
    budgets = db.get_budgets(month)
    status = db.get_budget_status(month)
    return {"month": month, "budgets": budgets, "status": status}


@app.post("/api/budgets")
async def set_budget(req: Request):
    data = await req.json()
    db = _db()
    month = data.get("month", datetime.now().strftime("%Y-%m"))
    category = data.get("category", "")
    amount = float(data.get("amount", 0))
    if not category:
        raise HTTPException(400, "Category required")
    if amount <= 0:
        raise HTTPException(400, "Amount must be positive")
    db.set_budget(month, category, amount)
    return {"ok": True}


@app.delete("/api/budgets")
async def delete_budget(req: Request):
    data = await req.json()
    db = _db()
    month = data.get("month", datetime.now().strftime("%Y-%m"))
    category = data.get("category", "")
    if not category:
        raise HTTPException(400, "Category required")
    db.delete_budget(month, category)
    return {"ok": True}


@app.post("/api/budgets/copy")
async def copy_budgets(req: Request):
    data = await req.json()
    db = _db()
    from_month = data.get("from_month", "")
    to_month = data.get("to_month", "")
    if not from_month or not to_month:
        raise HTTPException(400, "from_month and to_month required")
    count = db.copy_budgets(from_month, to_month)
    return {"copied": count}


# ------------------------------------------------------------------ goals
@app.get("/api/goals")
async def get_goals():
    return {"goals": _db().get_goals()}


@app.post("/api/goals")
async def add_goal(req: Request):
    data = await req.json()
    db = _db()
    name = data.get("name", "").strip()
    target = float(data.get("target", 0))
    if not name:
        raise HTTPException(400, "Name required")
    if target <= 0:
        raise HTTPException(400, "Target must be positive")
    goal_id = db.add_goal(
        name=name, target=target,
        saved=float(data.get("saved", 0)),
        deadline=data.get("deadline"),
        category=data.get("category", "Other"),
    )
    return {"id": goal_id}


@app.post("/api/goals/{goal_id}/deposit")
async def deposit_goal(goal_id: int, req: Request):
    data = await req.json()
    amount = float(data.get("amount", 0))
    if amount <= 0:
        raise HTTPException(400, "Amount must be positive")
    result = _db().deposit_goal(goal_id, amount)
    if not result:
        raise HTTPException(404, "Goal not found")
    return result


@app.delete("/api/goals/{goal_id}")
async def delete_goal(goal_id: int):
    _db().delete_goal(goal_id)
    return {"ok": True}


# ------------------------------------------------------------------ trends
@app.get("/api/trends")
async def get_trends(month: str | None = None):
    db = _db()
    if month is None:
        month = datetime.now().strftime("%Y-%m")
    breakdown = db.get_category_breakdown(month)
    recurring = db.get_recurring_transactions()
    total = sum(r["total"] for r in breakdown)
    for r in breakdown:
        r["pct"] = round(r["total"] / total * 100, 1) if total > 0 else 0
    return {"month": month, "breakdown": breakdown, "total": round(total, 2),
            "recurring": recurring}


# ------------------------------------------------------------------ events
@app.get("/api/events")
async def get_events():
    db = _db()
    events = db.get_events()
    for e in events:
        e["summary"] = db.get_event_summary(e["id"])
    return {"events": events}


@app.post("/api/events")
async def create_event(req: Request):
    data = await req.json()
    db = _db()
    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(400, "Name required")
    event_id = db.create_event(
        name=name,
        description=data.get("description", ""),
        start_date=data.get("start_date", datetime.now().strftime("%Y-%m-%d")),
        end_date=data.get("end_date", datetime.now().strftime("%Y-%m-%d")),
        location_keyword=data.get("location_keyword", ""),
        color_index=int(data.get("color_index", 0)),
    )
    return {"id": event_id}


@app.get("/api/events/{event_id}")
async def get_event(event_id: int):
    db = _db()
    event = db.get_event(event_id)
    if not event:
        raise HTTPException(404, "Event not found")
    event["transactions"] = db.get_event_transactions(event_id)
    event["summary"] = db.get_event_summary(event_id)
    return event


@app.delete("/api/events/{event_id}")
async def delete_event(event_id: int):
    _db().delete_event(event_id)
    return {"ok": True}


@app.post("/api/events/{event_id}/transactions")
async def add_txn_to_event(event_id: int, req: Request):
    data = await req.json()
    txn_id = int(data.get("transaction_id", 0))
    if not txn_id:
        raise HTTPException(400, "transaction_id required")
    _db().add_transaction_to_event(event_id, txn_id)
    return {"ok": True}


@app.delete("/api/events/{event_id}/transactions/{txn_id}")
async def remove_txn_from_event(event_id: int, txn_id: int):
    _db().remove_transaction_from_event(event_id, txn_id)
    return {"ok": True}


# ------------------------------------------------------------------ bank connect
@app.get("/api/bank/accounts")
async def get_bank_accounts():
    return {"accounts": _db().get_bank_accounts()}


@app.post("/api/bank/connect/mock")
async def mock_bank_connect(req: Request):
    """Connect via mock Scotiabank API."""
    data = await req.json()
    bank_api = ScotiabankAPI()
    result = bank_api.connect(username=data.get("username", ""), password=data.get("password", ""))
    if not result.get("success"):
        raise HTTPException(400, result.get("error", "Connection failed"))

    db = _db()
    accounts = result["accounts"]
    txns = bank_api.get_transactions()

    # Check for existing mock bank accounts to avoid duplicates
    existing = db.get_bank_accounts()
    existing_names = {(a["bank_name"], a["account_number_masked"]) for a in existing}

    new_count = 0
    for acc in accounts:
        key = ("Scotiabank (Mock)", acc["number"])
        if key in existing_names:
            continue
        acc_id = db.add_bank_account(
            bank_name="Scotiabank (Mock)", account_name=acc["name"],
            account_number_masked=acc["number"],
        )
        for t in txns:
            db.add_transaction(
                amount=t["amount"], type_=t["type"], category=t["category"],
                description=t["description"], trans_date=t["date"],
                source="scotiabank", bank_account_id=acc_id,
            )
        new_count += 1

    db.apply_classification_rules()
    if new_count == 0:
        return {"success": True, "accounts": 0, "transactions": 0,
                "message": "Bank already connected — use Sync to pull new transactions"}
    return {"success": True, "accounts": new_count, "transactions": len(txns)}


@app.post("/api/bank/connect/plaid/link")
async def plaid_link():
    """Create Plaid hosted link token."""
    db = _db()
    server_url = db.get_setting("plaid_server_url")
    api_key = db.get_setting("plaid_api_key")
    if not server_url:
        raise HTTPException(400, "Plaid server URL not configured")
    api = get_bank_api("plaid", server_url=server_url, api_key=api_key)
    result = api.create_link_token()
    return result


@app.post("/api/bank/connect/plaid/complete")
async def plaid_complete(req: Request):
    """Complete Plaid link — exchange session for access token."""
    data = await req.json()
    session_id = data.get("session_id", "")
    if not session_id:
        raise HTTPException(400, "session_id required")
    db = _db()
    server_url = db.get_setting("plaid_server_url")
    api_key = db.get_setting("plaid_api_key")
    api = get_bank_api("plaid", server_url=server_url, api_key=api_key)
    result = api.complete_link(session_id)
    if not result.get("success"):
        raise HTTPException(502, result.get("error", "Link completion failed"))

    # Save bank account — dedup by item_id to avoid duplicates
    item_id = result.get("item_id", "")
    access_token = result.get("access_token", "")
    plaid_env = db.get_setting("plaid_env", "sandbox")
    accounts = result.get("accounts", [])

    existing = db.get_bank_accounts()
    existing_items = {a["item_id"] for a in existing if a.get("item_id")}

    if item_id and item_id in existing_items:
        # Update access token on existing accounts for this item
        for a in existing:
            if a.get("item_id") == item_id:
                db.conn.execute(
                    "UPDATE bank_accounts SET access_token=?, last_sync=? WHERE id=?",
                    (access_token, datetime.now().isoformat(), a["id"]),
                )
        db.conn.commit()
        return {"success": True, "accounts": 0,
                "message": "Bank already connected — access token refreshed"}

    new_count = 0
    for acc in accounts:
        db.add_bank_account(
            bank_name="Plaid", account_name=acc.get("name", "Account"),
            account_number_masked=acc.get("number", "****"),
            access_token=access_token,
            item_id=item_id,
            environment=plaid_env,
        )
        new_count += 1
    return {"success": True, "accounts": new_count}


@app.post("/api/bank/sync/{account_id}")
async def sync_bank(account_id: int):
    """Sync transactions for a bank account."""
    db = _db()
    accounts = db.get_bank_accounts()
    account = next((a for a in accounts if a["id"] == account_id), None)
    if not account:
        raise HTTPException(404, "Account not found")
    if not account.get("access_token"):
        raise HTTPException(400, "No access token for this account")

    server_url = db.get_setting("plaid_server_url")
    api_key = db.get_setting("plaid_api_key")
    api = get_bank_api("plaid", server_url=server_url, api_key=api_key)

    cursor = db.get_plaid_cursor(account_id)
    result = api.get_transactions(access_token=account["access_token"], cursor=cursor)

    added_count = 0
    for t in result.get("added", []):
        db.add_transaction(
            amount=t["amount"], type_=t["type"], category=t.get("category", "Other"),
            description=t.get("description", ""), trans_date=t.get("date", ""),
            source="plaid", bank_account_id=account_id,
            plaid_transaction_id=t.get("plaid_transaction_id", ""),
        )
        added_count += 1

    removed = result.get("removed", [])
    if removed:
        db.delete_transactions_by_plaid_id(removed)

    new_cursor = result.get("cursor", cursor)
    if new_cursor:
        db.set_plaid_cursor(account_id, new_cursor)

    db.update_bank_sync_time(account_id)
    db.apply_classification_rules(account_id)

    return {"added": added_count, "removed": len(removed)}


@app.delete("/api/bank/accounts/{account_id}")
async def delete_bank_account(account_id: int):
    """Remove a bank account and its synced transactions."""
    db = _db()
    db.conn.execute("DELETE FROM plaid_sync_cursors WHERE bank_account_id = ?", (account_id,))
    db.conn.execute("DELETE FROM transactions WHERE bank_account_id = ?", (account_id,))
    db.conn.execute("DELETE FROM bank_accounts WHERE id = ?", (account_id,))
    db.conn.commit()
    return {"ok": True}


# ------------------------------------------------------------------ classification
@app.get("/api/classify/unclassified")
async def get_unclassified():
    return {"transactions": _db().get_unclassified_transactions()}


@app.post("/api/classify/rule")
async def save_classification_rule(req: Request):
    data = await req.json()
    keyword = data.get("keyword", "").strip()
    category = data.get("category", "")
    type_ = data.get("type", "expense")
    if not keyword or not category:
        raise HTTPException(400, "keyword and category required")
    _db().save_user_rule(keyword, category, type_)
    return {"ok": True}


@app.post("/api/classify/apply")
async def apply_rules():
    count = _db().apply_classification_rules()
    return {"updated": count}


# ------------------------------------------------------------------ settings
@app.get("/api/settings")
async def get_settings():
    db = _db()
    return {
        "gemini_api_key": "***" if db.get_setting("gemini_api_key") else "",
        "plaid_server_url": db.get_setting("plaid_server_url"),
        "plaid_api_key": "***" if db.get_setting("plaid_api_key") else "",
        "plaid_env": db.get_setting("plaid_env", "sandbox"),
        "cloud_api_key": "***" if db.get_setting("cloud_api_key") else "",
        "cloud_bin_id": db.get_setting("cloud_bin_id"),
        "pin_hash": "set" if db.get_setting("pin_hash") else "",
        "dark_mode": db.get_setting("dark_mode", "0"),
    }


@app.post("/api/settings")
async def save_settings(req: Request):
    data = await req.json()
    db = _db()
    allowed = ["gemini_api_key", "plaid_server_url", "plaid_api_key",
               "plaid_env", "cloud_api_key", "cloud_bin_id", "pin_hash",
               "dark_mode"]
    for key in allowed:
        if key in data:
            db.set_setting(key, data[key])
    return {"ok": True}


# ------------------------------------------------------------------ cloud sync
@app.post("/api/cloud/backup")
async def cloud_backup():
    db = _db()
    api_key = db.get_setting("cloud_api_key")
    bin_id = db.get_setting("cloud_bin_id")
    if not api_key:
        raise HTTPException(400, "Cloud API key not configured")
    _cloud_sync.set_credentials(api_key, bin_id)
    result = _cloud_sync.backup(db.export_to_dict())
    if result.get("success") and result.get("bin_id"):
        db.set_setting("cloud_bin_id", result["bin_id"])
    return result


@app.post("/api/cloud/restore")
async def cloud_restore():
    db = _db()
    api_key = db.get_setting("cloud_api_key")
    bin_id = db.get_setting("cloud_bin_id")
    if not api_key or not bin_id:
        raise HTTPException(400, "Cloud credentials not configured")
    _cloud_sync.set_credentials(api_key, bin_id)
    result = _cloud_sync.restore()
    if result.get("success"):
        db.import_from_dict(result["data"])
    return result


# ------------------------------------------------------------------ data management
@app.post("/api/data/demo")
async def seed_demo():
    _db().seed_demo_data()
    return {"ok": True}


@app.get("/api/data/export")
async def export_data():
    return _db().export_to_dict()


@app.post("/api/data/import")
async def import_data(req: Request):
    data = await req.json()
    _db().import_from_dict(data)
    return {"ok": True}


@app.post("/api/data/clear")
async def clear_data(req: Request):
    data = await req.json()
    db = _db()
    pin = db.get_setting("pin_hash")
    if pin and data.get("pin_hash") != pin:
        raise HTTPException(403, "Invalid PIN")
    # Drop and recreate
    db.conn.executescript("""
        DELETE FROM event_transactions;
        DELETE FROM events;
        DELETE FROM transactions;
        DELETE FROM bank_accounts;
        DELETE FROM budgets;
        DELETE FROM goals;
        DELETE FROM plaid_sync_cursors;
        DELETE FROM notifications_log;
        DELETE FROM classification_rules WHERE source = 'user';
    """)
    db.conn.commit()
    return {"ok": True}


# ------------------------------------------------------------------ months list
@app.get("/api/months")
async def get_months():
    """Return list of months that have transactions."""
    db = _db()
    rows = db.conn.execute(
        """SELECT DISTINCT strftime('%Y-%m', date) as month
           FROM transactions ORDER BY month DESC"""
    ).fetchall()
    return {"months": [r["month"] for r in rows]}
