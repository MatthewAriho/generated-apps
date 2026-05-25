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

### Phase 2 — Library *(next)*
- [x] Backlog / reading / read shelves
- [x] Progress tracking (backend + save every 30s)
- [ ] Library search and filter
- [ ] Read history / activity feed
- [ ] Progress indicators on book cards in library grid
- [ ] Book metadata editing
- [ ] Sort library (by title, author, last read, date added)

### Phase 3 — Analytics & Reader Features
- [ ] Reading speed calculation (WPM)
- [ ] Genre/microgenre tagging
- [ ] Reading stats dashboard
- [ ] Time-per-session tracking
- [ ] Reading streaks and habits
- [ ] Features from popular ebook apps (research Kindle, Apple Books, Kobo, Libby, Moon+ Reader, etc.):
  - Dictionary/Wikipedia lookup on word select
  - Adjustable line spacing and font family
  - Page turn animations (slide, curl)
  - Reading timer / session clock
  - Estimated time remaining in chapter/book
  - Immersive mode (auto-dim, night shift)
  - Vocabulary builder (save looked-up words)
  - Synced reading position across devices
  - Collections / custom tags
  - Import/export annotations
  - Text-to-speech
  - Flashcard generation from highlights

### Phase 4 — Discovery & Personalization
- [ ] App-wide theme changer (dark, light, midnight, ocean, etc.)
- [ ] User profile builder (from reading history, genres, pace, preferences)
- [ ] Recommendation engine
- [ ] Internet book search / download integration
- [ ] Browse by genre/microgenre

### Phase 5 — Social
- [x] **Friends & Profiles**
  - Add/follow other users (friend requests, accept/decline)
  - View others' bookshelves (books read, backlog) — friends-only visibility
  - See others' reading progress on a book
  - User search by username
  - Activity feed (friends' finished books, shared highlights)
- [x] **Shared Reading**
  - Group reading: users form a group around a specific book
  - Track each member's progress in the group
  - Send books to other users (trivial given file-based storage)
- [x] **Highlights & Comments**
  - Opt-in public highlights/annotations (shared highlights)
  - See other readers' comments on the same passage
  - Comment/reply on highlights
- [x] **Book Clubs**
  - Create/join clubs with scheduled reading targets
  - Discussion threads per club
  - Reply to discussions
  - Discover clubs (browse all clubs)
  - Club management (leave, delete)
- [x] **Notifications**
  - In-app notification system (friend requests, club discussions, highlight comments, book finished)
  - Unread count badge on Social nav tab
  - Mark as read (individual & bulk)
  - "X finished this book" / "X started reading Y" feed updates
  - [ ] Push notifications (future — requires VAPID/service worker integration)
  - [ ] Reminders when a book club meeting is due (future)

### Phase 6 — Reader Bug Fixes (see BUGS.md for full details)
- [ ] Center tap causes backward page navigation (epub.js column-snap scroll)
- [ ] Page counter / progress never updates (CFI binary search unreliable)
- [ ] Internal epub links not working (overlay blocks iframe clicks)
- [ ] Epub reader stops rendering pages after a few navigations (touch overlay may block epub.js's internal iframe swap/layout cycle; pages go blank)
