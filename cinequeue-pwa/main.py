"""
CineQueue PWA — FastAPI backend
All business logic lives in core/; this file wires endpoints.
"""

import os
import random
import threading
import traceback
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.settings import Settings
from core.cache import MovieCache
from core.constants import MOCK_PLEX, MOCK_LB, MOCK_WATCHED, FLAG
from core.plex_client import PlexClient
from core.letterboxd_client import LetterboxdClient
from core.synology_client import SynologyClient, nas_ip_from_plex_url
from core.radarr_client import RadarrClient
from core.qbit_client import QBitClient
from core.download_queue import DownloadQueue, get_queue
from core.tmdb import PosterCache, enrich_movies, is_bad_movie, find_intersection

# ── In-memory state ──────────────────────────────────────────────────────────
_plex_movies = []
_lb_movies = []
_lb_stats = {}

# ── Server-side log ring buffer ─────────────────────────────────────────────
_log_buffer = deque(maxlen=200)

def slog(level, source, message, detail=None):
    """Append a structured log entry."""
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "level": level,
        "source": source,
        "message": message,
    }
    if detail:
        entry["detail"] = detail
    _log_buffer.appendleft(entry)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def _init_state():
    """Load settings, caches, and download queue from disk."""
    global _plex_movies, _lb_movies, _lb_stats
    Settings.init(DATA_DIR)
    Settings.load()
    MovieCache.init(DATA_DIR)
    PosterCache.init(DATA_DIR)
    DownloadQueue.load()

    cached_plex, cached_lb, cached_stats = MovieCache.load()
    if cached_plex or cached_lb:
        _plex_movies = cached_plex
        _lb_movies = cached_lb
        _lb_stats = cached_stats
        find_intersection(_plex_movies, _lb_movies)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _init_state()
    yield


_PREFIX = "/cinequeue"

_app = FastAPI(title="CineQueue", version="1.0.0", lifespan=lifespan)

# Static files will be served from /static/
static_dir = os.path.join(DATA_DIR, "static")
os.makedirs(static_dir, exist_ok=True)
_app.mount("/static", StaticFiles(directory=static_dir), name="static")


class StripPrefixMiddleware:
    """ASGI middleware that strips a path prefix before dispatching."""
    def __init__(self, app, prefix: str):
        self.app = app
        self.prefix = prefix

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "")
            if path.startswith(self.prefix):
                scope = dict(scope)
                scope["path"] = path[len(self.prefix):] or "/"
                scope["root_path"] = scope.get("root_path", "") + self.prefix
        await self.app(scope, receive, send)


# Wrap the FastAPI app: strip /cinequeue prefix from incoming requests
app = StripPrefixMiddleware(_app, _PREFIX)


# ── Pydantic models ─────────────────────────────────────────────────────────
class SettingsUpdate(BaseModel):
    plex_url: str | None = None
    plex_token: str | None = None
    lb_username: str | None = None
    tmdb_key: str | None = None
    dsm_port: str | None = None
    dsm_username: str | None = None
    dsm_password: str | None = None
    qbit_project: str | None = None
    arr_project: str | None = None
    radarr_url: str | None = None
    radarr_api_key: str | None = None
    prowlarr_url: str | None = None
    prowlarr_api_key: str | None = None
    qbit_url: str | None = None
    qbit_username: str | None = None
    qbit_password: str | None = None
    netflix_token: str | None = None
    disney_token: str | None = None
    prime_token: str | None = None


class ServiceAction(BaseModel):
    service: str  # plex | qbit_proj | arr_proj
    action: str   # start | stop


class DownloadRequest(BaseModel):
    title: str
    year: int | str = ""
    genre: str = ""
    director: str = ""
    poster_url: str = ""
    poster_color: list | None = None
    source: str = ""


# ── Health ───────────────────────────────────────────────────────────────────
@_app.get("/healthz")
def healthz():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# ── Logs ─────────────────────────────────────────────────────────────────────
@_app.get("/api/logs")
def get_logs(limit: int = 100):
    """Return recent server-side log entries."""
    return list(_log_buffer)[:limit]


# ── Settings ─────────────────────────────────────────────────────────────────
@_app.get("/api/settings")
def get_settings():
    """Return current settings (passwords masked)."""
    data = dict(Settings._data)
    for key in data:
        if 'password' in key or 'token' in key or 'api_key' in key:
            if data[key]:
                data[key] = "***"
    return data


@_app.put("/api/settings")
def update_settings(body: SettingsUpdate):
    """Update settings. Only non-None fields are written."""
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    ok = Settings.save(updates)
    return {"ok": ok}


