# PWA Design System

Reference document for building PWA apps (FastAPI + vanilla JS/CSS frontend).
Every app in this project MUST follow these rules.

Legacy KivyMD design rules are preserved in `design_kivy.md` for reference.

---

## 1. Golden Rule: Backend Owns Logic

ALL business logic lives in the **Python FastAPI backend**. The frontend is a thin
rendering layer — it calls the API and displays results. Never move parsing,
classification, validation, or data manipulation into JavaScript.

### Why

- The user debugs in Python, not JS
- Server-side logic is testable with `pytest` and `TestClient`
- Frontend stays small, fast, and replaceable

---

## 2. App Structure

```
<app>/
  core/                  # Business logic (no framework imports)
    __init__.py
    module.py            # One concern per file
  main.py                # FastAPI app, routes, serves static
  static/
    index.html           # Single page, all tabs inline
    app.js               # All frontend logic, fetch calls
    style.css            # All styles
    sw.js                # Service worker
    manifest.json        # PWA manifest
    icon-192.png         # App icon (any purpose)
    icon-512.png
    icon-192-maskable.png # Maskable icon (80% safe zone)
    icon-512-maskable.png
  requirements.txt
  Dockerfile
  docker-compose.yml
  deploy.sh
```

### Module pattern

Every `core/` module follows:

```python
"""One-line description."""
from __future__ import annotations

# Pure Python — no framework imports
```

`main.py` imports from `core/` and wraps in thin route handlers:
parse request → call `core/` → return JSON.

---

## 3. Page Structure

Single `index.html` with tab-based navigation. No client-side routing, no
framework, no build step.

```html
<body>
  <!-- Tab content (one per feature) -->
  <div class="tab active" id="tab-main">...</div>
  <div class="tab" id="tab-settings">...</div>

  <!-- Bottom navigation -->
  <nav class="bottom-nav">
    <button class="active" onclick="switchTab('main')">...</button>
    <button onclick="switchTab('settings')">...</button>
  </nav>
</body>
```

Rules:
- Each tab is a `div.tab` that flexes vertically
- Only one tab has `.active` at a time
- Bottom nav is sticky, always visible
- Tab headers are lightweight inline elements, not fat app bars

---

## 4. Scrollable Content Pattern

Every tab with dynamic content uses this structure:

```html
<div class="tab" id="tab-name">
  <!-- Optional: fixed controls at top -->
  <div class="controls">...</div>
  <!-- Scrollable area fills remaining space -->
  <div class="scroll-area">
    <!-- Cards, lists, etc. -->
  </div>
</div>
```

```css
.tab { display: none; flex: 1; flex-direction: column; overflow: hidden; }
.tab.active { display: flex; }
.scroll-area {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  -webkit-overflow-scrolling: touch;
}
```

---

## 5. Card Pattern

Cards group related content. Consistent spacing and radius.

```css
.card {
  background: var(--card-bg);
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 10px;
}
```

### Card with action row

```html
<div class="card">
  <div class="card-title">Title</div>
  <div class="card-body">Content</div>
  <div class="card-actions">
    <button>Edit</button>
    <button>Delete</button>
  </div>
</div>
```

---

## 6. Form Pattern

```css
input, textarea, select {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 14px;
  outline: none;
  font-family: inherit;
}
textarea { resize: none; }
```

Rules:
- All inputs are full-width by default
- Use `border-radius: 6px` for form elements
- Use `border-radius: 8-10px` for cards and buttons
- Password fields use `type="password"`
- Textareas get explicit `height` (no auto-resize)

---

## 7. Button Patterns

```css
/* Primary action */
.btn-primary {
  width: 100%;
  padding: 12px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  color: #fff;
  background: var(--primary);
}

/* Inline button row */
.btn-row {
  display: flex;
  gap: 6px;
}
.btn-row button {
  flex: 1;
  padding: 10px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  cursor: pointer;
}
```

Rules:
- Primary actions are full-width
- Button groups use flex row with `gap: 6-8px`
- Each button in a group gets `flex: 1` for equal width
- Icon buttons use unicode or inline SVG, not icon fonts

---

## 8. Color System

Every app defines its palette in CSS custom properties:

```css
:root {
  --primary: #...;       /* Main brand color */
  --primary-dark: #...;  /* Darker variant */
  --bg: #...;            /* Page background */
  --card-bg: #...;       /* Card/surface background */
  --text: #...;          /* Primary text */
  --text-muted: #...;    /* Secondary/hint text */
  --success: #...;       /* Positive actions */
  --error: #...;         /* Negative actions / errors */
  --nav-bg: #...;        /* Bottom nav background */
  --border: #...;        /* Input/card borders */
}
```

### Semantic usage

| Purpose | Variable |
|---|---|
| Primary buttons, active states | `var(--primary)` |
| Page background | `var(--bg)` |
| Cards, modals, inputs | `var(--card-bg)` |
| Body text | `var(--text)` |
| Captions, hints, timestamps | `var(--text-muted)` |
| Success states, positive actions | `var(--success)` |
| Errors, destructive actions | `var(--error)` |
| Bottom nav, dark chrome | `var(--nav-bg)` |

Theme (dark or light) is per-app. The variable names stay the same.

---

## 9. Sizing and Spacing

### Standard values

