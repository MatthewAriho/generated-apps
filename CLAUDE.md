# Generated Apps — Global Rules

## Default: PWA-First

All new apps in this repo are **PWAs** (FastAPI backend + thin web frontend) unless they
require offline-only operation or deep Android integration (intents, background services).

Use the **kivy-to-pwa** skill (`/workspace/.claude/skills/kivy-to-pwa/SKILL.md`) as the
authoritative reference for building and deploying PWAs.

Legacy Kivy/KivyMD rules are preserved in `claude_kivy.md` (same directory) for
maintaining older Android apps.

## Architecture

- **Backend = FastAPI (Python).** All business logic lives server-side.
- **Frontend = thin PWA** (vanilla JS, HTMX, or Vite+React). Only calls API and renders.
- **Never move logic into JS.**

## Deployment

- All apps deploy on the **Synology DS224+** behind **Tailscale Funnel**.
- Path-based routing: each app gets `--set-path /<app>` on Funnel port 10000.
- Docker with `network_mode: host` for localhost service access.
- Every app has a `deploy.sh` in its root.

## Routing Contracts (hard-won lessons)

1. **Tailscale Funnel DOES strip the `--set-path` prefix.** Backend receives `/api/foo`, not `/<app>/api/foo`.
2. **Nginx locations must be UNPREFIXED** (`/api/`, not `/<app>/api/`).
3. **Vite `base` must include the prefix** (`"/<app>/"`) so browser URLs route through Funnel.
4. **Frontend `fetch()` must use prefixed URLs** (`/<app>/api/...`) — these are browser-side.
5. **manifest.json** `scope` and `start_url` use `/<app>/` (browser-side).
6. **Service worker** precache paths use the prefix; API calls use network-first.

## Icons

- Separate `any` and `maskable` icon entries in manifest (never reuse same file).
- Maskable icons: content inset to inner 80% safe zone.
- Both 192 and 512 sizes for each purpose.

## Deploy Scripts

- Must `sudo chown` before `npm run build` (Docker creates dirs as root).
- Must include frontend build step before `docker compose up --build`.
- Health check hits container directly: `/api/health`, NOT `/<app>/api/health`.

## Testing

- Tests live in `/workspace/tests/`.
- Run `python3 -m pytest tests/ -v` after any routing/config/deploy changes.
- Add regression tests for every debugged issue.

## Port Registry

| App       | Port | Path        |
|-----------|------|-------------|
| Bookworm  | 3080 | /bookworm   |
| TapLord   | 3090 | /taplord    |
| CineQueue | 8100 | /cinequeue  |
| Kindling  | 8200 | /kindling   |
| ClearSpend| 8300 | /clearspend |