# ── Movies ───────────────────────────────────────────────────────────────────
@_app.get("/api/movies")
def get_movies():
    """Return all loaded movies (Plex + Letterboxd) with intersection flags."""
    return {
        "plex": _plex_movies,
        "letterboxd": _lb_movies,
        "lb_stats": _lb_stats,
        "total_plex": len(_plex_movies),
        "total_lb": len(_lb_movies),
        "overlap": sum(1 for m in _plex_movies if m.get('on_lb')),
    }


@_app.get("/api/movies/watch")
def get_watch_movies(
    count: int = 3,
    sort: str = "random",
    source: str = "plex",
):
    """Return a selection of movies for the Watch screen.

    source: plex, all (plex + letterboxd combined)
    sort options: random, plex_date, lb_date, foreign, runtime
    """
    SORT_MAP = {
        "random": lambda m: random.random(),
        "plex_date": lambda m: m.get('plex_added', '') or '',
        "lb_date": lambda m: m.get('lb_added', '') or '',
        "foreign": lambda m: 0 if m.get('country', 'US') not in ('US', 'UK') else 1,
        "runtime": lambda m: m.get('runtime', 0),
    }
    if source == "all":
        # Deduplicate by title+year
        seen = set()
        pool = []
        for m in _plex_movies + _lb_movies:
            key = (m.get('title', '').lower(), m.get('year', ''))
            if key not in seen and not is_bad_movie(m):
                seen.add(key)
                pool.append(m)
    else:
        pool = [m for m in _plex_movies if not is_bad_movie(m)]
    sort_fn = SORT_MAP.get(sort, SORT_MAP["random"])
    if sort == "random":
        selected = random.sample(pool, min(count, len(pool)))
    else:
        selected = sorted(pool, key=sort_fn, reverse=(sort in ("plex_date", "lb_date")))[:count]
    return {"movies": selected, "sort": sort, "count": len(selected)}


@_app.get("/api/movies/recommend")
def get_recommendation(index: int = 0):
    """Return a single movie for the swipe-to-decide Recommend screen."""
    all_movies = _plex_movies + _lb_movies
    all_movies = [m for m in all_movies if not is_bad_movie(m)]
    if not all_movies:
        return {"movie": None, "index": index, "total": 0}
    idx = index % len(all_movies)
    return {"movie": all_movies[idx], "index": idx, "total": len(all_movies)}


# ── Sync / Refresh ───────────────────────────────────────────────────────────
def _do_sync():
    """Background: fetch fresh data from Plex + Letterboxd, enrich, cache."""
    global _plex_movies, _lb_movies, _lb_stats

    plex_url = Settings.get('plex_url')
    plex_token = Settings.get('plex_token')
    lb_user = Settings.get('lb_username')
    tmdb_key = Settings.get('tmdb_key')

    slog("info", "sync", f"Starting sync (plex={'yes' if plex_url else 'no'}, lb={'yes' if lb_user else 'no'})")
    new_plex, new_lb = [], []

    if plex_url and plex_token:
        try:
            fresh = PlexClient(plex_url, plex_token).fetch_movies()
            merged, new = MovieCache.merge(_plex_movies, fresh)
            _plex_movies = merged
            new_plex = new
            slog("info", "sync", f"Plex: {len(fresh)} fetched, {len(new)} new")
        except Exception as e:
            slog("error", "sync", f"Plex fetch failed: {e}", detail=traceback.format_exc())

    if lb_user:
        try:
            fresh = LetterboxdClient(lb_user).fetch_watchlist()
            merged, new = MovieCache.merge(_lb_movies, fresh)
            _lb_movies = merged
            new_lb = new
            slog("info", "sync", f"Letterboxd: {len(fresh)} fetched, {len(new)} new")
        except Exception as e:
            slog("error", "sync", f"Letterboxd watchlist failed: {e}", detail=traceback.format_exc())
        try:
            _lb_stats.update(LetterboxdClient(lb_user).fetch_stats())
        except Exception as e:
            slog("error", "sync", f"Letterboxd stats failed: {e}", detail=traceback.format_exc())

    find_intersection(_plex_movies, _lb_movies)

    all_new = new_plex + new_lb
    if tmdb_key and all_new:
        enrich_movies(all_new, tmdb_key)
        _plex_movies = [m for m in _plex_movies if not is_bad_movie(m)]
        _lb_movies = [m for m in _lb_movies if not is_bad_movie(m)]

    MovieCache.save(_plex_movies, _lb_movies, _lb_stats)
    slog("info", "sync", f"Sync complete: {len(_plex_movies)} plex, {len(_lb_movies)} lb movies")


@_app.post("/api/sync")
def sync_movies(background_tasks: BackgroundTasks):
    """Trigger a background sync of Plex + Letterboxd data."""
    background_tasks.add_task(_do_sync)
    return {"status": "sync_started"}


