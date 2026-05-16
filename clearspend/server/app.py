"""ClearSpend Plaid proxy server.

Keeps Plaid credentials server-side and handles the HTTPS redirect
that Plaid requires (bouncing to clearspend:// deep link).

Environment variables:
    PLAID_CLIENT_ID      -- Plaid client ID
    PLAID_SECRET         -- Plaid secret
    PLAID_ENV            -- sandbox | development | production
    CLEARSPEND_API_KEY   -- shared secret the app sends in X-API-Key header
"""

import json
import os
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


@app.get("/")
def health():
    return jsonify(status="ok")


@app.post("/api/link-token")
@require_api_key
def link_token():
    server_url = request.host_url.rstrip("/")
    redirect_uri = f"{server_url}/plaid-callback"
    payload = {
        **_auth(),
        "user": {"client_user_id": "clearspend_user"},
        "client_name": "ClearSpend",
        "products": ["transactions"],
        "country_codes": ["US", "CA"],
        "language": "en",
        "hosted_link": {
            "completion_redirect_uri": redirect_uri,
            "is_mobile_app": True,
        },
    }
    resp = _plaid_post("/link/token/create", payload)
    url = resp.get("hosted_link_url", "")
    if not url:
        abort(502, description="No hosted_link_url in Plaid response")
    return jsonify(url=url)


@app.get("/plaid-callback")
def plaid_callback():
    public_token = request.args.get("public_token", "")
    params = urlencode({"public_token": public_token}) if public_token else ""
    target = f"{DEEP_LINK}?{params}" if params else DEEP_LINK
    return redirect(target, code=302)


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
    app.run(host="0.0.0.0", port=5000, debug=True)
