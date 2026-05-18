"""ClearSpend Plaid proxy server.

Keeps Plaid credentials server-side and handles the HTTPS redirect
that Plaid requires (bouncing to clearspend:// deep link).

Environment variables:
    PLAID_CLIENT_ID      -- Plaid client ID
    PLAID_SECRET         -- Plaid secret
    PLAID_ENV            -- sandbox | development | production
    CLEARSPEND_API_KEY   -- shared secret the app sends in X-API-Key header
    PUBLIC_URL           -- public HTTPS URL of this server (e.g. https://supersecretnas.tailc3a431.ts.net)
"""

import json
import os
import secrets
import time
from functools import wraps
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import Flask, abort, jsonify, redirect, request

app = Flask(__name__)

PLAID_ENVS = {
    "sandbox": "https://sandbox.plaid.com",
    "development": "https://development.plaid.com",
    "production": "https://production.plaid.com",
}

DEEP_LINK = "clearspend://plaid-callback"

# In-memory store: session_id -> {link_token, created_at}
# Entries expire after 10 minutes
_sessions = {}
SESSION_TTL = 600


def _cfg():
    return {
        "client_id": os.environ.get("PLAID_CLIENT_ID", ""),
        "secret": os.environ.get("PLAID_SECRET", ""),
        "env": os.environ.get("PLAID_ENV", "sandbox"),
    }


def _plaid_post(endpoint, payload):
    cfg = _cfg()
    base = PLAID_ENVS.get(cfg["env"], PLAID_ENVS["sandbox"])
    body = json.dumps(payload).encode()
    req = Request(f"{base}{endpoint}", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=20) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        try:
            err = json.loads(e.read())
        except Exception:
            err = {"error_message": str(e)}
        abort(502, description=err.get("error_message", str(e)))


def _auth():
    return {"client_id": _cfg()["client_id"], "secret": _cfg()["secret"]}


def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        expected = os.environ.get("CLEARSPEND_API_KEY", "")
        if expected and request.headers.get("X-API-Key") != expected:
            abort(401)
        return f(*args, **kwargs)
    return decorated


def _cleanup_sessions():
    now = time.time()
    expired = [k for k, v in _sessions.items() if now - v["created_at"] > SESSION_TTL]
    for k in expired:
        del _sessions[k]


PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")


@app.get("/")
def health():
    return jsonify(status="ok")


@app.post("/api/link-token")
@require_api_key
def link_token():
    _cleanup_sessions()
    server_url = PUBLIC_URL or request.host_url.rstrip("/")

    # Create a session ID to track this link attempt
    session_id = secrets.token_urlsafe(16)
    redirect_uri = f"{server_url}/plaid-callback/{session_id}"

    payload = {
        **_auth(),
        "user": {"client_user_id": "clearspend_user"},
        "client_name": "ClearSpend",
        "products": ["transactions"],
        "country_codes": ["US", "CA"],
        "language": "en",
        "redirect_uri": redirect_uri,
        "hosted_link": {
            "completion_redirect_uri": redirect_uri,
            "is_mobile_app": True,
        },
    }
    resp = _plaid_post("/link/token/create", payload)
    link_token_val = resp.get("link_token", "")
    url = resp.get("hosted_link_url", "")
    if not url:
        abort(502, description="No hosted_link_url in Plaid response")

    # Store the link_token for retrieval after callback
    _sessions[session_id] = {
        "link_token": link_token_val,
        "created_at": time.time(),
        "public_token": None,
    }

    return jsonify(url=url, session_id=session_id)


@app.get("/plaid-callback/<session_id>")
def plaid_callback(session_id):
    all_params = dict(request.args)
    app.logger.info(f"plaid-callback session={session_id} params={all_params}")

    # Mark session as completed so the app can poll for it
    if session_id in _sessions:
        _sessions[session_id]["completed"] = True
        _sessions[session_id]["callback_params"] = all_params

    # Redirect back to app
    params = urlencode({"session_id": session_id})
    target = f"{DEEP_LINK}?{params}"
    return redirect(target, code=302)