# ── Analytics ────────────────────────────────────────────────────────────────
@_app.get("/api/analytics")
def get_analytics():
    """Compute and return all analytics data."""
    current_year = str(datetime.now().year)
    watchlist_titles = {m['title'] for m in _lb_movies + _plex_movies}

    total_w = len(MOCK_WATCHED)
    total_uw = len(_plex_movies) + len(_lb_movies)
    total = total_w + total_uw

    from_watchlist_this_year = sum(
        1 for e in MOCK_WATCHED
        if e.get('date', '').startswith(current_year)
        and e['title'] in watchlist_titles)
    added_watchlist_this_year = sum(
        1 for m in _lb_movies + _plex_movies
        if (m.get('lb_added') or m.get('plex_added', '')).startswith(current_year))
    watched_outside_watchlist = sum(
        1 for e in MOCK_WATCHED if e['title'] not in watchlist_titles)

    on_both = sum(1 for m in _plex_movies if m.get('on_lb'))

    # Genre breakdown
    genres = {}
    for m in _plex_movies + _lb_movies:
        g = m.get('genre', 'Other')
        genres[g] = genres.get(g, 0) + 1

    # Country breakdown
    countries = {}
    for m in _plex_movies + _lb_movies:
        c = m.get('country', '?')
        countries[c] = countries.get(c, 0) + 1

    # Watch days
    day_counts = {}
    for entry in MOCK_WATCHED:
        try:
            day = datetime.strptime(entry['date'], '%Y-%m-%d').strftime('%A')
            day_counts[day] = day_counts.get(day, 0) + 1
        except Exception:
            pass

    # Averages
    ratings = [m['rating'] for m in _plex_movies + _lb_movies if m.get('rating')]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0
    runtimes = [m.get('runtime', 0) for m in _plex_movies + _lb_movies if m.get('runtime')]
    avg_runtime = sum(runtimes) // len(runtimes) if runtimes else 0

    # Watch progress
    lb_watchlist_total = len(_lb_movies)
    lb_watched_count = _lb_stats.get('total_films', total_w)
    lb_pct = int(lb_watched_count / (lb_watched_count + lb_watchlist_total) * 100) \
        if (lb_watched_count + lb_watchlist_total) else 0

    plex_total = len(_plex_movies)
    plex_watched = sum(1 for e in MOCK_WATCHED
                       if any(m['title'] == e['title'] for m in _plex_movies))
    plex_pct = int(plex_watched / (plex_watched + plex_total) * 100) \
        if (plex_watched + plex_total) else 0

    agg_pct = int(total_w / total * 100) if total else 0

    return {
        "summary": {
            "lb_total_watched": _lb_stats.get('total_films'),
            "lb_watched_this_year": _lb_stats.get('watched_this_year'),
            "plex_count": len(_plex_movies),
            "on_both": on_both,
        },
        "this_year": {
            "year": current_year,
            "from_watchlist": from_watchlist_this_year,
            "added_to_watchlist": added_watchlist_this_year,
            "watched_outside": watched_outside_watchlist,
        },
        "progress": {
            "letterboxd_pct": lb_pct,
            "plex_pct": plex_pct,
            "aggregated_pct": agg_pct,
            "overlap": on_both,
        },
        "genres": sorted(genres.items(), key=lambda x: -x[1]),
        "countries": sorted(countries.items(), key=lambda x: -x[1]),
        "watch_days": sorted(day_counts.items(), key=lambda x: -x[1])[:5],
        "avg_rating": avg_rating,
        "avg_runtime": avg_runtime,
    }


# ── Downloads ────────────────────────────────────────────────────────────────
@_app.get("/api/downloads")
def get_downloads():
    """Return the current download queue."""
    return {"queue": get_queue()}


@_app.post("/api/downloads")
def add_download(req: DownloadRequest, background_tasks: BackgroundTasks):
    """Add a movie to the download queue and start Radarr search."""
    movie = req.model_dump()
    entry = DownloadQueue.add(movie)
    if entry is None:
        raise HTTPException(status_code=409, detail="Already in download queue")
    background_tasks.add_task(DownloadQueue.search_and_grab, entry['id'])
    return {"entry": entry}


@_app.delete("/api/downloads/{entry_id}")
def remove_download(entry_id: str):
    """Remove an entry from the download queue."""
    DownloadQueue.remove(entry_id)
    return {"ok": True}


@_app.post("/api/downloads/poll")
def poll_downloads(background_tasks: BackgroundTasks):
    """Poll Radarr + qBittorrent for progress on active downloads."""
    background_tasks.add_task(DownloadQueue.poll_progress)
    return {"status": "polling"}


