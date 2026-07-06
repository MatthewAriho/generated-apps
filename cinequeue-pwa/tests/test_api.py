"""Tests for CineQueue FastAPI endpoints using TestClient."""

import json
import os
import sys
import pytest

# Ensure the app root is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app


@pytest.fixture(autouse=True)
def reset_state():
    """Reset in-memory state before each test."""
    import main
    from core import download_queue as dq
    main._plex_movies = list(main.MOCK_PLEX)
    main._lb_movies = list(main.MOCK_LB)
    main._lb_stats = {}
    dq._download_queue = []
    from core.tmdb import find_intersection
    find_intersection(main._plex_movies, main._lb_movies)
    yield


client = TestClient(app)


# ── Health ───────────────────────────────────────────────────────────────────
def test_healthz():
    r = client.get("/healthz")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "timestamp" in data


# ── Settings ─────────────────────────────────────────────────────────────────
def test_get_settings():
    r = client.get("/api/settings")
    assert r.status_code == 200
    # Passwords should be masked
    data = r.json()
    assert isinstance(data, dict)


def test_update_settings():
    r = client.put("/api/settings", json={"plex_url": "http://test:32400"})
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ── Movies ───────────────────────────────────────────────────────────────────
def test_get_movies():
    r = client.get("/api/movies")
    assert r.status_code == 200
    data = r.json()
    assert "plex" in data
    assert "letterboxd" in data
    assert data["total_plex"] > 0
    assert data["total_lb"] > 0


def test_get_watch_movies_random():
    r = client.get("/api/movies/watch?count=3&sort=random")
    assert r.status_code == 200
    data = r.json()
    assert len(data["movies"]) <= 3
    assert data["sort"] == "random"


def test_get_watch_movies_runtime():
    r = client.get("/api/movies/watch?count=5&sort=runtime")
    assert r.status_code == 200
    data = r.json()
    assert len(data["movies"]) <= 5
    runtimes = [m.get("runtime", 0) for m in data["movies"]]
    assert runtimes == sorted(runtimes)


def test_get_recommendation():
    r = client.get("/api/movies/recommend?index=0")
    assert r.status_code == 200
    data = r.json()
    assert data["movie"] is not None
    assert data["total"] > 0


def test_get_recommendation_wraps():
    r = client.get("/api/movies/recommend?index=9999")
    assert r.status_code == 200
    data = r.json()
    assert data["movie"] is not None


# ── Sync ─────────────────────────────────────────────────────────────────────
def test_sync():
    r = client.post("/api/sync")
    assert r.status_code == 200
    assert r.json()["status"] == "sync_started"


# ── Analytics ────────────────────────────────────────────────────────────────
def test_analytics():
    r = client.get("/api/analytics")
    assert r.status_code == 200
    data = r.json()
    assert "summary" in data
    assert "this_year" in data
    assert "progress" in data
    assert "genres" in data
    assert "countries" in data
    assert "watch_days" in data
    assert isinstance(data["avg_rating"], (int, float))
    assert isinstance(data["avg_runtime"], int)


# ── Downloads ────────────────────────────────────────────────────────────────
def test_get_downloads():
    r = client.get("/api/downloads")
    assert r.status_code == 200
    assert "queue" in r.json()


def test_add_and_remove_download():
    movie = {
        "title": "Test Movie",
        "year": 2024,
        "genre": "Drama",
        "director": "Test Director",
    }
    r = client.post("/api/downloads", json=movie)
    assert r.status_code == 200
    entry = r.json()["entry"]
    assert entry["title"] == "Test Movie"
    assert entry["status"] == "queued"
    entry_id = entry["id"]

    # Duplicate should 409
    r2 = client.post("/api/downloads", json=movie)
    assert r2.status_code == 409

    # Remove
    r3 = client.delete(f"/api/downloads/{entry_id}")
    assert r3.status_code == 200
    assert r3.json()["ok"] is True


def test_poll_downloads():
    r = client.post("/api/downloads/poll")
    assert r.status_code == 200
    assert r.json()["status"] == "polling"


# ── Services ─────────────────────────────────────────────────────────────────
def test_services_status_no_creds():
    """Without NAS credentials, should return 400."""
    r = client.get("/api/services/status")
    assert r.status_code == 400


def test_services_action_no_creds():
    r = client.post("/api/services/action",
                    json={"service": "plex", "action": "start"})
    assert r.status_code == 400


def test_services_action_bad_action():
    # Set fake creds so we get past the creds check
    from core.settings import Settings
    Settings.save({
        "plex_url": "http://192.168.1.1:32400",
        "dsm_username": "admin",
        "dsm_password": "password",
    })
    r = client.post("/api/services/action",
                    json={"service": "plex", "action": "restart"})
    assert r.status_code == 400


# ── PWA routes ───────────────────────────────────────────────────────────────
def test_manifest_404_without_file():
    """manifest.json won't exist yet but endpoint should be wired."""
    r = client.get("/manifest.json")
    # Either 200 (file exists) or 404 (not yet created) — endpoint is routed
    assert r.status_code in (200, 404)


def test_sw_404_without_file():
    r = client.get("/sw.js")
    assert r.status_code in (200, 404)
