# ClearSpend PWA — Current Status (2026-07-08)

## What's Done
- Full Kivy-to-PWA conversion complete (Steps 1-3 of workflow)
- FastAPI backend with 35+ endpoints (main.py)
- Vanilla JS PWA frontend with 8 tabs: Home, Txns, Budget, Goals, Trends, Events, Bank, Settings
- Dark mode toggle (CSS custom properties + localStorage)
- Scrollable bottom nav (replaced broken popup menu)
- Plaid integration via Flask proxy server (real bank connections)
- Bank account deduplication by item_id (fixes 13-duplicate bug)
- Delete bank account endpoint
- Auto-classification (keyword rules + Gemini fallback)
- Demo data seeding moved to Settings > Data Management
- All 22 API tests pass + 49 routing tests pass (71 total)
- Code committed and pushed to `clearspend-progress` branch

## What's Blocked — Deploy
- **Docker build hangs on DS224+** — the Celeron J4125 is too slow to build the image in reasonable time
- Suggested fix: **run directly without Docker** (like Kindling does):
  ```bash
  CLEARSPEND_DATA_DIR=~/.clearspend uvicorn main:app --host 0.0.0.0 --port 8300 &
  sudo tailscale funnel --bg --set-path /clearspend http://127.0.0.1:8300
  ```
- Update `deploy.sh` to skip Docker and run uvicorn directly
- The deploy script also starts the Plaid Flask proxy on port 5000

## What's Left
1. **Fix deploy.sh** — switch from Docker to direct uvicorn (update deploy script)
2. **Deploy and verify** — health check, manifest, SW, installability (Steps 4-5)
3. **Browser verification** — Chrome DevTools Application tab on Pixel 8 Pro
4. **Retire old Kivy APK** (Step 7) — only after user confirms parity

## Plaid Retirement (Old App)
- Old Flask proxy server at `/generated_apps/clearspend/server/app.py` is NOT running
- Access tokens from old Kivy app were on the phone only — can't retrieve them
- Plaid dashboard shows no items (likely expired or were sandbox)
- User should revoke from bank's online banking (Settings → Security → Connected Apps)
- Script at `scripts/remove_plaid_items.py` if tokens are found later

## Plaid Proxy Config
- Flask proxy: `/generated_apps/clearspend/server/app.py` on port 5000
- PLAID_CLIENT_ID: 69e46df110446b000de754e7
- PLAID_SECRET: 7c288e28e0e03966399273807f2985
- PLAID_ENV: production
- CLEARSPEND_API_KEY: clearspend-nas-2026
- PUBLIC_URL: https://supersecretnas.tailc3a431.ts.net
- deploy.sh already includes launching the proxy

## Key Files
- `main.py` — FastAPI backend (35+ endpoints)
- `core/` — database.py, classifier.py, tips.py, bank_api.py, cloud_sync.py, connectivity.py
- `static/` — index.html, app.js, style.css, sw.js, manifest.json, icons
- `deploy.sh` — needs update to skip Docker
- `docker-compose.yml` / `Dockerfile` — may not be needed if running direct
- `scripts/remove_plaid_items.py` — Plaid cleanup utility
- Tests: `/workspace/tests/test_clearspend_api.py` (22 tests)

## Port Registry
| App        | Port | Path        |
|------------|------|-------------|
| Bookworm   | 3080 | /bookworm   |
| TapLord    | 3090 | /taplord    |
| CineQueue  | 8100 | /cinequeue  |
| Kindling   | 8200 | /kindling   |
| ClearSpend | 8300 | /clearspend |
| Plaid Proxy| 5000 | (internal)  |
