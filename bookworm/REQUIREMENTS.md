# Bookworm — PWA Book Reader

## Overview
A Progressive Web App (PWA) book reader hosted on NAS, launchable as a Docker image.
Built with TypeScript, JavaScript, CSS (frontend) and Python (backend).

## Core Features

### Book Management
- Store and read books (ePub, PDF support)
- Pull books from the internet via a Prowlarr/Radarr-style indexer service
- Backlog of books to read
- History of read books

### Reading Experience
- In-app reader for ePub and PDF
- Progress tracking (per book, per user)
- Bookmarks and annotations (future)

### Analytics
- Reading speed tracking
- Time spent reading
- Genres and microgenres tagging
- Reading streaks and habits

### Discovery & Recommendations
- User profile built from reading history (genres, pace, preferences)
- Book recommendations based on profile
- Search and browse by genre/microgenre

### User Accounts
- Multi-user support with basic authentication (username + password, JWT)
- Per-user data stored locally on NAS
- Daily automated backup to a separate location on the NAS

### Social (Future)
- Book club features
- Shared shelves and reading lists
- Discussion threads per book

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | TypeScript + Vite, vanilla CSS (no heavy framework) |
| Backend API | Python (FastAPI) |
| Database | SQLite (per-user) + shared metadata DB |
| Book indexing | Prowlarr API integration or Jackett |
| Auth | JWT (python-jose) |
| File storage | Local NAS volume (Docker bind mount) |
| Containerisation | Docker + docker-compose |

## Data Storage
- `/data/users/{username}/` — user library, progress, settings
- `/data/books/` — shared book file store
- `/data/db/` — SQLite databases
- `/data/backups/` — daily backup destination (separate from app data)

## Docker
- Single `docker-compose.yml` launching:
  - `bookworm-api` — FastAPI backend
  - `bookworm-web` — Vite-built static files served via Nginx
- Volumes bind-mounted to NAS paths
- Daily backup via cron inside container or separate cron service

## Progress Tracking

### Phase 1 — Foundation *(complete)*
- [x] Project scaffold (Docker, Vite, FastAPI)
- [x] User auth (register, login, JWT)
- [x] Book upload and storage
- [x] ePub reader (epub.js) + PDF reader (PDF.js)
- [x] PWA install (manifest, service worker, icons)
- [x] Dark/sepia/light themes
- [x] Font size controls
- [x] Per-side margin controls (top/bottom/left/right px)
- [x] TOC panel
- [x] Highlights with colour picker + notes
- [x] Annotations list panel
- [x] Auto-hide UI overlay
- [x] Fullscreen reading mode (hides nav bar)
- [x] Swipe navigation
- [x] Prowlarr search integration
- [x] Daily backup scheduler

### Phase 2 — Library & Reader Polish *(next)*
- [x] Backlog / reading / read shelves
- [x] Progress tracking (backend + save every 30s)
- [ ] Progress display bugs (see BUGS.md)
- [ ] Touch interaction bugs (see BUGS.md)
- [ ] Internal epub link navigation (see BUGS.md)
- [ ] Library search and filter
- [ ] Read history / activity feed
- [ ] Progress indicators on book cards in library grid
- [ ] Book metadata editing
- [ ] Sort library (by title, author, last read, date added)

### Phase 3 — Analytics
- [ ] Fix remaining reader bugs (see BUGS.md for detailed notes)
- [ ] Reading speed calculation (WPM)
- [ ] Genre/microgenre tagging
- [ ] Reading stats dashboard
- [ ] Time-per-session tracking

### Phase 4 — Discovery
- [ ] User profile builder
- [ ] Recommendation engine
- [ ] Internet book search / download integration

### Phase 5 — Social (Future)
- [ ] Book clubs
- [ ] Shared shelves
- [ ] Discussion threads
