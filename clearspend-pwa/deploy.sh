#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

APP=clearspend
PORT=8300
PLAID_PROXY_PORT=5000
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLAID_SERVER_DIR="$SCRIPT_DIR/../clearspend/server"

echo "=== Deploying $APP ==="

# Stop existing
sudo docker compose down 2>/dev/null || true

# Kill any existing Plaid proxy
pkill -f "flask run.*--port=$PLAID_PROXY_PORT" 2>/dev/null || true

# Start Plaid proxy server
echo "Starting Plaid proxy on port $PLAID_PROXY_PORT..."
cd "$PLAID_SERVER_DIR"
PLAID_CLIENT_ID=69e46df110446b000de754e7 \
PLAID_SECRET=7c288e28e0e03966399273807f2985 \
PLAID_ENV=production \
CLEARSPEND_API_KEY=clearspend-nas-2026 \
PUBLIC_URL=https://supersecretnas.tailc3a431.ts.net \
nohup python3 -m flask run --host=0.0.0.0 --port=$PLAID_PROXY_PORT > /tmp/clearspend-plaid-proxy.log 2>&1 &
PLAID_PID=$!
echo "Plaid proxy started (PID $PLAID_PID)"
cd "$(dirname "$0")"

# Build and start
sudo docker compose up -d --build

# Set up Funnel
sudo tailscale funnel --bg --set-path /$APP http://127.0.0.1:$PORT

# Health check
echo "Waiting for health..."
for i in $(seq 1 60); do
  if curl -sf http://127.0.0.1:$PORT/api/health > /dev/null 2>&1; then
    echo "=== $APP is live ==="
    # Pre-configure Plaid settings
    curl -sf http://127.0.0.1:$PORT/api/settings -X POST \
      -H 'Content-Type: application/json' \
      -d '{"plaid_server_url":"http://127.0.0.1:5000","plaid_api_key":"clearspend-nas-2026","plaid_env":"production"}' > /dev/null 2>&1
    echo "https://$(tailscale status --json | python3 -c 'import sys,json; print(json.load(sys.stdin)["Self"]["DNSName"].rstrip("."))')/$APP/"
    exit 0
  fi
  sleep 1
done

echo "ERROR: health check timed out"
exit 1