# ── Services (Synology NAS) ─────────────────────────────────────────────────
def _make_syno_client():
    plex_url = Settings.get('plex_url', '')
    nas_ip = nas_ip_from_plex_url(plex_url)
    port = Settings.get('dsm_port', '5000') or '5000'
    username = Settings.get('dsm_username', '')
    password = Settings.get('dsm_password', '')
    slog("debug", "syno", f"Building client: nas_ip={nas_ip}, port={port}, user={username}")
    if not nas_ip or not username or not password:
        msg = "Set Plex URL + NAS username & password first"
        slog("warn", "syno", msg)
        return None, msg
    return SynologyClient(nas_ip, port, username, password), None


@_app.get("/api/services/status")
def get_service_statuses():
    """Check status of all managed services (Plex, qBit, arr stack)."""
    client, err = _make_syno_client()
    if not client:
        slog("error", "services/status", err)
        raise HTTPException(status_code=400, detail=err)

    results = {}

    try:
        results['plex'] = client.plex_status()
        slog("info", "services/status", f"plex: {results['plex']}")
    except Exception as e:
        tb = traceback.format_exc()
        results['plex'] = f"error: {type(e).__name__}: {e}"
        slog("error", "services/status", f"plex: {e}", detail=tb)

    try:
        projects = client._list_projects()
        project_names = [p.get('name', '?') for p in projects] if isinstance(projects, list) else str(projects)
        slog("debug", "services/status", f"DSM projects found: {project_names}")
        nas_ip = client._nas_ip
        qbit_proj = Settings.get('qbit_project') or 'qbittorrent-gluetun'
        arr_proj = Settings.get('arr_project') or 'arr-apps'
        results['qbit_proj'] = client.project_status_from_list(qbit_proj, projects, nas_ip=nas_ip)
        results['arr_proj'] = client.project_status_from_list(arr_proj, projects, nas_ip=nas_ip)
        slog("info", "services/status", f"qbit_proj: {results['qbit_proj']}, arr_proj: {results['arr_proj']}")
    except Exception as e:
        tb = traceback.format_exc()
        results['qbit_proj'] = f"error: {type(e).__name__}: {e}"
        results['arr_proj'] = f"error: {type(e).__name__}: {e}"
        slog("error", "services/status", f"Docker projects: {e}", detail=tb)

    return results


@_app.post("/api/services/action")
def service_action(body: ServiceAction):
    """Start or stop a managed service."""
    client, err = _make_syno_client()
    if not client:
        raise HTTPException(status_code=400, detail=err)

    svc = body.service
    action = body.action

    if action not in ('start', 'stop'):
        raise HTTPException(status_code=400, detail="action must be 'start' or 'stop'")

    slog("info", "services/action", f"{action} {svc}")
    try:
        if svc == 'plex':
            result = client.plex_start() if action == 'start' else client.plex_stop()
        elif svc == 'qbit_proj':
            proj = Settings.get('qbit_project') or 'qbittorrent-gluetun'
            result = client.project_start(proj) if action == 'start' else client.project_stop(proj)
        elif svc == 'arr_proj':
            proj = Settings.get('arr_project') or 'arr-apps'
            result = client.project_start(proj) if action == 'start' else client.project_stop(proj)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown service: {svc}")
    except Exception as e:
        tb = traceback.format_exc()
        slog("error", "services/action", f"{action} {svc} failed: {e}", detail=tb)
        raise HTTPException(status_code=500, detail=str(e))

    success = result.get('success', False)
    error_code = result.get('error', {}).get('code')
    slog("info", "services/action", f"{action} {svc}: success={success}, error_code={error_code}")
    return {"success": success, "error_code": error_code}


# ── Poster proxy ─────────────────────────────────────────────────────────────
@_app.get("/api/poster")
def get_poster(url: str):
    """Download and serve a poster image from cache."""
    local = PosterCache.download(url)
    if local and os.path.exists(local):
        return FileResponse(local)
    raise HTTPException(status_code=404, detail="Poster not available")


# ── PWA files ────────────────────────────────────────────────────────────────
@_app.get("/manifest.json")
def manifest():
    path = os.path.join(DATA_DIR, "manifest.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="manifest.json not found")
    return FileResponse(path, media_type="application/manifest+json")


@_app.get("/sw.js")
def service_worker():
    path = os.path.join(DATA_DIR, "sw.js")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="sw.js not found")
    return FileResponse(path, media_type="application/javascript",
                        headers={"Service-Worker-Allowed": "/"})


@_app.get("/")
def index():
    path = os.path.join(static_dir, "index.html")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(path)
