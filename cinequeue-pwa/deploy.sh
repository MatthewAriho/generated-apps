#!/bin/bash
# CineQueue PWA — deploy locally on the NAS
set -e

PORT=8100
APP_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== CineQueue PWA Deploy ==="

# 1. Stop existing container if running
echo "[1/3] Stopping existing container..."
cd "$APP_DIR"
sudo docker compose down 2>/dev/null || true

# 2. Start container
echo "[2/3] Starting container..."
sudo docker compose up -d

# 3. Expose via tailscale funnel with path-based routing
# With network_mode: host the container listens directly on port 8100
echo "[3/3] Setting up tailscale funnel..."
sudo tailscale funnel --bg --set-path /cinequeue http://127.0.0.1:$PORT 2>/dev/null || \
  echo "   (tailscale funnel may already be configured)"

# Wait for server to be ready
echo ""
echo "Waiting for server to start..."
for i in $(seq 1 30); do
  if curl -sf http://127.0.0.1:$PORT/healthz > /dev/null 2>&1; then
    echo ""
    echo "=== DEPLOYED ==="
    echo "Local:    http://localhost:$PORT"
    echo "Tailnet:  https://supersecretnas:$PORT"
    echo ""
    echo "Open on your Pixel to install as PWA."
    exit 0
  fi
  printf "."
  sleep 2
done

echo ""
echo "Server didn't respond in 60s. Check with:"
echo "  docker compose -f $APP_DIR/docker-compose.yml logs"
exit 1
