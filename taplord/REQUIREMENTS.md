# Taplord — Competitive Drinking Tracker

## Overview
A competitive beer tracking PWA — "Strava for drinking". Friend groups compete on leaderboards across events, weeks, months, and seasons. Users log beers live during events (or retroactively), track stats, and climb the rankings.

Hosted on NAS, Docker-based, multi-user with JWT auth.

## Core Concept
- Users create **events** (nights out, pub crawls, day drinking, beer runs)
- During an event, they **check in beers** — quick, drunk-proof flow (2-3 taps)
- Leaderboards rank users by beers consumed across time periods
- Friend groups via invite system
- Shame leaderboard tracks blackouts and vomiting

## Vibe
Dark and sporty (Strava-inspired black/orange) but also fun and playful — beer emojis, celebration animations, crown for #1.

---

## Features

### Auth & Users
- Register / login (username + password, JWT)
- User profile (display name, avatar initial, join date)
- Per-user stats and history

### Events (Sessions)
- **Start event**: big prominent button, name the event, optional type tag (night out, pub crawl, day drinking, beer run)
- **Live check-in**: log beers as you drink them
- **Auto-end**: event auto-closes after 5h of inactivity
- **Edit after the fact**: retroactive logging, edit event details/beers after it ends
- **Event summary**: total beers, duration, unique beers, leaderboard position change, share card
- **Blackout toggle**: self-reported, tracked on shame leaderboard
- **Vomit toggle**: self-reported, tracked on shame leaderboard
- **Event types**: night out, pub crawl, day drinking, beer run (or custom)

### Beer Check-in (the core UX — must be drunk-proof)
- **Flow**: Beer name (autocomplete from DB / free text) → size (preset buttons: 12oz, 16oz, 20oz, 335ml, 500ml + custom) → done (2-3 taps)
- **Quick repeat**: "+1" button on recently logged beers (1 tap for another of the same)
- **Optional fields** (expandable, not required): venue description, beer type/style, rating (1-5), photo, notes
- **Beer database**: seeded from open API + user-contributed entries. Free-text entries matched to DB after the fact.

### Beer Database
- Seed from open APIs (PunkAPI, Open Brewery DB, or similar)
- User entries auto-create new beers in the DB
- Fields: name, brewery, style/type, ABV (if known), image
- Autocomplete search during check-in
- Used for "unique beers" tracking and future recommendations

### Leaderboards
- **Time periods**: event, day, week, month, season (e.g., "Summer 2026"), all-time
- **Default ranking**: total beers consumed
- **Additional categories**:
  - Unique beers tried
  - Events attended
  - Longest event (duration)
  - Most beers in a single event
  - Most venues visited
  - Current streak (consecutive weeks with an event)
- **Shame leaderboard**: most blackouts, most vomits (separate tab/section)
- **Animations**: crown/badge on #1 profile, celebration animation when taking #1, notification "You just overtook [name]"

### Social
- **Friend groups**: create group, invite by username, per-group leaderboards
- **Activity feed**: friends' recent events, check-ins, leaderboard changes
- **Notifications**: overtaken on leaderboard, group invites, friend activity

### Event Summary & Sharing
- End-of-event card: total beers, duration, unique beers, position change
- Shareable image card (screenshot-friendly)
- Leaderboard position change callout

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | TypeScript + Vite, vanilla CSS |
| Backend API | Python (FastAPI) |
| Database | SQLite (database-agnostic ORM patterns for future Postgres migration) |
| Auth | JWT (python-jose + bcrypt) |
| File storage | Local NAS volume (Docker bind mount) |
| Containerisation | Docker + docker-compose |

### Database-Agnostic Notes
- Use SQLAlchemy ORM exclusively — no raw SQL
- Avoid SQLite-specific features
- Abstract DB connection for easy swap to Postgres later

---

## Data Models (core)

### User
- id, username, display_name, hashed_password, avatar_color, created_at, is_active

### Event (Session)
- id, user_id, name, type (night_out/pub_crawl/day_drinking/beer_run/custom), started_at, ended_at, is_active, blacked_out (bool), vomited (bool), venue_description (text, optional)

### CheckIn (Beer Log)
- id, event_id, user_id, beer_id (nullable — for free-text entries), beer_name, beer_style, brewery, size_ml, rating (1-5, optional), notes, photo_url, created_at

### Beer
- id, name, brewery, style, abv, image_url, created_by (user who first entered it), verified (bool)

### Group
- id, name, created_by, created_at

### GroupMember
- id, group_id, user_id, joined_at

### Notification
- id, user_id, type, message, link, is_read, created_at

---

## Docker
- `taplord-api`: FastAPI on port 8000 (internal)
- `taplord-web`: Nginx serving Vite build + proxy /api → taplord-api
- External port: 3090 (configurable via .env)
- Volumes: `./data:/data`

---

## Progress Tracking

### Phase 1 — Foundation
- [ ] Project scaffold (Docker, Vite, FastAPI)
- [ ] Auth (register, login, JWT)
- [ ] User profile
- [ ] Event CRUD (start, end, edit)
- [ ] Beer check-in flow (drunk-proof UX)
- [ ] Beer database (seed + user-contributed)
- [ ] Quick repeat (+1 same beer)
- [ ] Auto-end events after 5h inactivity
- [ ] Event summary page
- [ ] Basic leaderboard (total beers — week, month, all-time)
- [ ] PWA manifest + service worker
- [ ] Dark/sporty theme with playful elements

### Phase 2 — Competitive
- [ ] Full leaderboard categories (unique beers, events attended, longest event, etc.)
- [ ] Shame leaderboard (blackouts, vomits)
- [ ] Season leaderboards (Summer 2026, etc.)
- [ ] Crown/badge animations for #1
- [ ] Celebration animation on overtaking
- [ ] Leaderboard position change notifications
- [ ] Share card generation (event summary image)

### Phase 3 — Social
- [ ] Friend groups (create, invite, per-group leaderboards)
- [ ] Activity feed
- [ ] Notifications system
- [ ] "You overtook [name]" push

### Phase 4 — Polish & Nice-to-Have
- [ ] Group events (one person creates, friends join and log to same event)
- [ ] Global leaderboard (all users)
- [ ] Venue tracking (name, location, map)
- [ ] Beer recommendations based on history
- [ ] Offline support (queue check-ins, sync later)
- [ ] BAC estimate (optional, based on beers/weight/time)
- [ ] "Check on them" friend safety flag
- [ ] Barcode/label scanning for beer identification

### TODO — Safety & Responsibility
- [ ] "Know your limits" disclaimer on signup
- [ ] Optional BAC estimate feature
- [ ] Ability to flag a friend as "check on them" if logging heavily
- [ ] Review: does gamifying drinking need guardrails? What's the right balance?
