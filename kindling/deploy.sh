#!/bin/bash
set -e
PORT=8200
APP_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "=== Kindling Deploy ==="

echo "[1/3] Stopping existing containers..."
cd "$APP_DIR"
sudo docker compose down 2>/dev/null || true

echo "[2/3] Building and starting container..."
sudo docker compose up -d --build

echo "[3/3] Setting up tailscale funnel..."
sudo tailscale funnel --bg --set-path /kindling http://127.0.0.1:$PORT 2>/dev/null || \
  echo "   (tailscale funnel may already be configured)"

echo ""
echo "Waiting for server to start..."
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:$PORT/api/health > /dev/null 2>&1; then
    echo ""
    echo "=== DEPLOYED ==="
    echo "Local:    http://localhost:$PORT/kindling/"
    echo "Tailnet:  https://supersecretnas.tailc3a431.ts.net/kindling/"
    exit 0
  fi
  printf "."
  sleep 2
done
echo ""
echo "Server didn't respond in 60s. Check logs:"
echo "  sudo docker compose -f $APP_DIR/docker-compose.yml logs"
exit 1