| Element | Size |
|---|---|
| Bottom nav height | `~54px` + safe area |
| Nav icon | `22px` |
| Nav label | `9px` |
| Input height | `~44px` (from padding) |
| Button height | `~44px` (from padding) |
| Card padding | `14px` |
| Card radius | `10px` |
| Input/button radius | `6-8px` |

### Standard spacing

| Context | Value |
|---|---|
| Between cards | `10px` |
| Inside cards | `8px` |
| Page padding (scroll-area) | `12px` |
| Between form fields | `10-12px` |
| Button group gap | `6-8px` |
| Between sections | `14-16px` |

---

## 10. Bottom Navigation

```css
.bottom-nav {
  display: flex;
  background: var(--nav-bg);
  padding: 6px 0 max(6px, env(safe-area-inset-bottom));
  position: sticky;
  bottom: 0;
  z-index: 100;
}
.bottom-nav button {
  flex: 1;
  background: none;
  border: none;
  color: rgba(255,255,255,0.45);
  font-size: 22px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.bottom-nav button.active { color: #fff; }
```

Rules:
- Max 5 tabs
- Use unicode emoji or simple symbols for icons
- Active state is full white, inactive is 45% opacity
- Labels below icons in 9px
- Respect `env(safe-area-inset-bottom)` for notch phones

---

## 11. Modal / Dialog Pattern

```html
<div class="modal-overlay" onclick="closeModal()">
  <div class="modal" onclick="event.stopPropagation()">
    <h3>Title</h3>
    <input id="modal-input" placeholder="...">
    <div class="modal-btns">
      <button class="cancel" onclick="closeModal()">Cancel</button>
      <button class="confirm">Save</button>
    </div>
  </div>
</div>
```

```css
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal {
  background: var(--card-bg);
  border-radius: 12px;
  padding: 20px;
  width: 85%;
  max-width: 360px;
}
```

Rules:
- Overlay closes on background tap
- Modal stops propagation
- Max width 360px for readability
- Render into a `#modal-root` div, clear on close

---

## 12. Chat / Messaging Pattern

For apps with conversational UI:

```css
.bubble {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 12px;
  margin-bottom: 6px;
  font-size: 14px;
  line-height: 1.45;
  white-space: pre-wrap;
  word-wrap: break-word;
}
.bubble.user {
  background: var(--primary);
  color: #fff;
  margin-left: auto;
  border-top-right-radius: 4px;
}
.bubble.assistant {
  background: #ededee;
  color: #1a1a1e;
  border-top-left-radius: 4px;
}
```

Input bar sticks to bottom of chat area, not the page bottom.

---

## 13. JavaScript Patterns

### API calls

```javascript
const BASE = "/<app>/api";

async function doThing() {
  const r = await fetch(BASE + "/endpoint", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key: "value" }),
  });
  const d = await r.json();
  if (!r.ok) { /* show error */ }
  else { /* update UI */ }
}
```

Rules:
- `BASE` is always `"/<app>/api"` (prefixed for Funnel routing)
- Always check `r.ok` before using response
- Use `async/await`, not `.then()` chains
- Escape user content with a text-node helper, never `innerHTML` raw input

### Tab switching

```javascript
function switchTab(name) {
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".bottom-nav button").forEach(b => b.classList.remove("active"));
  document.getElementById("tab-" + name).classList.add("active");
  document.getElementById("nav-" + name).classList.add("active");
}
```

### XSS prevention

```javascript
function esc(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}
```

Use `esc()` whenever inserting user-provided text into HTML.

---

## 14. Service Worker

```javascript
const CACHE_NAME = "<app>-v1";
const PREFIX = "/<app>";
const PRECACHE = [
  PREFIX + "/",
  PREFIX + "/static/app.js",
  PREFIX + "/static/style.css",
];
```

Rules:
- Bump `CACHE_NAME` version on every deploy
- Precache paths must include the app prefix (browser-side URLs)
- API calls (`/api/`): always network, never cache
- Static assets: stale-while-revalidate or cache-first
- `self.skipWaiting()` in install, `self.clients.claim()` in activate

---

## 15. PWA Manifest

```json
{
  "id": "/<app>/",
  "name": "App Name",
  "short_name": "App",
  "start_url": "/<app>/",
  "scope": "/<app>/",
  "display": "standalone",
  "icons": [
    { "src": "/<app>/static/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any" },
    { "src": "/<app>/static/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any" },
    { "src": "/<app>/static/icon-192-maskable.png", "sizes": "192x192", "type": "image/png", "purpose": "maskable" },
    { "src": "/<app>/static/icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

Rules:
- Serve with `media_type="application/manifest+json"`
- `scope` and `start_url` use the app prefix
- Icon paths use the prefix (browser-side URLs)
- Separate `any` and `maskable` icons — never same file for both
- Maskable content inset to inner 80%

---

## Quick Checklist

Before every deploy, verify:

- [ ] All CSS uses custom properties (no hardcoded colors except in `:root`)
- [ ] All `fetch()` calls use `BASE` prefix
- [ ] All user input escaped before HTML insertion
- [ ] Service worker cache version bumped
- [ ] Manifest `scope` and `start_url` match app prefix
- [ ] Separate maskable icons with 80% safe zone inset
- [ ] `deploy.sh` exists and includes health check
- [ ] `python3 -m pytest tests/ -v` passes
