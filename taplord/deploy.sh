#!/bin/bash
set -e
PORT=3090
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=== TapLord Deploy ==="

echo "[1/4] Building frontend..."
cd "$APP_DIR/frontend"
if command -v npm &>/dev/null; then
  # Fix ownership — Docker/Claude may create files as root
  sudo chown -R "$(whoami)" "$APP_DIR/frontend" "$APP_DIR/nginx" 2>/dev/null || true
  npm install
  npm run build
  echo "   Frontend built to nginx/dist/"
else
  echo "   npm not found, using existing dist/"
fi

echo "[2/4] Stopping existing containers..."
cd "$APP_DIR"
sudo docker compose down 2>/dev/null || true

echo "[3/4] Building and starting containers..."
sudo docker compose up -d --build

echo "[4/4] Setting up tailscale funnel..."
sudo tailscale funnel --bg --set-path /taplord http://127.0.0.1:$PORT 2>/dev/null || \
  echo "   (tailscale funnel may already be configured)"

echo ""
echo "Waiting for server to start..."
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:$PORT/api/health > /dev/null 2>&1; then
    echo ""
    echo "=== DEPLOYED ==="
    echo "Local:    http://localhost:$PORT/taplord/"
    echo "Tailnet:  https://supersecretnas.tailc3a431.ts.net/taplord/"
    exit 0
  fi
  printf "."
  sleep 2
done
echo ""
echo "Server didn't respond in 60s. Check logs:"
echo "  sudo docker compose -f $APP_DIR/docker-compose.yml logs"
exit 1
