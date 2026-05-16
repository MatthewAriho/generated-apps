# ClearSpend Plaid Proxy Server

Flask server that proxies Plaid API calls for the ClearSpend Android app. Keeps Plaid credentials server-side and handles the HTTPS redirect that Plaid requires.

## Setup

```bash
cd clearspend/server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Environment Variables

Set these before running:

```bash
export PLAID_CLIENT_ID="your_plaid_client_id"
export PLAID_SECRET="your_plaid_secret"
export PLAID_ENV="sandbox"                    # sandbox | development | production
export CLEARSPEND_API_KEY="any_shared_secret" # app sends this in X-API-Key header
```

## Run (Development)

```bash
flask run --host=0.0.0.0 --port=5000
```

## Run (Production)

Use gunicorn behind nginx with HTTPS:

```bash
pip install gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

Nginx config (minimal):
```nginx
server {
    listen 443 ssl;
    server_name yourserver.com;

    ssl_certificate     /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Plaid Dashboard Setup

1. Go to https://dashboard.plaid.com
2. Team Settings > Allowed redirect URIs
3. Add: `https://yourserver.com/plaid-callback`
4. Copy your Client ID and Secret from the Keys section
5. Set them as environment variables on the server

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | No | Health check |
| POST | `/api/link-token` | X-API-Key | Creates Plaid Hosted Link token, returns `{ url }` |
| GET | `/plaid-callback` | No | Receives Plaid redirect, 302 to `clearspend://plaid-callback` |
| POST | `/api/exchange-token` | X-API-Key | Exchanges public_token for access_token + accounts |
| POST | `/api/transactions-sync` | X-API-Key | Syncs transactions with cursor-based pagination |

## App Configuration

In the ClearSpend Android app Settings screen:
- **Server URL**: `https://yourserver.com` (no trailing slash)
- **API Key**: same value as `CLEARSPEND_API_KEY` env var
- **Environment**: must match `PLAID_ENV` on the server

## Testing

1. Start the server with sandbox credentials
2. In the app, enter the server URL and API key in Settings
3. Use "Sandbox Test" button to test direct token flow (bypasses browser)
4. Use "Plaid" button to test the full browser redirect flow
