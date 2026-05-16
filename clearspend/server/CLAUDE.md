# ClearSpend Plaid Proxy Server

This is a lightweight Flask server that proxies Plaid API calls for the ClearSpend Android app.

## Purpose

The Android app cannot handle Plaid's HTTPS redirect requirement directly (custom URI schemes are rejected by Plaid Dashboard). This server:
1. Holds Plaid credentials server-side (not on the phone)
2. Creates Plaid Hosted Link tokens with an HTTPS redirect URI
3. Receives the Plaid callback and bounces to `clearspend://plaid-callback` deep link
4. Proxies token exchange and transaction sync calls

## Architecture

```
Android App  -->  This Server  -->  Plaid API
                     |
              /plaid-callback  -->  302 clearspend://plaid-callback?public_token=xxx
```

## Files

- `app.py` -- Flask application with all endpoints
- `requirements.txt` -- Python dependencies (just flask)

## Environment Variables (required)

```bash
PLAID_CLIENT_ID=xxx        # From dashboard.plaid.com > Keys
PLAID_SECRET=xxx           # From dashboard.plaid.com > Keys
PLAID_ENV=sandbox          # sandbox | development | production
CLEARSPEND_API_KEY=xxx     # Shared secret - app sends in X-API-Key header
```

## Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| GET | `/` | No | Health check |
| POST | `/api/link-token` | X-API-Key | Create Plaid Hosted Link token |
| GET | `/plaid-callback` | No | Receive Plaid redirect, 302 to deep link |
| POST | `/api/exchange-token` | X-API-Key | Exchange public_token for access_token |
| POST | `/api/transactions-sync` | X-API-Key | Sync transactions with cursor pagination |

## Running

Development:
```bash
pip install -r requirements.txt
flask run --host=0.0.0.0 --port=5000
```

Production:
```bash
pip install gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

Must be behind HTTPS (nginx/caddy) for Plaid redirect URI registration.

## Plaid Dashboard Setup

Register `https://<your-domain>/plaid-callback` as an Allowed redirect URI in the Plaid Dashboard.

## Constraints

- Do NOT add authentication beyond the API key -- the app is single-user
- Do NOT store access_tokens on the server -- they are returned to the app and stored on-device
- Do NOT modify the `/plaid-callback` redirect target (`clearspend://plaid-callback`) -- the Android app's intent filter depends on this exact scheme and host
- Keep the server stateless -- no database, no sessions
- The `_plaid_post` helper handles all Plaid API communication; do not use the `requests` library (stdlib only for Plaid calls)
- Transaction category mapping happens on the app side, not here -- the server returns raw Plaid category strings

## Testing

Use the Plaid sandbox environment:
```bash
export PLAID_ENV=sandbox
export PLAID_CLIENT_ID=your_sandbox_client_id
export PLAID_SECRET=your_sandbox_secret
export CLEARSPEND_API_KEY=test123
flask run
```

Test with curl:
```bash
# Health check
curl http://localhost:5000/

# Create link token
curl -X POST http://localhost:5000/api/link-token -H "X-API-Key: test123"

# Exchange token (use a real public_token from sandbox)
curl -X POST http://localhost:5000/api/exchange-token \
  -H "X-API-Key: test123" \
  -H "Content-Type: application/json" \
  -d '{"public_token": "public-sandbox-xxx"}'
```