@app.post("/api/complete-link")
@require_api_key
def complete_link():
    """Called by app after receiving the deep link callback.
    Retrieves the link_token for this session and exchanges it for an access_token."""
    data = request.get_json(force=True)
    session_id = data.get("session_id", "")
    if not session_id or session_id not in _sessions:
        abort(400, description="Invalid or expired session_id")

    session = _sessions[session_id]
    link_token_val = session.get("link_token", "")
    if not link_token_val:
        abort(400, description="No link_token for this session")

    # Get the public_token from Plaid using the link_token
    resp = _plaid_post("/link/token/get", {
        **_auth(),
        "link_token": link_token_val,
    })

    public_token = resp.get("metadata", {}).get("public_token", "")
    if not public_token:
        # Try direct field
        public_token = resp.get("public_token", "")

    app.logger.info(f"complete-link session={session_id} link_token_get keys={list(resp.keys())}")

    if not public_token:
        # Return the raw response so the app can log it
        abort(502, description=f"No public_token in response. Keys: {list(resp.keys())}")

    # Exchange public_token for access_token
    exchange = _plaid_post("/item/public_token/exchange", {
        **_auth(), "public_token": public_token,
    })
    access_token = exchange.get("access_token", "")
    item_id = exchange.get("item_id", "")

    accounts_resp = _plaid_post("/accounts/get", {
        **_auth(), "access_token": access_token,
    })
    accounts = []
    for a in accounts_resp.get("accounts", []):
        accounts.append({
            "name": a.get("name", "Account"),
            "number": a.get("mask", "****"),
            "type": a.get("type", ""),
            "subtype": a.get("subtype", ""),
        })

    del _sessions[session_id]

    return jsonify(
        success=True,
        access_token=access_token,
        item_id=item_id,
        accounts=accounts,
    )


@app.post("/api/exchange-token")
@require_api_key
def exchange_token():
    data = request.get_json(force=True)
    public_token = data.get("public_token", "")
    if not public_token:
        abort(400, description="public_token required")

    exchange = _plaid_post("/item/public_token/exchange", {
        **_auth(), "public_token": public_token,
    })
    access_token = exchange.get("access_token", "")
    item_id = exchange.get("item_id", "")

    accounts_resp = _plaid_post("/accounts/get", {
        **_auth(), "access_token": access_token,
    })
    accounts = []
    for a in accounts_resp.get("accounts", []):
        accounts.append({
            "name": a.get("name", "Account"),
            "number": a.get("mask", "****"),
            "type": a.get("type", ""),
            "subtype": a.get("subtype", ""),
        })

    return jsonify(
        success=True,
        access_token=access_token,
        item_id=item_id,
        accounts=accounts,
    )


@app.post("/api/transactions-sync")
@require_api_key
def transactions_sync():
    data = request.get_json(force=True)
    access_token = data.get("access_token", "")
    cursor = data.get("cursor", "")
    if not access_token:
        abort(400, description="access_token required")

    all_added, all_removed = [], []
    current_cursor = cursor
    has_more = True

    while has_more:
        payload = {**_auth(), "access_token": access_token}
        if current_cursor:
            payload["cursor"] = current_cursor
        resp = _plaid_post("/transactions/sync", payload)

        for t in resp.get("added", []):
            cat = t.get("personal_finance_category", {})
            all_added.append({
                "amount": abs(t.get("amount", 0)),
                "type": "expense" if t.get("amount", 0) > 0 else "income",
                "category": cat.get("primary", "Other") if cat else "Other",
                "description": t.get("name", ""),
                "date": t.get("date", ""),
                "plaid_transaction_id": t.get("transaction_id", ""),
            })

        for t in resp.get("removed", []):
            tid = t.get("transaction_id", "")
            if tid:
                all_removed.append(tid)

        current_cursor = resp.get("next_cursor", current_cursor)
        has_more = resp.get("has_more", False)

    return jsonify(
        added=all_added,
        removed=all_removed,
        cursor=current_cursor,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8008, debug=True)
