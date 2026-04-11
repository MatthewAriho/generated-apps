"""
CineQueue — Movie Picker App
Plex + Letterboxd integration with real API connections
"""

import random, json, os, re, ssl, threading, socket, webbrowser
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.image import AsyncImage
from kivy.uix.popup import Popup
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.textinput import TextInput
from kivy.core.text import LabelBase
from kivy.resources import resource_find

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = (0.07, 0.07, 0.10, 1)
CARD    = (0.13, 0.13, 0.18, 1)
ACCENT  = (0.95, 0.30, 0.30, 1)
ACCENT2 = (0.30, 0.60, 0.95, 1)
GREEN   = (0.20, 0.75, 0.40, 1)
GOLD    = (0.95, 0.75, 0.20, 1)
TEXT    = (0.95, 0.95, 0.95, 1)
SUBTEXT = (0.60, 0.60, 0.70, 1)

# ── Mock Fallback Data ────────────────────────────────────────────────────────
_T = "https://image.tmdb.org/t/p/w342"   # TMDB CDN base (no auth needed)

MOCK_PLEX = [
    {"title": "Blade Runner 2049", "year": 2017, "genre": "Sci-Fi", "country": "US",
     "rating": 8.0, "plex_added": "2024-01-15", "poster_color": (0.15, 0.20, 0.35, 1),
     "runtime": 164, "director": "Denis Villeneuve", "source": "plex",
     "poster_url": _T + "/gajva2L0rPYkEWjzgFlBXCAVBE5.jpg"},
    {"title": "Parasite", "year": 2019, "genre": "Thriller", "country": "KR",
     "rating": 8.6, "plex_added": "2024-02-20", "poster_color": (0.20, 0.30, 0.15, 1),
     "runtime": 132, "director": "Bong Joon-ho", "source": "plex",
     "poster_url": _T + "/7IiTTgloJzvGI1TAYymCfbfl3vT.jpg"},
    {"title": "The Grand Budapest Hotel", "year": 2014, "genre": "Comedy", "country": "US",
     "rating": 8.1, "plex_added": "2023-11-05", "poster_color": (0.40, 0.15, 0.30, 1),
     "runtime": 99, "director": "Wes Anderson", "source": "plex",
     "poster_url": _T + "/eWdyYQreja6JGCzqHWXpWHDrrPo.jpg"},
    {"title": "Spirited Away", "year": 2001, "genre": "Animation", "country": "JP",
     "rating": 8.6, "plex_added": "2024-03-10", "poster_color": (0.10, 0.25, 0.40, 1),
     "runtime": 125, "director": "Hayao Miyazaki", "source": "plex",
     "poster_url": _T + "/39wmItIWsg5sZMyRUHLkWBcuVCM.jpg"},
    {"title": "No Country for Old Men", "year": 2007, "genre": "Crime", "country": "US",
     "rating": 8.1, "plex_added": "2023-12-18", "poster_color": (0.30, 0.20, 0.10, 1),
     "runtime": 122, "director": "Coen Brothers", "source": "plex",
     "poster_url": _T + "/6d5XOczc2bqDMB3wBqBpTBQQiJa.jpg"},
    {"title": "Portrait of a Lady on Fire", "year": 2019, "genre": "Romance", "country": "FR",
     "rating": 8.1, "plex_added": "2024-01-28", "poster_color": (0.35, 0.10, 0.10, 1),
     "runtime": 122, "director": "Celine Sciamma", "source": "plex",
     "poster_url": _T + "/sygBh89OG7E0mBxBVmf3VwI2sXI.jpg"},
    {"title": "Everything Everywhere", "year": 2022, "genre": "Sci-Fi", "country": "US",
     "rating": 7.8, "plex_added": "2024-02-14", "poster_color": (0.25, 0.10, 0.35, 1),
     "runtime": 139, "director": "Daniels", "source": "plex",
     "poster_url": _T + "/w3LxiVYdWWRvEVdn5RYq6jIqkb1.jpg"},
    {"title": "The Lighthouse", "year": 2019, "genre": "Horror", "country": "US",
     "rating": 7.5, "plex_added": "2023-10-31", "poster_color": (0.20, 0.20, 0.20, 1),
     "runtime": 109, "director": "Robert Eggers", "source": "plex",
     "poster_url": _T + "/5EFh4QAKKtKtTMNDGnI4H8Ao3JH.jpg"},
]

MOCK_LB = [
    {"title": "Drive My Car", "year": 2021, "genre": "Drama", "country": "JP",
     "rating": 7.9, "lb_added": "2024-03-01", "poster_color": (0.10, 0.15, 0.30, 1),
     "runtime": 179, "director": "Ryusuke Hamaguchi", "source": "letterboxd",
     "poster_url": _T + "/oFMSsm7tl3VIF5GkLBSxdNnqVSX.jpg"},
    {"title": "The Favourite", "year": 2018, "genre": "Drama", "country": "UK",
     "rating": 7.5, "lb_added": "2024-02-10", "poster_color": (0.25, 0.25, 0.15, 1),
     "runtime": 119, "director": "Yorgos Lanthimos", "source": "letterboxd",
     "poster_url": _T + "/5k7bH2Mzm9k4LiRKHAHDGaI2fSP.jpg"},
    {"title": "Aftersun", "year": 2022, "genre": "Drama", "country": "UK",
     "rating": 7.7, "lb_added": "2024-01-05", "poster_color": (0.15, 0.30, 0.25, 1),
     "runtime": 101, "director": "Charlotte Wells", "source": "letterboxd",
     "poster_url": _T + "/s3VBKN5nCqJlgGORfT0MvdVJlhU.jpg"},
    {"title": "Tar", "year": 2022, "genre": "Drama", "country": "US",
     "rating": 7.5, "lb_added": "2024-03-15", "poster_color": (0.20, 0.15, 0.25, 1),
     "runtime": 158, "director": "Todd Field", "source": "letterboxd",
     "poster_url": _T + "/7j6uRfvGkgZzFw0SjFJTEqD5rVU.jpg"},
    {"title": "Cache", "year": 2005, "genre": "Thriller", "country": "FR",
     "rating": 7.7, "lb_added": "2024-02-28", "poster_color": (0.30, 0.25, 0.10, 1),
     "runtime": 117, "director": "Michael Haneke", "source": "letterboxd",
     "poster_url": _T + "/d9nBoowhjiiYc4FBNtQkPY7c11H.jpg"},
]

MOCK_WATCHED = [
    {"title": "Dune", "year": 2021, "date": "2024-03-20"},
    {"title": "The Batman", "year": 2022, "date": "2024-03-15"},
    {"title": "Past Lives", "year": 2023, "date": "2024-03-10"},
    {"title": "Oppenheimer", "year": 2023, "date": "2024-02-28"},
    {"title": "Poor Things", "year": 2023, "date": "2024-02-14"},
    {"title": "May December", "year": 2023, "date": "2024-02-05"},
    {"title": "Barbie", "year": 2023, "date": "2024-01-20"},
    {"title": "Saltburn", "year": 2023, "date": "2024-01-10"},
    {"title": "Priscilla", "year": 2023, "date": "2023-12-25"},
    {"title": "Monster", "year": 2023, "date": "2023-12-18"},
    {"title": "Killers of the Flower Moon", "year": 2023, "date": "2023-12-05"},
    {"title": "The Zone of Interest", "year": 2023, "date": "2023-11-30"},
]

# ── Live Data Store ───────────────────────────────────────────────────────────
_plex_movies    = list(MOCK_PLEX)
_lb_movies      = list(MOCK_LB)
_lb_stats       = {}   # scraped from Letterboxd profile: total_films, watched_this_year
_refresh_cbs    = []
_download_queue = []   # list of DownloadEntry dicts (persisted to cinequeue_downloads.json)

def _notify_refresh():
    for cb in list(_refresh_cbs):
        try:
            cb()
        except Exception:
            pass

# ── Settings ──────────────────────────────────────────────────────────────────
class Settings:
    _data = {}
    _path = None

    @classmethod
    def _file(cls):
        if cls._path is None:
            try:
                base = App.get_running_app().user_data_dir
            except Exception:
                base = os.path.expanduser('~')
            cls._path = os.path.join(base, 'cinequeue.json')
        return cls._path

    @classmethod
    def load(cls):
        try:
            f = cls._file()
            if os.path.exists(f):
                with open(f) as fp:
                    cls._data = json.load(fp)
        except Exception:
            pass
        return cls._data

    @classmethod
    def save(cls, updates):
        cls._data.update(updates)
        try:
            with open(cls._file(), 'w') as fp:
                json.dump(cls._data, fp, indent=2)
            return True
        except Exception:
            return False

    @classmethod
    def get(cls, key, default=''):
        val = cls._data.get(key)
        if val is None:
            return default  # key doesn't exist at all
        return val          # return whatever was saved, including ''

# ── Movie Cache ───────────────────────────────────────────────────────────────
class MovieCache:
    """Persists movie data across launches to avoid re-fetching everything."""
    _path = None
    _TMDB_FIELDS = ('poster_url', 'poster_color', 'director', 'runtime',
                    'genre', 'country', 'year')
    _EMPTY_VALS  = (None, '', 'Unknown', '?', 0)

    @classmethod
    def _file(cls):
        if cls._path is None:
            try:
                base = App.get_running_app().user_data_dir
            except Exception:
                base = os.path.expanduser('~')
            cls._path = os.path.join(base, 'cinequeue_movies.json')
        return cls._path

    @classmethod
    def load(cls):
        """Returns (plex_movies, lb_movies, lb_stats). Empty lists if no cache."""
        try:
            f = cls._file()
            if os.path.exists(f):
                with open(f) as fp:
                    d = json.load(fp)
                plex = d.get('plex', [])
                lb   = d.get('lb',   [])
                stats = d.get('lb_stats', {})
                if plex or lb:
                    #print(f"[Cache] Loaded {len(plex)} plex, {len(lb)} lb movies")
                    return plex, lb, stats
        except Exception as e:
            pass
            #print(f"[Cache] Load failed: {e}")
        return [], [], {}

    @classmethod
    def save(cls, plex_movies, lb_movies, lb_stats):
        try:
            with open(cls._file(), 'w') as fp:
                json.dump({
                    'plex':     plex_movies,
                    'lb':       lb_movies,
                    'lb_stats': lb_stats,
                    'saved_at': datetime.now().isoformat(),
                }, fp)
            #print(f"[Cache] Saved {len(plex_movies)} plex, {len(lb_movies)} lb")
        except Exception as e:
            pass
            #print(f"[Cache] Save failed: {e}")

    @classmethod
    def merge(cls, cached, fresh):
        """Merge fresh API results into cached list.
        Returns (merged, new_only).
        TMDB enrichment from cache is preserved for existing movies."""
        def _key(m): return m['title'].lower().strip()
        cached_map = {_key(m): m for m in cached}

        merged, new = [], []
        for m in fresh:
            k = _key(m)
            if k in cached_map:
                old = cached_map[k]
                updated = dict(m)
                # Keep TMDB-enriched fields from cache if fresh data is empty/unknown
                for field in cls._TMDB_FIELDS:
                    if updated.get(field) in cls._EMPTY_VALS and \
                            old.get(field) not in cls._EMPTY_VALS:
                        updated[field] = old[field]
                merged.append(updated)
            else:
                merged.append(m)
                new.append(m)
        return merged, new

# ── Plex Client ───────────────────────────────────────────────────────────────
class PlexClient:
    _COUNTRY = {
        'Japan': 'JP', 'South Korea': 'KR', 'France': 'FR',
        'United Kingdom': 'UK', 'United States of America': 'US',
        'Germany': 'DE', 'Italy': 'IT', 'Spain': 'ES',
        'Australia': 'AU', 'Canada': 'CA', 'China': 'CN',
        'Sweden': 'SE', 'Denmark': 'DK', 'Norway': 'NO',
        'Mexico': 'MX', 'Brazil': 'BR', 'India': 'IN',
    }

    def __init__(self, url, token):
        self.url   = url.rstrip('/')
        self.token = token
        self._ctx  = ssl._create_unverified_context()

    def _get(self, path, timeout=30):
        sep = '&' if '?' in path else '?'
        req = urllib.request.Request(
            f"{self.url}{path}{sep}X-Plex-Token={self.token}",
            headers={'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=timeout, context=self._ctx) as r:
            return json.loads(r.read())

    def fetch_movies(self):
        sections = self._get('/library/sections')['MediaContainer'].get('Directory', [])
        movies = []
        for sec in sections:
            if sec.get('type') != 'movie':
                continue
            items = self._get(
                f"/library/sections/{sec['key']}/all?type=1", timeout=60
            )['MediaContainer'].get('Metadata', [])
            for item in items:
                thumb = item.get('thumb', '')
                added = item.get('addedAt', 0)
                try:
                    plex_added = datetime.fromtimestamp(added).strftime('%Y-%m-%d')
                except Exception:
                    plex_added = ''
                raw_c = (item.get('Country') or [{}])[0].get('tag', '')
                cc = self._COUNTRY.get(raw_c, raw_c[:2].upper() if raw_c else 'US')
                movies.append({
                    'title':       item.get('title', 'Unknown'),
                    'year':        item.get('year', 0),
                    'genre':       (item.get('Genre') or [{}])[0].get('tag', 'Unknown'),
                    'country':     cc,
                    'rating':      float(item.get('audienceRating') or item.get('rating') or 0),
                    'plex_added':  plex_added,
                    'poster_url':  (f"{self.url}{thumb}?X-Plex-Token={self.token}"
                                    if thumb else None),
                    'poster_color': CARD,
                    'runtime':     (item.get('duration') or 0) // 60000,
                    'director':    (item.get('Director') or [{}])[0].get('tag', 'Unknown'),
                    'source':      'plex',
                })
        return movies

# ── Letterboxd Client ─────────────────────────────────────────────────────────
class LetterboxdClient:
    def __init__(self, username):
        self.username = username.lstrip('@').strip()
        self._ctx = ssl._create_unverified_context()

    def fetch_watchlist(self):
        from html import unescape
        movies = []
        page = 1

        while True:
            url = f"https://letterboxd.com/{self.username}/watchlist/page/{page}/"
            #print(f"[Letterboxd] Fetching page {page}: {url}")

            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            try:
                with urllib.request.urlopen(req, timeout=20, context=self._ctx) as r:
                    html = r.read().decode('utf-8', errors='replace')
                #print(f"[Letterboxd] Got response, length={len(html)} chars")
            except urllib.error.HTTPError as e:
                #print(f"[Letterboxd] HTTPError {e.code} on page {page} — stopping pagination")
                if e.code == 404:
                    break
                raise

            poster_divs = re.findall(
                r'<div[^>]+class="react-component"[^>]+data-target-link="/film/[^>]+>',
                html
            )
            #print(f"[Letterboxd] Found {len(poster_divs)} react-component film divs on page {page}")

            if not poster_divs:
                #print(f"[Letterboxd] No films found on page {page} — stopping")
                break

            for i, tag in enumerate(poster_divs):
                #print(f"[Letterboxd]   [{i}] Raw tag: {tag[:200]}")

                slug_m = re.search(r'data-target-link="/film/([^/]+)/"', tag)
                slug = slug_m.group(1) if slug_m else None
                if not slug:
                    #print(f"[Letterboxd]   [{i}] No slug found — skipping")
                    continue

                title = slug.replace('-', ' ').title()
                #print(f"[Letterboxd]   [{i}] slug={slug!r}  title={title!r}")

                movies.append({
                    'title':        title,
                    'year':         0,
                    'genre':        'Unknown',
                    'country':      '?',
                    'rating':       0.0,
                    'lb_added':     '',
                    'poster_url':   None,
                    'poster_color': CARD,
                    'runtime':      0,
                    'director':     'Unknown',
                    'source':       'letterboxd',
                })

            next_page_url = f'/watchlist/page/{page + 1}/'
            has_next = next_page_url in html
            #print(f"[Letterboxd] Next page check: {next_page_url!r} in html → {has_next}")

            if not has_next:
                #print(f"[Letterboxd] No next page found — done after page {page}")
                break

            page += 1

        #print(f"[Letterboxd] Done. Total films fetched: {len(movies)}")
        return movies

    def fetch_stats(self):
        """Scrape basic watch stats from the user's Letterboxd profile."""
        stats = {}
        try:
            url = f"https://letterboxd.com/{self.username}/"
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=20, context=self._ctx) as r:
                html = r.read().decode('utf-8', errors='replace')

            # Total films watched
            m = re.search(r'data-stat="film-count"[^>]*>\s*<span[^>]*>([\d,]+)', html)
            if m:
                stats['total_films'] = int(m.group(1).replace(',', ''))
                #print(f"[LB Stats] Total films: {stats['total_films']}")

            # This year
            year = datetime.now().year
            year_url = f"https://letterboxd.com/{self.username}/films/year/{year}/"
            req2 = urllib.request.Request(year_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req2, timeout=20, context=self._ctx) as r2:
                year_html = r2.read().decode('utf-8', errors='replace')

            film_divs = re.findall(r'<li[^>]+class="[^"]*poster-container[^"]*"', year_html)
            stats['watched_this_year'] = len(film_divs)
            #print(f"[LB Stats] Watched this year: {stats['watched_this_year']}")
        except Exception as e:
            #print(f"[LB Stats] Error: {e}")
            pass
        return stats

# ── Synology Client ───────────────────────────────────────────────────────────
class SynologyClient:
    """Controls Plex (package) and Docker containers via DSM 7 REST API."""

    _AUTH_ERRORS = {
        400: "Wrong username or password",
        401: "Account disabled",
        402: "Permission denied — add user to administrators group in DSM Control Panel → User & Group",
        403: "2FA is enabled — create a DSM user without 2FA for the app",
        404: "2FA code incorrect",
        407: "Account locked (too many attempts) — unlock in DSM Control Panel → User",
        411: "Account locked down",
    }

    _API_ERRORS = {
        100: "Unknown error",
        101: "Invalid parameter",
        102: "API does not exist",
        103: "Method does not exist",
        105: "Permission denied — user needs administrator rights in DSM",
        106: "Session timeout — will retry",
        107: "Session interrupted",
        114: "Container may be in a stack/project — try starting from Container Manager",
        # 2104 intentionally NOT here — handled per-call in project methods
    }

    def __init__(self, nas_ip, port, username, password):
        self._nas_ip  = nas_ip
        self._port    = str(port)
        self.username = username
        self.password = password
        self._sid     = None
        self._ctx     = ssl._create_unverified_context()
        self.base     = self._resolve_base()

    def _resolve_base(self):
        """Try HTTP first, fall back to HTTPS if connection refused."""
        return f"http://{self._nas_ip}:{self._port}/webapi/entry.cgi"

    def _url(self, params):
        return self.base + '?' + urllib.parse.urlencode(params)

    def _get(self, url, timeout=10):
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(url), timeout=timeout,
                    context=self._ctx) as r:
                return json.loads(r.read())
        except (socket.timeout, TimeoutError):
            raise  # don't retry on timeout — it would double the wait
        except OSError:
            # Retry on HTTPS port if HTTP connection was refused
            https_base = f"https://{self._nas_ip}:{int(self._port)+1}/webapi/entry.cgi"
            alt_url = url.replace(self.base, https_base)
            with urllib.request.urlopen(
                    urllib.request.Request(alt_url), timeout=timeout,
                    context=self._ctx) as r:
                data = json.loads(r.read())
            self.base = https_base  # switch permanently
            return data

    def _login(self):
        params = {'api': 'SYNO.API.Auth', 'method': 'login', 'version': '7',
                  'account': self.username, 'passwd': self.password,
                  'session': 'CineQueue', 'format': 'sid',
                  'device_name': 'CineQueue'}
        body = urllib.parse.urlencode(params).encode()
        try:
            req = urllib.request.Request(self.base, data=body,
                                         method='POST',
                                         headers={'Content-Type':
                                                  'application/x-www-form-urlencoded'})
            with urllib.request.urlopen(req, timeout=10, context=self._ctx) as r:
                data = json.loads(r.read())
        except OSError:
            https_base = f"https://{self._nas_ip}:{int(self._port)+1}/webapi/entry.cgi"
            req = urllib.request.Request(https_base, data=body,
                                         method='POST',
                                         headers={'Content-Type':
                                                  'application/x-www-form-urlencoded'})
            with urllib.request.urlopen(req, timeout=10, context=self._ctx) as r:
                data = json.loads(r.read())
            self.base = https_base
        if data.get('success'):
            self._sid = data['data']['sid']
        else:
            code = data.get('error', {}).get('code', '?')
            msg  = self._AUTH_ERRORS.get(code, f"code {code}")
            raise Exception(msg)

    def _req(self, params, timeout=10):
        if not self._sid:
            self._login()
        result = self._get(self._url(dict(params, _sid=self._sid)), timeout)
        # Re-login on expired/invalid session and retry once
        if not result.get('success'):
            code = result.get('error', {}).get('code')
            if code in (106, 119):
                self._sid = None
                self._login()
                result = self._get(self._url(dict(params, _sid=self._sid)), timeout)
        return result

    # ── Plex package ──────────────────────────────────────────────────────────
    def plex_status(self):
        d = self._req({'api': 'SYNO.Core.Package', 'method': 'list',
                       'version': '2', 'additional': '["status"]'}, timeout=60)
        for pkg in d.get('data', {}).get('packages', []):
            print(f"pkg - {pkg.get('id')}")
            if pkg.get('id') == 'PlexMediaServer':
                for k, v in pkg.items():
                    print(f"  {k}: {v}")
                return pkg.get('additional', {}).get('status', 'unknown')
        return 'not installed'

    def discover_package_apis(self):
        url = self.base.replace('entry.cgi', 'query.cgi') + \
              '?api=SYNO.API.Info&method=query&version=1&query=all'
        print(f"[Discovery] Querying all APIs...")
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15, context=self._ctx) as r:
                data = json.loads(r.read())
            apis = data.get('data', {})
            print(f"[Discovery] Total APIs found: {len(apis)}")
            for name, info in sorted(apis.items()):
                if 'package' in name.lower():
                    print(f"  {name}: min={info.get('minVersion')} "
                          f"max={info.get('maxVersion')} path={info.get('path')}")
        except Exception as e:
            print(f"[Discovery] Error: {e}")

    def discover_control_methods(self):
        if not self._sid:
            self._login()
        print("\n--- SYNO.Core.Package.Control ---")
        combos = [
            {'method': 'start', 'id': 'PlexMediaServer'},
            {'method': 'stop',  'id': 'PlexMediaServer'},
            {'method': 'set',   'id': 'PlexMediaServer', 'status': 'stop'},
            {'method': 'set',   'id': 'PlexMediaServer', 'action': 'stop'},
            {'method': 'set',   'name': 'PlexMediaServer', 'status': 'stop'},
            {'method': 'stop',  'name': 'PlexMediaServer'},
            {'method': 'start', 'name': 'PlexMediaServer'},
        ]
        for combo in combos:
            params = {'api': 'SYNO.Core.Package.Control', 'version': '1',
                      '_sid': self._sid, **combo}
            try:
                result = self._get(self._url(params), timeout=15)
                print(f"  {combo} → success={result.get('success')} "
                      f"code={result.get('error', {}).get('code')} "
                      f"data={result.get('data')}")
            except Exception as e:
                print(f"  {combo} → exception={e}")
        print("\n--- SYNO.Core.Package v1+v2 ---")
        for method in ['start', 'stop', 'restart']:
            for version in [1, 2]:
                for id_key in ['id', 'name']:
                    params = {'api': 'SYNO.Core.Package', 'method': method,
                              'version': str(version), id_key: 'PlexMediaServer',
                              '_sid': self._sid}
                    try:
                        result = self._get(self._url(params), timeout=15)
                        print(f"  Core.Package.{method} v{version} {id_key}= → "
                              f"success={result.get('success')} "
                              f"code={result.get('error', {}).get('code')}")
                    except Exception as e:
                        print(f"  Core.Package.{method} v{version} {id_key}= → exception={e}")

    def _try_pkg_control(self, action, timeout):
        # SYNO.Core.Package.Control with method=start/stop is the correct DSM 7.2 API
        params = {
            'api': 'SYNO.Core.Package.Control',
            'method': action,
            'version': '1',
            'id': 'PlexMediaServer',
        }
        r = self._req(params, timeout=timeout)
        return r

    def plex_start(self):
        return self._try_pkg_control('start', timeout=60)

    def plex_stop(self):
        return self._try_pkg_control('stop', timeout=60)

    # ── Docker Compose projects ───────────────────────────────────────────────
    # DSM 7.2+ Container Manager: SYNO.ContainerManager.Project
    # DSM <7.2 Docker package:    SYNO.Docker.Project
    _PROJECT_APIS = ('SYNO.Docker.Project',)

    def _list_projects(self):
        for api in self._PROJECT_APIS:
            for attempt in range(2):
                try:
                    r = self._req({'api': api, 'method': 'list', 'version': '1'}, timeout=20)
                    if r.get('success'):
                        data = r.get('data', {})
                        if isinstance(data, dict):
                            projects = list(data.values())
                            return projects
                        if isinstance(data, list):
                            return data
                    break
                except (socket.timeout, TimeoutError):
                    if attempt == 0:
                        continue
                except Exception as e:
                    print(f"[Projects] {api} list → exception: {e}")
                    break
        return []

    def _project_by_name(self, name):
        for p in self._list_projects():
            pname = (p.get('name') or p.get('project_name') or
                     p.get('compose_project_name') or '')
            if pname == name:
                return p
        return None

    def project_status(self, name):
        # kept for back-compat but check_all uses project_status_from_list instead
        p = self._project_by_name(name)
        if p is None:
            all_names = [q.get('name') for q in self._list_projects()]
            return f'not found (have: {", ".join(str(n) for n in all_names)})'
        status = (p.get('status') or p.get('state') or 'unknown').lower()
        return status

    def _check_arr_services(self, nas_ip):
        """Check arr services by probing HTTP ports directly."""
        services = {'prowlarr': 9696, 'sonarr': 8989, 'radarr': 7878}
        results = {}
        for name, port in services.items():
            try:
                url = f"http://{nas_ip}:{port}/"
                req = urllib.request.Request(url, headers={'User-Agent': 'CineQueue/1.0'})
                with urllib.request.urlopen(req, timeout=5, context=self._ctx) as r:
                    results[name] = 'running'
            except urllib.error.HTTPError:
                results[name] = 'running'  # any HTTP response = service is up
            except Exception:
                results[name] = 'stopped'
        return results

    def project_status_from_list(self, name, projects, nas_ip=None):
        p = next((p for p in projects if p.get('name') == name), None)
        if p is None:
            all_names = [q.get('name') for q in projects]
            return f'not found (have: {", ".join(str(n) for n in all_names)})'

        if name == 'arr-apps' and nas_ip:
            svc_statuses = self._check_arr_services(nas_ip)
            running = [n for n, s in svc_statuses.items() if s == 'running']
            stopped = [n for n, s in svc_statuses.items() if s == 'stopped']
            if not stopped:
                return 'running'
            elif not running:
                return f'stopped ({", ".join(stopped)} down)'
            else:
                return f'partial ({", ".join(stopped)} down)'

        status = (p.get('status') or p.get('state') or 'unknown').lower()
        return status

    def _project_action(self, method, name, timeout):
        projects = self._list_projects()
        p = next((p for p in projects if p.get('name') == name), None)
        if p is None:
            raise Exception(f"Project '{name}' not found")
        project_id = p.get('id')
        r = self._req({
            'api': 'SYNO.Docker.Project',
            'method': method,
            'version': '1',
            'id': project_id,
        }, timeout=timeout)
        return r

    def project_start(self, name):
        return self._project_action('start', name, timeout=60)

    def project_stop(self, name):
        return self._project_action('stop', name, timeout=60)

def _nas_ip_from_plex_url(plex_url):
    """Extract hostname/IP from the stored Plex URL."""
    try:
        return urllib.parse.urlparse(plex_url).hostname or ''
    except Exception:
        return ''

def syno_action_async(action_fn, on_done, on_error):
    def run():
        try:
            result = action_fn()
            Clock.schedule_once(lambda dt: on_done(result), 0)
        except Exception as e:
            exc = e
            Clock.schedule_once(lambda dt: on_error(str(exc)), 0)
    threading.Thread(target=run, daemon=True).start()

# ── Prowlarr Client ───────────────────────────────────────────────────────────
class ProwlarrClient:
    """Reserved for future direct indexer access via Prowlarr API v1.
    Prowlarr aggregates torrent/NZB indexers into a single search proxy.

    Currently NOT used in the download pipeline — Radarr (which connects to
    Prowlarr internally) handles movie searching. ProwlarrClient is kept here
    for future use cases:
    - Manual release browsing / release picker UI
    - Fallback search if Radarr is unavailable
    - Multi-indexer health checks
    - NZB/Usenet support independent of Radarr
    """
    CATEGORIES_MOVIE = [2000, 2010, 2020, 2030, 2040, 2045, 2050, 2060]

    def __init__(self, base_url, api_key):
        self._base = base_url.rstrip('/')
        self._key  = api_key

    def _get(self, path, params=None, timeout=15):
        qs  = urllib.parse.urlencode(params or {})
        url = f"{self._base}{path}?{qs}" if qs else f"{self._base}{path}"
        req = urllib.request.Request(url, headers={'X-Api-Key': self._key})
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as r:
            return json.loads(r.read().decode())

    def search(self, title, year=None):
        query = f"{title} {year}" if year else title
        cats  = ','.join(str(c) for c in self.CATEGORIES_MOVIE)
        results = self._get('/api/v1/search', {
            'query': query, 'type': 'search',
            'indexerIds': '-1', 'categories': cats,
        })
        return results if isinstance(results, list) else []

    def indexers(self):
        return self._get('/api/v1/indexer')


# ── Radarr Client ─────────────────────────────────────────────────────────────
class RadarrClient:
    """REST client for Radarr API v3.
    Radarr is the correct service for managing and searching movies:
    - It connects to Prowlarr for indexer search under the hood
    - It manages quality profiles, root folders, and the movie library
    - It sends grabs directly to qBittorrent/SABnzbd as configured

    Flow: lookup(title) → get quality profile + root folder → add_movie() →
          Radarr auto-searches indexers → sends to download client → we poll queue()

    Future ideas:
    - Expose quality profile selection to the user (currently uses first available)
    - Show Radarr's grab history per movie (radarr_movie_id stored in entry)
    - Support manual search trigger: POST /api/v3/command {name: MovieSearch}
    - Sync Radarr library back to CineQueue's "on Plex" status after download
    - Handle "already in Radarr" gracefully (update monitored flag instead of re-adding)
    - Use Radarr tags to mark movies added via CineQueue
    """

    def __init__(self, base_url, api_key):
        self._base = base_url.rstrip('/')
        self._key  = api_key

    def _ctx(self):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def _req(self, method, path, params=None, body=None, timeout=15):
        qs  = urllib.parse.urlencode(params or {})
        url = f"{self._base}{path}?{qs}" if qs else f"{self._base}{path}"
        data = json.dumps(body).encode() if body is not None else None
        headers = {'X-Api-Key': self._key, 'Content-Type': 'application/json'}
        req = urllib.request.Request(url, data=data, method=method,
                                     headers=headers)
        with urllib.request.urlopen(req, context=self._ctx(), timeout=timeout) as r:
            return json.loads(r.read().decode())

    def lookup(self, title, year=None):
        """Search Radarr's movie lookup (TMDB-backed). Returns list of candidates."""
        term = f"{title} {year}" if year else title
        results = self._req('GET', '/api/v3/movie/lookup', {'term': term})
        return results if isinstance(results, list) else []

    def quality_profiles(self):
        return self._req('GET', '/api/v3/qualityProfile')

    def root_folders(self):
        return self._req('GET', '/api/v3/rootFolder')

    def add_movie(self, tmdb_id, title, year, quality_profile_id, root_folder_path,
                  search_on_add=True):
        """Add a movie to Radarr and optionally trigger an immediate search."""
        body = {
            'tmdbId':           tmdb_id,
            'title':            title,
            'year':             year,
            'qualityProfileId': quality_profile_id,
            'rootFolderPath':   root_folder_path,
            'monitored':        True,
            'addOptions':       {'searchForMovie': search_on_add},
        }
        return self._req('POST', '/api/v3/movie', body=body)

    def get_movie(self, radarr_id):
        """Get movie record by Radarr internal ID."""
        return self._req('GET', f'/api/v3/movie/{radarr_id}')

    def queue(self, radarr_id=None):
        """Return Radarr's download queue. Optionally filter by movie ID."""
        params = {}
        if radarr_id:
            params['movieId'] = radarr_id
        result = self._req('GET', '/api/v3/queue', params)
        records = result.get('records', result) if isinstance(result, dict) else result
        return records if isinstance(records, list) else []

    def command(self, name, **kwargs):
        """Trigger a Radarr command (e.g. MovieSearch, RescanMovie)."""
        body = {'name': name, **kwargs}
        return self._req('POST', '/api/v3/command', body=body)


# ── qBittorrent Client ────────────────────────────────────────────────────────
class QBitClient:
    """REST client for qBittorrent Web API v2.
    Used to track download progress once Prowlarr has sent a release.

    Future ideas:
    - Auto-move completed downloads to a /movies folder
    - Trigger Plex library scan via PlexClient on completion
    - Pause/resume individual downloads from the Downloads tab
    - Show per-file progress for multi-file torrents
    - Support categories so downloads land in the right Plex library path
    """
    def __init__(self, base_url, username='admin', password='adminadmin'):
        self._base = base_url.rstrip('/')
        self._user = username
        self._pass = password
        self._sid  = None   # session cookie (SID)

    def _ctx(self):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def login(self):
        data = urllib.parse.urlencode({'username': self._user,
                                       'password': self._pass}).encode()
        req = urllib.request.Request(f"{self._base}/api/v2/auth/login",
                                     data=data, method='POST')
        with urllib.request.urlopen(req, context=self._ctx(), timeout=10) as r:
            cookie = r.headers.get('Set-Cookie', '')
            for part in cookie.split(';'):
                if part.strip().startswith('SID='):
                    self._sid = part.strip()[4:]
            return r.read().decode().strip() == 'Ok.'

    def _get(self, path, params=None, timeout=10):
        qs  = urllib.parse.urlencode(params or {})
        url = f"{self._base}{path}?{qs}" if qs else f"{self._base}{path}"
        headers = {'Cookie': f'SID={self._sid}'} if self._sid else {}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=self._ctx(), timeout=timeout) as r:
            return json.loads(r.read().decode())

    def get_torrents(self, hashes=None):
        """Return list of torrent info dicts. Optionally filter by hash list."""
        params = {}
        if hashes:
            params['hashes'] = '|'.join(hashes)
        return self._get('/api/v2/torrents/info', params)

    def torrent_by_hash(self, h):
        """Return info for a single torrent, or None if not found."""
        results = self.get_torrents(hashes=[h])
        return results[0] if results else None

    def add_magnet(self, magnet_url, save_path=None):
        """Add a magnet link. Returns True on success."""
        fields = {'urls': magnet_url}
        if save_path:
            fields['savepath'] = save_path
        data = urllib.parse.urlencode(fields).encode()
        headers = {'Cookie': f'SID={self._sid}'} if self._sid else {}
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        req = urllib.request.Request(f"{self._base}/api/v2/torrents/add",
                                     data=data, method='POST', headers=headers)
        with urllib.request.urlopen(req, context=self._ctx(), timeout=10) as r:
            return r.read().decode().strip() == 'Ok.'


# ── Download Queue ────────────────────────────────────────────────────────────
class DownloadQueue:
    """Persistent download queue stored in cinequeue_downloads.json.

    Each entry dict:
      id           — unique string (title+year slug)
      title        — movie title
      year         — release year
      genre        — genre string
      director     — director
      poster_url   — URL for poster image
      poster_color — fallback color tuple
      added_at     — ISO timestamp when queued
      status       — queued | searching | results_found | no_results |
                     grabbing | downloading | complete | failed
      results      — list of Prowlarr release dicts (populated after search)
      chosen       — chosen release dict (after auto-pick)
      qbit_hash    — torrent hash string (after grab)
      progress     — 0.0–1.0 download progress
      qbit_status  — raw qBit state string (downloading, seeding, paused, etc.)
      eta_secs     — estimated seconds remaining
      size_bytes   — total file size
      error        — error message if failed

    Future ideas (not yet implemented):
    - quality_profile: per-entry quality preference (1080p, 4K, 720p)
    - subtitle_lang: auto-search subtitles on complete
    - auto_refresh_plex: trigger Plex scan when status → complete
    - retry_count: track retry attempts for failed entries
    - preferred_indexer: whitelist trusted indexers per user
    - download_path: custom save path per movie
    - tags: user-defined tags for grouping downloads
    - notification_sent: track if a completion notification was shown
    """
    _FILE = 'cinequeue_downloads.json'

    @staticmethod
    def _path():
        d = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(d, DownloadQueue._FILE)

    @staticmethod
    def load():
        global _download_queue
        try:
            with open(DownloadQueue._path(), 'r') as f:
                _download_queue = json.load(f)
        except Exception:
            _download_queue = []

    @staticmethod
    def save():
        try:
            with open(DownloadQueue._path(), 'w') as f:
                json.dump(_download_queue, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def add(movie):
        """Add a movie to the queue. Deduplicates by title+year."""
        global _download_queue
        entry_id = re.sub(r'[^a-z0-9]', '_',
                          f"{movie['title']}_{movie.get('year','')}".lower())
        if any(e['id'] == entry_id for e in _download_queue):
            return None  # already queued
        entry = {
            'id':           entry_id,
            'title':        movie['title'],
            'year':         movie.get('year', ''),
            'genre':        movie.get('genre', ''),
            'director':     movie.get('director', ''),
            'poster_url':   movie.get('poster_url', ''),
            'poster_color': list(movie.get('poster_color', list(CARD))),
            'added_at':     datetime.now().strftime('%Y-%m-%d %H:%M'),
            'status':       'queued',
            'results':      [],
            'chosen':       None,
            'qbit_hash':    None,
            'progress':     0.0,
            'qbit_status':  '',
            'eta_secs':     -1,
            'size_bytes':   0,
            'radarr_id':    None,
            'error':        '',
        }
        _download_queue.append(entry)
        DownloadQueue.save()
        return entry

    @staticmethod
    def update(entry_id, **kwargs):
        global _download_queue
        for e in _download_queue:
            if e['id'] == entry_id:
                e.update(kwargs)
                DownloadQueue.save()
                return e
        return None

    @staticmethod
    def remove(entry_id):
        global _download_queue
        _download_queue = [e for e in _download_queue if e['id'] != entry_id]
        DownloadQueue.save()

    @staticmethod
    def search_and_grab(entry_id, on_update):
        """Background: Radarr lookup → add movie → Radarr searches via Prowlarr → qBit.
        Radarr is the correct service for movie management; it uses Prowlarr internally
        for indexer access and sends releases directly to the configured download client.
        on_update(entry) called on main thread after each state change."""
        radarr_url = Settings.get('radarr_url', '')
        radarr_key = Settings.get('radarr_api_key', '')

        def run():
            entry = next((e for e in _download_queue if e['id'] == entry_id), None)
            if not entry:
                return

            if not radarr_url or not radarr_key:
                DownloadQueue.update(entry_id, status='failed',
                                     error='Radarr URL/API key not set in Settings')
                Clock.schedule_once(lambda dt: on_update(entry), 0)
                return

            client = RadarrClient(radarr_url, radarr_key)

            # 1. Lookup movie in Radarr (TMDB-backed)
            DownloadQueue.update(entry_id, status='searching', error='')
            Clock.schedule_once(lambda dt: on_update(entry), 0)
            try:
                candidates = client.lookup(entry['title'], entry.get('year'))
                if not candidates:
                    DownloadQueue.update(entry_id, status='no_results',
                                         error='Movie not found in Radarr/TMDB lookup')
                    Clock.schedule_once(lambda dt: on_update(entry), 0)
                    return
                # Pick closest title+year match
                year = entry.get('year')
                best_candidate = next(
                    (c for c in candidates
                     if str(c.get('year','')) == str(year)
                     and c.get('title','').lower() == entry['title'].lower()),
                    candidates[0])
                tmdb_id = best_candidate.get('tmdbId') or best_candidate.get('id')
                DownloadQueue.update(entry_id, status='results_found',
                                      chosen={'title': best_candidate.get('title'),
                                              'year':  best_candidate.get('year'),
                                              'tmdbId': tmdb_id})
                Clock.schedule_once(lambda dt: on_update(entry), 0)
            except Exception as e:
                DownloadQueue.update(entry_id, status='failed', error=str(e))
                Clock.schedule_once(lambda dt: on_update(entry), 0)
                return

            # 2. Get quality profile + root folder (use first available)
            try:
                profiles     = client.quality_profiles()
                root_folders = client.root_folders()
                if not profiles or not root_folders:
                    raise RuntimeError('No quality profiles or root folders in Radarr')
                profile_id   = profiles[0]['id']
                root_path    = root_folders[0]['path']
            except Exception as e:
                DownloadQueue.update(entry_id, status='failed',
                                      error=f"Radarr config error: {e}")
                Clock.schedule_once(lambda dt: on_update(entry), 0)
                return

            # 3. Add movie to Radarr + trigger automatic search via Prowlarr indexers
            try:
                DownloadQueue.update(entry_id, status='grabbing')
                Clock.schedule_once(lambda dt: on_update(entry), 0)
                result = client.add_movie(
                    tmdb_id=tmdb_id,
                    title=entry['title'],
                    year=int(entry.get('year') or 0),
                    quality_profile_id=profile_id,
                    root_folder_path=root_path,
                    search_on_add=True)
                radarr_id = result.get('id')
                DownloadQueue.update(entry_id, status='downloading',
                                      radarr_id=radarr_id, qbit_hash=None)
                Clock.schedule_once(lambda dt: on_update(entry), 0)
            except Exception as e:
                err = str(e)
                # Radarr returns 400 if movie already exists — treat as success
                if '400' in err or 'already' in err.lower():
                    DownloadQueue.update(entry_id, status='downloading',
                                          error='Already in Radarr — monitoring active')
                else:
                    DownloadQueue.update(entry_id, status='failed', error=err)
                Clock.schedule_once(lambda dt: on_update(entry), 0)

        threading.Thread(target=run, daemon=True).start()

    @staticmethod
    def poll_progress(on_update):
        """Poll Radarr queue + qBittorrent for download progress on active entries.
        Radarr queue provides the authoritative status (it knows the Radarr state);
        qBittorrent gives byte-level progress and ETA.
        Future: cache qBit SID session to avoid re-login every poll."""
        radarr_url = Settings.get('radarr_url', '')
        radarr_key = Settings.get('radarr_api_key', '')
        qbit_url   = Settings.get('qbit_url', '')
        qbit_user  = Settings.get('qbit_username', 'admin')
        qbit_pass  = Settings.get('qbit_password', 'adminadmin')
        active     = [e for e in _download_queue
                      if e['status'] in ('downloading', 'grabbing')]
        if not active:
            return

        def run():
            # 1. Poll Radarr queue for status of each entry that has a radarr_id
            radarr_queue = []
            if radarr_url and radarr_key:
                try:
                    radarr_queue = RadarrClient(radarr_url, radarr_key).queue()
                except Exception:
                    pass

            # 2. Poll qBittorrent for byte-level progress
            torrents = []
            if qbit_url:
                try:
                    qb = QBitClient(qbit_url, qbit_user, qbit_pass)
                    if qb.login():
                        torrents = qb.get_torrents()
                except Exception:
                    pass

            for entry in active:
                updates = {}

                # Match in Radarr queue by radarr_id or title
                rq_match = None
                if entry.get('radarr_id'):
                    rq_match = next((r for r in radarr_queue
                                     if r.get('movieId') == entry['radarr_id']), None)
                if not rq_match:
                    rq_match = next((r for r in radarr_queue
                                     if r.get('title','').lower() ==
                                        entry['title'].lower()), None)
                if rq_match:
                    size_left = rq_match.get('sizeleft', 0)
                    size_tot  = rq_match.get('size', 0)
                    prog      = (1.0 - size_left / size_tot) if size_tot else 0.0
                    state     = rq_match.get('status', '')
                    updates.update(progress=prog, qbit_status=state,
                                   size_bytes=int(size_tot))

                # Match in qBit by hash or title slug for finer ETA
                qb_match = None
                if entry.get('qbit_hash'):
                    qb_match = next((t for t in torrents
                                     if t['hash'] == entry['qbit_hash']), None)
                if not qb_match:
                    slug = entry['title'].lower().replace(' ', '.')
                    qb_match = next((t for t in torrents
                                     if slug[:12] in t.get('name','').lower()), None)
                if qb_match:
                    prog  = qb_match.get('progress', updates.get('progress', 0.0))
                    state = qb_match.get('state', updates.get('qbit_status', ''))
                    updates.update(
                        qbit_hash=qb_match['hash'],
                        progress=prog,
                        qbit_status=state,
                        eta_secs=qb_match.get('eta', -1),
                        size_bytes=qb_match.get('size', updates.get('size_bytes', 0)))

                if updates:
                    prog   = updates.get('progress', entry.get('progress', 0.0))
                    status = 'complete' if prog >= 1.0 else 'downloading'
                    updates['status'] = status
                    DownloadQueue.update(entry['id'], **updates)
                    Clock.schedule_once(lambda dt: on_update(), 0)

        threading.Thread(target=run, daemon=True).start()

    # Keep old name as alias for callers
    poll_qbit = poll_progress


# ── Async Fetch Helpers ───────────────────────────────────────────────────────
def fetch_plex_async(url, token, on_done, on_error):
    def run():
        try:
            movies = PlexClient(url, token).fetch_movies()
            #print(f"[Plex] Fetched {len(movies)} movies")
            Clock.schedule_once(lambda dt: on_done(movies), 0)
        except Exception as e:
            exc = e
            #print(f"[Plex] Error: {exc}")
            Clock.schedule_once(lambda dt: on_error(str(exc)), 0)
    threading.Thread(target=run, daemon=True).start()

def fetch_lb_async(username, on_done, on_error):
    def run():
        try:
            movies = LetterboxdClient(username).fetch_watchlist()
            #print(f"[LB] Fetched {len(movies)} watchlist movies")
            Clock.schedule_once(lambda dt: on_done(movies), 0)
        except Exception as e:
            exc = e
            #print(f"[LB] Error: {exc}")
            Clock.schedule_once(lambda dt: on_error(str(exc)), 0)
    threading.Thread(target=run, daemon=True).start()

def fetch_lb_stats_async(username, on_done, on_error):
    def run():
        try:
            stats = LetterboxdClient(username).fetch_stats()
            Clock.schedule_once(lambda dt: on_done(stats), 0)
        except Exception as e:
            exc = e
            Clock.schedule_once(lambda dt: on_error(str(exc)), 0)
    threading.Thread(target=run, daemon=True).start()

# ── Data Quality / Intersection ───────────────────────────────────────────────
def _is_bad_movie(m):
    """Return True if movie data looks too broken to display."""
    if not m.get('title') or len(m['title'].strip()) < 2:
        return True
    if m.get('runtime', 0) < 1:
        return True  # 0-min runtime means missing data
    unknown = sum(1 for v in [m.get('genre'), m.get('director')]
                  if str(v).strip() in ('Unknown', '?', '', 'None'))
    return unknown >= 2

def _find_intersection(plex_movies, lb_movies):
    """Tag each movie with on_plex / on_lb flags for intersection highlighting."""
    lb_keys = {m['title'].lower().strip() for m in lb_movies}
    px_keys = {m['title'].lower().strip() for m in plex_movies}
    for m in plex_movies:
        m['on_plex'] = True
        m['on_lb']   = m['title'].lower().strip() in lb_keys
    for m in lb_movies:
        m['on_lb']   = True
        m['on_plex'] = m['title'].lower().strip() in px_keys
    shared = sum(1 for m in plex_movies if m.get('on_lb'))
    #print(f"[Intersection] {shared} movies on both Plex and LB watchlist")

# ── KV ────────────────────────────────────────────────────────────────────────
KV = """
#:import dp kivy.metrics.dp

<NavBar>:
    size_hint_y: None
    height: dp(56)
    spacing: 0
    canvas.before:
        Color:
            rgba: 0.10, 0.10, 0.14, 1
        Rectangle:
            pos: self.pos
            size: self.size

<SectionLabel>:
    size_hint_y: None
    height: dp(36)
    font_size: dp(13)
    bold: True
    markup: True
    color: 0.60, 0.60, 0.70, 1
    halign: 'left'
    valign: 'middle'
    text_size: self.width, self.height
    padding_x: dp(4)
"""
Builder.load_string(KV)

# ── TMDB Enrichment ───────────────────────────────────────────────────────────
_TMDB_COUNTRY = {
    'United States of America': 'US', 'United Kingdom': 'UK',
    'Japan': 'JP', 'South Korea': 'KR', 'France': 'FR',
    'Germany': 'DE', 'Italy': 'IT', 'Spain': 'ES', 'Australia': 'AU',
    'Canada': 'CA', 'Sweden': 'SE', 'Denmark': 'DK', 'Norway': 'NO',
    'Mexico': 'MX', 'Brazil': 'BR', 'India': 'IN', 'China': 'CN',
}

def fetch_tmdb_posters_async(movies, api_key, on_done):
    """Back-compat: delegates to full enrichment."""
    fetch_tmdb_enrich_async(movies, api_key, on_done)

def fetch_tmdb_enrich_async(movies, api_key, on_done):
    """Enrich movies using TMDB: fills poster, runtime, genre, director, country, year.
       After enrichment, filters bad data from the global lists."""
    def run():
        search  = "https://api.themoviedb.org/3/search/movie"
        detail  = "https://api.themoviedb.org/3/movie"
        img     = "https://image.tmdb.org/t/p/w342"

        _ctx = ssl._create_unverified_context()
        for m in movies:
            needs = (
                not m.get('poster_url') or
                m.get('runtime', 0) < 1 or
                m.get('genre') in ('Unknown', '?', '', None) or
                m.get('director') in ('Unknown', '?', '', None) or
                not m.get('year')
            )
            if not needs:
                continue

            try:
                t   = urllib.parse.quote(m['title'])
                yr  = m.get('year', '')
                url = f"{search}?api_key={api_key}&query={t}&year={yr}&language=en-US"
                req = urllib.request.Request(url, headers={'Accept': 'application/json'})
                with urllib.request.urlopen(req, timeout=10, context=_ctx) as r:
                    results = json.loads(r.read()).get('results', [])

                if not results:
                    #print(f"[TMDB] No results for {m['title']!r}")
                    continue

                top = results[0]
                tmdb_id = top.get('id')

                if not m.get('poster_url') and top.get('poster_path'):
                    m['poster_url'] = img + top['poster_path']
                if not m.get('year') and top.get('release_date'):
                    try: m['year'] = int(top['release_date'][:4])
                    except Exception: pass

                if tmdb_id and (m.get('runtime', 0) < 1 or
                                m.get('genre') in ('Unknown', '?', '', None) or
                                m.get('director') in ('Unknown', '?', '', None)):
                    durl = f"{detail}/{tmdb_id}?api_key={api_key}&append_to_response=credits"
                    req2 = urllib.request.Request(durl, headers={'Accept': 'application/json'})
                    with urllib.request.urlopen(req2, timeout=10, context=_ctx) as r2:
                        d = json.loads(r2.read())

                    rt = d.get('runtime', 0)
                    if rt > 0 and m.get('runtime', 0) < 1:
                        m['runtime'] = rt

                    genres = d.get('genres', [])
                    if genres and m.get('genre') in ('Unknown', '?', '', None):
                        m['genre'] = genres[0]['name']

                    crew = d.get('credits', {}).get('crew', [])
                    dirs = [c['name'] for c in crew if c.get('job') == 'Director']
                    if dirs and m.get('director') in ('Unknown', '?', '', None):
                        m['director'] = dirs[0]

                    if m.get('country') in ('?', '', None):
                        pcs = d.get('production_countries', [])
                        if pcs:
                            raw = pcs[0].get('name', '')
                            m['country'] = _TMDB_COUNTRY.get(raw, raw[:2].upper() if raw else '?')

                #print(f"[TMDB] Enriched {m['title']!r}: rt={m.get('runtime')} genre={m.get('genre')}")

            except Exception as e:
                #print(f"[TMDB] Error for {m['title']!r}: {e}")
                pass

        # Filter bad data out of global lists
        global _plex_movies, _lb_movies
        before_px = len(_plex_movies)
        before_lb = len(_lb_movies)
        _plex_movies = [m for m in _plex_movies if not _is_bad_movie(m)]
        _lb_movies   = [m for m in _lb_movies   if not _is_bad_movie(m)]
        #print(f"[TMDB] Filtered: plex {before_px}→{len(_plex_movies)}, lb {before_lb}→{len(_lb_movies)}")

        Clock.schedule_once(lambda dt: on_done(), 0)

    threading.Thread(target=run, daemon=True).start()

# ── Emoji helper ──────────────────────────────────────────────────────────────
def E(s):
    """Wrap text in NotoEmoji font markup for Kivy labels with markup=True."""
    return f"[font=NotoEmoji]{s}[/font]"

# ── Shared Widgets ────────────────────────────────────────────────────────────
# Flag emoji use Regional Indicator pairs — NotoEmoji renders each indicator
# as a styled letter square (e.g. 🇯🇵 → squared J + squared P), which looks
# good and is clearly readable without needing ligature shaping.
FLAG = {"JP": "🇯🇵", "KR": "🇰🇷", "FR": "🇫🇷", "UK": "🇬🇧", "US": "🇺🇸",
        "DE": "🇩🇪", "IT": "🇮🇹", "SE": "🇸🇪", "AU": "🇦🇺", "CN": "🇨🇳",
        "IN": "🇮🇳", "BR": "🇧🇷", "MX": "🇲🇽", "DK": "🇩🇰", "NO": "🇳🇴"}

class SectionLabel(Label):
    pass

# ── Downloads Screen ──────────────────────────────────────────────────────────
class DownloadsScreen(Screen):
    """Tracks movies queued for download through the Prowlarr + qBittorrent pipeline.

    Status flow per entry:
      queued → searching → results_found / no_results → grabbing → downloading → complete / failed

    Future features to build here:
    - Drag-to-reorder priority queue
    - Tap entry to see all Prowlarr search results and pick a different release
    - Quality preference badge (user-chosen: 1080p / 4K / 720p)
    - Auto Plex library refresh when status → complete
    - Completed downloads badge count on tab button
    - Filter buttons: All | Downloading | Complete | Failed
    - Subtitle search trigger (OpenSubtitles) after completion
    - Batch-add from Recommend swipe gestures
    - Estimated storage usage total across all downloading entries
    """

    _STATUS_COLOR = {
        'queued':        (0.60, 0.60, 0.70, 1),  # SUBTEXT
        'searching':     (0.95, 0.75, 0.20, 1),  # GOLD
        'results_found': (0.30, 0.60, 0.95, 1),  # ACCENT2
        'no_results':    (0.95, 0.30, 0.30, 1),  # ACCENT
        'grabbing':      (0.95, 0.75, 0.20, 1),  # GOLD
        'downloading':   (0.30, 0.60, 0.95, 1),  # ACCENT2
        'complete':      (0.20, 0.75, 0.40, 1),  # GREEN
        'failed':        (0.95, 0.30, 0.30, 1),  # ACCENT
    }
    _STATUS_LABEL = {
        'queued':        '● Queued',
        'searching':     '● Searching Prowlarr…',
        'results_found': '● Release found',
        'no_results':    '● No releases found',
        'grabbing':      '● Sending to qBit…',
        'downloading':   '● Downloading',
        'complete':      '● Complete',
        'failed':        '● Failed',
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._poll_ev    = None
        self._list_box   = None
        self._empty_lbl  = None
        self._build_ui()

    def on_enter(self):
        self._rebuild_list()
        self._poll_ev = Clock.schedule_interval(lambda dt: self._poll(), 30)

    def on_leave(self):
        if self._poll_ev:
            self._poll_ev.cancel()
            self._poll_ev = None

    def _build_ui(self):
        root = BoxLayout(orientation='vertical')
        with root.canvas.before:
            Color(*BG)
            Rectangle(pos=root.pos, size=root.size)

        hdr = BoxLayout(size_hint_y=None, height=dp(50), padding=[dp(12), dp(8)])
        with hdr.canvas.before:
            Color(0.10, 0.10, 0.14, 1)
            self._hdr_rect = Rectangle(pos=hdr.pos, size=hdr.size)
        hdr.bind(pos=lambda w, _: self._upd_rect(w),
                 size=lambda w, _: self._upd_rect(w))
        hdr.add_widget(Label(text="[b]Downloads[/b]", markup=True,
                             font_size=dp(20), color=ACCENT,
                             halign='left', valign='middle'))
        refresh_btn = Button(text="↺", font_size=dp(18),
                             size_hint_x=None, width=dp(40),
                             background_normal="", background_color=(0,0,0,0),
                             color=ACCENT2)
        refresh_btn.bind(on_press=lambda *_: (self._poll(), self._rebuild_list()))
        hdr.add_widget(refresh_btn)
        root.add_widget(hdr)

        scroll = ScrollView()
        self._list_box = BoxLayout(orientation='vertical', size_hint_y=None,
                                   spacing=dp(8), padding=[dp(8), dp(8)])
        self._list_box.bind(minimum_height=self._list_box.setter('height'))
        self._empty_lbl = Label(
            text="No downloads queued.\nTap Download on any movie not available on Plex.",
            font_size=dp(13), color=SUBTEXT, halign='center', valign='middle',
            size_hint_y=None, height=dp(120))
        self._empty_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        self._list_box.add_widget(self._empty_lbl)
        scroll.add_widget(self._list_box)
        root.add_widget(scroll)
        self.add_widget(root)

    def _upd_rect(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(0.10, 0.10, 0.14, 1)
            Rectangle(pos=w.pos, size=w.size)

    def _rebuild_list(self):
        self._list_box.clear_widgets()
        if not _download_queue:
            self._list_box.add_widget(self._empty_lbl)
            return
        for entry in reversed(_download_queue):  # newest first
            self._list_box.add_widget(self._make_entry_card(entry))

    def _make_entry_card(self, entry):
        card = BoxLayout(orientation='vertical', size_hint_y=None,
                         height=dp(110), padding=[dp(10), dp(8)], spacing=dp(4))
        with card.canvas.before:
            Color(*CARD)
            RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(10)])
        card.bind(pos=lambda w, _: self._redraw_card(w),
                  size=lambda w, _: self._redraw_card(w))

        # Row 1: title + status badge
        row1 = BoxLayout(size_hint_y=None, height=dp(22))
        title_lbl = Label(
            text=f"[b]{entry['title']}[/b]  ({entry.get('year','')})",
            markup=True, font_size=dp(13), color=TEXT,
            halign='left', valign='middle')
        title_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        status = entry.get('status', 'queued')
        status_lbl = Label(
            text=self._STATUS_LABEL.get(status, status),
            font_size=dp(10),
            color=self._STATUS_COLOR.get(status, SUBTEXT),
            size_hint_x=None, width=dp(130),
            halign='right', valign='middle')
        status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        row1.add_widget(title_lbl)
        row1.add_widget(status_lbl)
        card.add_widget(row1)

        # Row 2: genre · director · added
        meta = f"{entry.get('genre','')}  ·  {entry.get('director','')}  ·  {entry.get('added_at','')}"
        meta_lbl = Label(text=meta, font_size=dp(9), color=SUBTEXT,
                         size_hint_y=None, height=dp(16),
                         halign='left', valign='middle')
        meta_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        card.add_widget(meta_lbl)

        # Row 3: progress bar or error/result info
        if status == 'downloading':
            prog     = entry.get('progress', 0.0)
            eta_secs = entry.get('eta_secs', -1)
            pct_txt  = f"{int(prog * 100)}%"
            if eta_secs > 0:
                m, s = divmod(int(eta_secs), 60)
                h, m = divmod(m, 60)
                eta_txt = f"  ETA {h}h {m}m" if h else f"  ETA {m}m {s}s"
            else:
                eta_txt = ''
            size_mb  = entry.get('size_bytes', 0) / 1024 / 1024
            size_txt = f"  {size_mb:.0f} MB" if size_mb > 0 else ''
            info_lbl = Label(
                text=f"{pct_txt}{eta_txt}{size_txt}",
                font_size=dp(10), color=ACCENT2,
                size_hint_y=None, height=dp(16),
                halign='left', valign='middle')
            info_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            card.add_widget(info_lbl)
            # Progress bar
            pb_box = BoxLayout(size_hint_y=None, height=dp(8))
            with pb_box.canvas.before:
                Color(*CARD)
                RoundedRectangle(pos=pb_box.pos, size=pb_box.size, radius=[dp(4)])
            pb_box.bind(pos=lambda w, _: self._redraw_prog_bg(w),
                        size=lambda w, _: self._redraw_prog_bg(w))
            fill = BoxLayout(size_hint_x=max(prog, 0.02))
            fill._fill_color = ACCENT2
            with fill.canvas.before:
                Color(*ACCENT2)
                RoundedRectangle(pos=fill.pos, size=fill.size, radius=[dp(4)])
            fill.bind(pos=lambda w, _: self._redraw_fill(w),
                      size=lambda w, _: self._redraw_fill(w))
            pb_box.add_widget(fill)
            pb_box.add_widget(Widget(size_hint_x=1.0 - max(prog, 0.02)))
            card.add_widget(pb_box)
        elif status == 'failed' and entry.get('error'):
            err_lbl = Label(text=entry['error'], font_size=dp(9), color=ACCENT,
                            size_hint_y=None, height=dp(16),
                            halign='left', valign='middle')
            err_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            card.add_widget(err_lbl)
        elif status == 'results_found' and entry.get('chosen'):
            chosen = entry['chosen']
            rel_title = chosen.get('title', '')[:50]
            seeders   = chosen.get('seeders', '?')
            size_mb   = (chosen.get('size') or 0) / 1024 / 1024
            size_txt  = f"{size_mb:.0f} MB" if size_mb > 0 else ''
            info_lbl = Label(
                text=f"{rel_title}  ·  {seeders} seeders  {size_txt}",
                font_size=dp(9), color=ACCENT2,
                size_hint_y=None, height=dp(16), halign='left', valign='middle')
            info_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            card.add_widget(info_lbl)
        elif status == 'no_results':
            retry_row = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(8))
            retry_btn = Button(text="↺ Retry Search", font_size=dp(10),
                               background_normal="", background_color=CARD,
                               color=ACCENT2)
            retry_btn.bind(on_press=lambda *_, eid=entry['id']:
                           self._retry(eid))
            retry_row.add_widget(retry_btn)
            card.add_widget(retry_row)

        # Row: remove button
        btn_row = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(8))
        btn_row.add_widget(Widget())
        remove_btn = Button(text="Remove", font_size=dp(9),
                            size_hint_x=None, width=dp(70),
                            background_normal="", background_color=(0.3,0.1,0.1,1),
                            color=ACCENT)
        remove_btn.bind(on_press=lambda *_, eid=entry['id']: self._remove(eid))
        btn_row.add_widget(remove_btn)
        card.add_widget(btn_row)
        return card

    def _redraw_card(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*CARD)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(10)])

    def _redraw_prog_bg(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(0.2, 0.2, 0.25, 1)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(4)])

    def _redraw_fill(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*getattr(w, '_fill_color', ACCENT2))
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(4)])

    def _retry(self, entry_id):
        DownloadQueue.search_and_grab(entry_id, lambda e: self._rebuild_list())

    def _remove(self, entry_id):
        DownloadQueue.remove(entry_id)
        self._rebuild_list()

    def _poll(self):
        DownloadQueue.poll_progress(self._rebuild_list)
        self._rebuild_list()


class NavBar(BoxLayout):
    def __init__(self, manager, **kwargs):
        super().__init__(**kwargs)
        self.manager = manager
        for label, name in [("Watch","watch"),("Recommend","recommend"),
                             ("Analytics","analytics"),("Downloads","downloads"),
                             ("Settings","settings")]:
            btn = Button(text=label, font_size=dp(10), bold=True,
                         background_color=(0,0,0,0), color=SUBTEXT)
            btn.screen_name = name
            btn.bind(on_press=self._switch)
            self.add_widget(btn)

    def _switch(self, btn):
        self.manager.current = btn.screen_name
        for b in self.children:
            b.color = ACCENT if b is btn else SUBTEXT


class PosterWidget(FloatLayout):
    """AsyncImage if poster_url, otherwise colored placeholder."""
    def __init__(self, movie, h=dp(160), **kwargs):
        super().__init__(size_hint_y=None, height=h, **kwargs)
        with self.canvas.before:
            Color(*movie.get('poster_color', CARD))
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)

        url = movie.get('poster_url')
        if url:
            self.add_widget(AsyncImage(source=url, allow_stretch=True,
                                       keep_ratio=False, size_hint=(1, 1)))
        else:
            cc     = movie.get('country', '?')
            rating = movie.get('rating', 0)
            text   = f"{cc}\n{E('⭐')} {rating:.1f}" if rating else cc
            self.add_widget(Label(text=text, markup=True, font_size=dp(18),
                                  bold=True, color=TEXT,
                                  halign='center', valign='middle',
                                  size_hint=(1, 1)))

    def _upd(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size


class MoviePosterCard(RelativeLayout):
    """Poster tile: image fills card, title overlaid at bottom."""
    def __init__(self, movie, on_tap=None, show_lb_badge=False, **kwargs):
        on_plex = movie.get('on_plex', movie.get('source') == 'plex')
        on_lb   = movie.get('on_lb',   movie.get('source') == 'letterboxd')
        if on_plex and on_lb:
            badge_text, badge_color = "Plex + LB", GREEN
        elif on_lb and not on_plex:
            badge_text, badge_color = "LB Only", GOLD
        elif on_plex and not on_lb:
            badge_text, badge_color = "Plex", ACCENT2
        else:
            badge_text, badge_color = ("LB · Not on Plex" if show_lb_badge else None), GOLD

        super().__init__(size_hint=(None, None),
                         size=(dp(120), dp(200)), **kwargs)
        self._on_tap     = on_tap
        self._movie      = movie
        self._touch_down = None

        # In RelativeLayout, canvas coords are relative to self — (0,0) = our bottom-left
        with self.canvas.before:
            Color(*movie.get('poster_color', CARD))
            self._bg = Rectangle(pos=(0, 0), size=self.size)
        self.bind(size=self._upd_bg)

        url = movie.get('poster_url')
        if url:
            self.add_widget(AsyncImage(
                source=url, allow_stretch=True, keep_ratio=False,
                size_hint=(1, 1), pos_hint={'x': 0, 'y': 0}))

        overlay_h = dp(58) if badge_text else dp(44)
        overlay = BoxLayout(orientation='vertical',
                            size_hint=(1, None), height=overlay_h,
                            pos_hint={'x': 0, 'y': 0},
                            padding=[dp(4), dp(4)])
        with overlay.canvas.before:
            Color(0, 0, 0, 0.65)
            self._ov = Rectangle(pos=(0, 0), size=overlay.size)
        overlay.bind(size=self._upd_ov)

        title_lbl = Label(text=movie['title'], font_size=dp(9), color=TEXT,
                          halign='center', valign='middle',
                          size_hint=(1, None), height=dp(32))
        title_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        overlay.add_widget(title_lbl)

        if badge_text:
            badge = Label(text=badge_text, font_size=dp(7), color=badge_color,
                          size_hint=(1, None), height=dp(12),
                          halign='center', valign='middle')
            overlay.add_widget(badge)

        self.add_widget(overlay)

    def _upd_bg(self, *_):
        self._bg.size = self.size

    def _upd_ov(self, w, size):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(0, 0, 0, 0.65)
            Rectangle(pos=(0, 0), size=size)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._touch_down = (touch.x, touch.y)
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self._on_tap and self._touch_down:
            dx = abs(touch.x - self._touch_down[0])
            dy = abs(touch.y - self._touch_down[1])
            inside = self.collide_point(*touch.pos)
            self._touch_down = None
            if dx < dp(8) and dy < dp(8) and inside:
                self._on_tap(self._movie)
                return True
        else:
            self._touch_down = None
        return super().on_touch_up(touch)


class FilterChip(ToggleButton):
    def __init__(self, text, **kwargs):
        super().__init__(text=text, **kwargs)
        self.size_hint = (None, None)
        self.size = (dp(90), dp(30))
        self.font_size = dp(11)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = CARD
        self.color = SUBTEXT
        self.bind(state=self._on_state)

    def _on_state(self, *_):
        if self.state == 'down':
            self.background_color = ACCENT
            self.color = TEXT
        else:
            self.background_color = CARD
            self.color = SUBTEXT

# ── Loading Screen ────────────────────────────────────────────────────────────
class LoadingScreen(Screen):
    """Shown on launch when credentials exist — preloads all data before continuing."""
    def __init__(self, on_ready, **kwargs):
        super().__init__(**kwargs)
        self._on_ready   = on_ready
        self._done_count = [0]
        self._total      = [0]
        self._lb_stats   = {}
        self._msgs       = []
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical', padding=dp(32), spacing=dp(20))
        with root.canvas.before:
            Color(*BG)
            Rectangle(pos=root.pos, size=root.size)
        root.add_widget(Widget(size_hint_y=0.25))

        title = Label(text="[b]CineQueue[/b]", markup=True,
                      font_size=dp(36), color=ACCENT,
                      size_hint_y=None, height=dp(54),
                      halign='center', valign='middle')
        title.bind(size=lambda w, s: setattr(w, 'text_size', s))
        root.add_widget(title)

        sub = Label(text="Loading your movies…", font_size=dp(13), color=SUBTEXT,
                    size_hint_y=None, height=dp(30),
                    halign='center', valign='middle')
        sub.bind(size=lambda w, s: setattr(w, 'text_size', s))
        root.add_widget(sub)

        self._status_lbl = Label(text="", font_size=dp(11), color=GOLD,
                                  size_hint_y=None, height=dp(72),
                                  halign='center', valign='top')
        self._status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        root.add_widget(self._status_lbl)

        root.add_widget(Widget())
        self.add_widget(root)

    def _log(self, msg):
        #print(f"[Loading] {msg}")
        self._msgs.append(msg)
        self._status_lbl.text = '\n'.join(self._msgs[-4:])

    def start(self, plex_url, plex_token, lb_username, tmdb_key, cached_plex=None, cached_lb=None):
        """Fetch fresh data. If cached_* lists are provided, only TMDB-enrich new movies."""
        self._tmdb_key    = tmdb_key
        self._cached_plex = cached_plex or []
        self._cached_lb   = cached_lb   or []
        sources = []
        if plex_url and plex_token:
            sources.append('plex')
        if lb_username:
            sources.append('lb')
        self._total[0] = len(sources)

        if not sources:
            Clock.schedule_once(lambda dt: self._finish(), 0.2)
            return

        if 'plex' in sources:
            self._log("Syncing Plex…" if self._cached_plex else "Connecting to Plex…")
            fetch_plex_async(
                plex_url, plex_token,
                on_done=self._on_plex_done,
                on_error=self._on_plex_err)

        if 'lb' in sources:
            self._log("Syncing Letterboxd…" if self._cached_lb else "Loading Letterboxd watchlist…")
            fetch_lb_async(
                lb_username,
                on_done=self._on_lb_done,
                on_error=self._on_lb_err)
            fetch_lb_stats_async(
                lb_username,
                on_done=self._on_lb_stats_done,
                on_error=lambda e: None)

    def _on_plex_done(self, movies):
        global _plex_movies
        merged, new = MovieCache.merge(self._cached_plex, movies)
        _plex_movies = merged
        self._new_plex = new
        self._log(f"Plex: {len(merged)} movies (+{len(new)} new)")
        self._check_done()

    def _on_plex_err(self, e):
        self._log(f"Plex error: {e}")
        # Keep cached data on error
        if self._cached_plex:
            self._new_plex = []
            self._log("Using cached Plex data")
        self._check_done()

    def _on_lb_done(self, movies):
        global _lb_movies
        merged, new = MovieCache.merge(self._cached_lb, movies)
        _lb_movies = merged
        self._new_lb = new
        self._log(f"Letterboxd: {len(merged)} movies (+{len(new)} new)")
        self._check_done()

    def _on_lb_err(self, e):
        self._log(f"LB error: {e}")
        if self._cached_lb:
            self._new_lb = []
            self._log("Using cached Letterboxd data")
        self._check_done()

    def _on_lb_stats_done(self, stats):
        global _lb_stats
        _lb_stats = stats
        #print(f"[Loading] LB stats: {stats}")

    def _check_done(self):
        self._done_count[0] += 1
        if self._done_count[0] >= self._total[0]:
            _find_intersection(_plex_movies, _lb_movies)
            tmdb_key  = getattr(self, '_tmdb_key', '')
            new_plex  = getattr(self, '_new_plex', _plex_movies)
            new_lb    = getattr(self, '_new_lb',   _lb_movies)
            new_movies = new_plex + new_lb
            if tmdb_key and new_movies:
                self._log(f"Enriching {len(new_movies)} new movies via TMDB…")
                fetch_tmdb_enrich_async(new_movies, tmdb_key, self._on_tmdb_done)
            else:
                if tmdb_key and not new_movies:
                    self._log("All movies up to date.")
                self._save_and_finish()

    def _on_tmdb_done(self):
        self._log("Ready!")
        self._save_and_finish()

    def _save_and_finish(self):
        MovieCache.save(_plex_movies, _lb_movies, _lb_stats)
        self._finish()

    def _finish(self):
        _notify_refresh()
        Clock.schedule_once(lambda dt: self._on_ready(), 0.4)


# ── Watch Screen ──────────────────────────────────────────────────────────────
class WatchScreen(Screen):
    SORT_OPTIONS = ["Plex Date", "LB Date", "Unique", "Foreign/EN", "Random", "Runtime"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_count = 3
        self.active_sorts = {"Random"}
        self._count_lbl = None
        # Card pools: keyed by movie title. Built once per movie, reused on every
        # sort/count change so AsyncImage widgets are never destroyed and recreated.
        self._watch_pool    = {}   # title → MoviePosterCard (plex movies)
        self._rec_pool      = {}   # title → MoviePosterCard (plex + lb movies)
        self._pool_plex_set = set()
        self._pool_lb_set   = set()
        self._build_ui()
        _refresh_cbs.append(lambda: Clock.schedule_once(
            lambda dt: self._refresh_movies(), 0))

    def _build_ui(self):
        root = BoxLayout(orientation='vertical')

        header = BoxLayout(size_hint_y=None, height=dp(50),
                           padding=[dp(12), dp(8)])
        with header.canvas.before:
            Color(0.10, 0.10, 0.14, 1)
            self._hdr_rect = Rectangle(pos=header.pos, size=header.size)
        header.bind(pos=self._upd_hdr, size=self._upd_hdr)

        title = Label(text="CineQueue", font_size=dp(20), bold=True,
                      color=ACCENT, size_hint_x=0.6, halign='left',
                      valign='middle')
        title.bind(size=lambda w, s: setattr(w, 'text_size', s))
        plex_dot = Label(text="● PLEX",
                         font_size=dp(10), color=GREEN,
                         size_hint_x=0.4, halign='right', valign='middle')
        plex_dot.bind(size=lambda w, s: setattr(w, 'text_size', s))
        header.add_widget(title)
        header.add_widget(plex_dot)
        root.add_widget(header)

        # Status bar
        self._status_lbl = Label(text="", font_size=dp(10), color=GOLD,
                                 size_hint_y=None, height=dp(0),
                                 halign='center', valign='middle')
        self._status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        root.add_widget(self._status_lbl)

        scroll = ScrollView()
        inner = BoxLayout(orientation='vertical', size_hint_y=None,
                          spacing=dp(8), padding=[dp(8), dp(8)])
        inner.bind(minimum_height=inner.setter('height'))

        # Count selector — [−]  N  [+]
        inner.add_widget(SectionLabel(text="HOW MANY TO SUGGEST"))
        count_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(0))
        minus_btn = Button(text="−", size_hint_x=None, width=dp(52),
                           background_normal="", background_color=CARD,
                           color=TEXT, font_size=dp(22), bold=True)
        self._count_lbl = Label(text=str(self.selected_count),
                                font_size=dp(24), bold=True, color=TEXT,
                                halign='center', valign='middle')
        plus_btn = Button(text="+", size_hint_x=None, width=dp(52),
                          background_normal="", background_color=CARD,
                          color=TEXT, font_size=dp(22), bold=True)
        minus_btn.bind(on_press=self._decrement_count)
        plus_btn.bind(on_press=self._increment_count)
        count_row.add_widget(Widget())
        count_row.add_widget(minus_btn)
        count_row.add_widget(self._count_lbl)
        count_row.add_widget(plus_btn)
        count_row.add_widget(Widget())
        inner.add_widget(count_row)

        # Sort chips
        inner.add_widget(SectionLabel(text="SORT / FILTER BY"))
        sort_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(6))
        self._sort_chips = []
        for opt in self.SORT_OPTIONS:
            chip = FilterChip(text=opt,
                              state='down' if opt in self.active_sorts else 'normal')
            chip.bind(on_press=lambda c=chip, o=opt: self._toggle_sort(c, o))
            sort_row.add_widget(chip)
            self._sort_chips.append(chip)
        inner.add_widget(sort_row)

        # Watch Now
        inner.add_widget(SectionLabel(text="WATCH NOW  (on Plex)"))
        self._watch_container = BoxLayout(orientation='horizontal',
                                          size_hint=(None, None),
                                          height=dp(210), width=dp(360),
                                          spacing=dp(8))
        ws = ScrollView(size_hint_y=None, height=dp(210), do_scroll_y=False,
                        do_scroll_x=True)
        ws.add_widget(self._watch_container)
        inner.add_widget(ws)

        # Recommended
        inner.add_widget(SectionLabel(text="RECOMMENDED  (Plex + Letterboxd)"))
        self._rec_container = BoxLayout(orientation='horizontal',
                                        size_hint=(None, None),
                                        height=dp(210), width=dp(360),
                                        spacing=dp(8))
        rs = ScrollView(size_hint_y=None, height=dp(210), do_scroll_y=False,
                        do_scroll_x=True)
        rs.add_widget(self._rec_container)
        inner.add_widget(rs)

        # Download stub
        dl_box = BoxLayout(orientation='vertical', size_hint_y=None,
                           height=dp(100), spacing=dp(4), padding=[dp(8), dp(8)])
        with dl_box.canvas.before:
            Color(*CARD)
            self._dl_rect = RoundedRectangle(pos=dl_box.pos, size=dl_box.size,
                                              radius=[dp(10)])
        dl_box.bind(pos=lambda w, _: self._upd_dl(w),
                    size=lambda w, _: self._upd_dl(w))
        dl_lbl = Label(text="[b]Download Pipeline[/b]  (Prowlarr + qBittorrent)",
                       markup=True, font_size=dp(12), color=GOLD,
                       size_hint_y=None, height=dp(20),
                       halign='left', valign='middle')
        dl_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        dl_sub = Label(
            text="This feature is not yet available. Configure Prowlarr & qBittorrent\nin Settings to enable automated downloads.",
            font_size=dp(10), color=SUBTEXT, size_hint_y=None, height=dp(36),
            halign='left', valign='top')
        dl_sub.bind(size=lambda w, s: setattr(w, 'text_size', s))
        dl_btn = Button(text="Download  (Coming Soon)", font_size=dp(11),
                        background_normal="", background_color=(0.3, 0.3, 0.4, 1),
                        color=SUBTEXT, size_hint_y=None, height=dp(30), disabled=True)
        dl_box.add_widget(dl_lbl)
        dl_box.add_widget(dl_sub)
        dl_box.add_widget(dl_btn)
        inner.add_widget(dl_box)

        scroll.add_widget(inner)
        root.add_widget(scroll)
        self.add_widget(root)
        self._refresh_movies()

    def _upd_hdr(self, w, _):
        self._hdr_rect.pos = w.pos
        self._hdr_rect.size = w.size

    def _upd_dl(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*CARD)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(10)])

    def set_status(self, msg, color=GOLD):
        self._status_lbl.text = msg
        self._status_lbl.color = color
        self._status_lbl.height = dp(20) if msg else dp(0)

    def _decrement_count(self, *_):
        if self.selected_count > 1:
            self.selected_count -= 1
            self._count_lbl.text = str(self.selected_count)
            self._refresh_movies()

    def _increment_count(self, *_):
        if self.selected_count < 5:
            self.selected_count += 1
            self._count_lbl.text = str(self.selected_count)
            self._refresh_movies()

    def _toggle_sort(self, chip, opt):
        if opt in self.active_sorts:
            self.active_sorts.discard(opt)
        else:
            self.active_sorts.add(opt)
        self._refresh_movies()

    def _sort_movies(self, movies):
        result = list(movies)
        if "Random" in self.active_sorts:
            random.shuffle(result)
        elif "Plex Date" in self.active_sorts:
            result.sort(key=lambda m: m.get("plex_added", ""), reverse=True)
        elif "LB Date" in self.active_sorts:
            result.sort(key=lambda m: m.get("lb_added", m.get("plex_added", "")),
                        reverse=True)
        elif "Foreign/EN" in self.active_sorts:
            result.sort(key=lambda m: 0 if m.get("country") != "US" else 1)
        elif "Unique" in self.active_sorts:
            seen, unique = {}, []
            for m in result:
                g = m.get("genre")
                if g not in seen:
                    seen[g] = True
                    unique.append(m)
            result = unique
        elif "Runtime" in self.active_sorts:
            result.sort(key=lambda m: m.get("runtime", 9999))
        return result[:self.selected_count]

    def _refresh_movies(self):
        # ── Rebuild card pool only when the underlying movie lists change ──────
        # This is the key optimisation: AsyncImage widgets are created once and
        # reused. Removing a card from clear_widgets() and re-adding it does NOT
        # re-trigger image loading — the texture is already loaded on the widget.
        plex_set = {m['title'] for m in _plex_movies}
        lb_set   = {m['title'] for m in _lb_movies}

        if plex_set != self._pool_plex_set or lb_set != self._pool_lb_set:
            # Add cards for new movies
            for m in _plex_movies:
                if m['title'] not in self._watch_pool:
                    self._watch_pool[m['title']] = MoviePosterCard(
                        m, on_tap=self._show_detail)
            for m in _plex_movies + _lb_movies:
                if m['title'] not in self._rec_pool:
                    is_plex = m.get('source') == 'plex' or m.get('on_plex', False)
                    self._rec_pool[m['title']] = MoviePosterCard(
                        m, on_tap=self._show_detail, show_lb_badge=not is_plex)
            # Prune cards for movies no longer in the lists
            for gone in self._pool_plex_set - plex_set:
                self._watch_pool.pop(gone, None)
            for gone in (self._pool_plex_set | self._pool_lb_set) - (plex_set | lb_set):
                self._rec_pool.pop(gone, None)
            self._pool_plex_set = plex_set
            self._pool_lb_set   = lb_set

        # ── Repopulate containers from pool (no new widgets created) ──────────
        self._watch_container.clear_widgets()
        self._rec_container.clear_widgets()

        watch = self._sort_movies(_plex_movies)
        if not watch:
            empty = Label(text="Nothing to show here",
                          font_size=dp(13), color=SUBTEXT,
                          halign='center', valign='middle')
            empty.bind(size=lambda w, s: setattr(w, 'text_size', s))
            self._watch_container.add_widget(empty)
        else:
            for m in watch:
                card = self._watch_pool.get(m['title'])
                if card:
                    self._watch_container.add_widget(card)
        self._watch_container.width = max(
            dp(130) * max(len(watch), 1) + dp(8) * max(len(watch)-1, 0), Window.width)

        rec = self._sort_movies(_plex_movies + _lb_movies)
        if not rec:
            empty = Label(text="Nothing to show here",
                          font_size=dp(13), color=SUBTEXT,
                          halign='center', valign='middle')
            empty.bind(size=lambda w, s: setattr(w, 'text_size', s))
            self._rec_container.add_widget(empty)
        else:
            for m in rec:
                card = self._rec_pool.get(m['title'])
                if card:
                    self._rec_container.add_widget(card)
        self._rec_container.width = max(
            dp(130) * max(len(rec), 1) + dp(8) * max(len(rec)-1, 0), Window.width)

    def _show_detail(self, movie):
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(16))
        with content.canvas.before:
            Color(*BG)
            Rectangle(pos=content.pos, size=content.size)

        poster = PosterWidget(movie, h=dp(160))
        content.add_widget(poster)

        for line in [
            f"[b]{movie['title']}[/b] ({movie['year']})",
            f"Director: {movie.get('director','N/A')}",
            f"Genre: {movie.get('genre','?')}  |  Country: {movie.get('country','?')}",
            f"Rating: {movie['rating']}  |  Runtime: {movie.get('runtime','?')} min",
        ]:
            lbl = Label(text=line, markup=True, font_size=dp(12), color=TEXT,
                        halign='left', valign='middle',
                        size_hint_y=None, height=dp(22))
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            content.add_widget(lbl)

        on_plex = movie.get('source') == 'plex' or movie.get('on_plex', False)

        if on_plex:
            watch_btn = Button(text="▶  Watch on Plex",
                               size_hint_y=None, height=dp(40),
                               background_normal="", background_color=GREEN,
                               color=TEXT, font_size=dp(13), bold=True)
            content.add_widget(watch_btn)
        else:
            dl_btn = Button(text="▼  Queue Download",
                            size_hint_y=None, height=dp(40),
                            background_normal="", background_color=ACCENT2,
                            color=TEXT, font_size=dp(13), bold=True)
            avail_lbl = Label(text="Not available on Plex — queue via Prowlarr",
                              font_size=dp(10), color=GOLD,
                              size_hint_y=None, height=dp(18),
                              halign='center', valign='middle')
            avail_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            content.add_widget(avail_lbl)
            content.add_widget(dl_btn)

        close_btn = Button(text="Close", size_hint_y=None, height=dp(36),
                           background_normal="", background_color=CARD,
                           color=SUBTEXT, font_size=dp(12))
        content.add_widget(close_btn)

        popup = Popup(title=movie['title'], content=content,
                      size_hint=(0.9, 0.82),
                      background_color=(0.10, 0.10, 0.14, 1), title_color=TEXT)

        if on_plex:
            def _open_plex(btn, m=movie):
                plex_url = Settings.get('plex_url', '').rstrip('/')
                if plex_url:
                    webbrowser.open(plex_url + '/web/index.html')
                popup.dismiss()
            watch_btn.bind(on_press=_open_plex)
        else:
            def _queue_dl(btn, m=movie):
                entry = DownloadQueue.add(m)
                if entry:
                    DownloadQueue.search_and_grab(entry['id'], lambda e: None)
                    popup.dismiss()
                    # Switch to Downloads tab
                    app = App.get_running_app()
                    if app and hasattr(app, '_sm'):
                        app._sm.current = 'downloads'
                else:
                    dl_btn.text = "Already queued"
                    dl_btn.background_color = SUBTEXT
            dl_btn.bind(on_press=_queue_dl)

        close_btn.bind(on_press=popup.dismiss)
        popup.open()


# ── Recommend Screen ──────────────────────────────────────────────────────────
class RecommendScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._all          = []
        self._idx          = 0
        self._current_card = None
        self._animating    = False
        self._touch_start  = None
        self._build_ui()
        self._reload()
        _refresh_cbs.append(lambda: Clock.schedule_once(
            lambda dt: self._reload(), 0))

    def _reload(self):
        self._all = list(_plex_movies + _lb_movies)
        random.shuffle(self._all)
        self._idx       = 0
        self._animating = False
        if hasattr(self, '_card_area'):
            self._show_card()

    def _build_ui(self):
        root = FloatLayout()
        with root.canvas.before:
            Color(*BG)
            self._bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._upd_bg, size=self._upd_bg)

        root.add_widget(Label(
            text="[b]Swipe to Decide[/b]", markup=True,
            font_size=dp(18), color=TEXT,
            pos_hint={'center_x': 0.5, 'top': 0.97},
            size_hint=(0.9, None), height=dp(36)))

        root.add_widget(Label(
            text=f"{E('➡')} Watch    {E('⬅')} Skip    {E('⬇')} Not Interested",
            markup=True, font_size=dp(10), color=SUBTEXT,
            pos_hint={'center_x': 0.5, 'top': 0.92},
            size_hint=(0.9, None), height=dp(20)))

        self._card_area = FloatLayout(
            size_hint=(1, None), height=dp(460),
            pos_hint={'center_x': 0.5, 'center_y': 0.55})
        root.add_widget(self._card_area)

        btn_row = BoxLayout(size_hint=(None, None), size=(dp(280), dp(50)),
                            pos_hint={'center_x': 0.5, 'y': 0.04},
                            spacing=dp(12))
        skip_btn = Button(text=f"{E('❌')} Skip", markup=True,
                          size_hint_x=None, width=dp(80),
                          background_normal="",
                          background_color=(0.35, 0.15, 0.15, 1),
                          color=TEXT, font_size=dp(13))
        nope_btn = Button(text=f"{E('👎')} Nope", markup=True,
                          size_hint_x=None, width=dp(80),
                          background_normal="",
                          background_color=(0.25, 0.20, 0.10, 1),
                          color=TEXT, font_size=dp(12))
        watch_btn = Button(text=f"{E('✅')} Watch", markup=True,
                           size_hint_x=None, width=dp(100),
                           background_normal="", background_color=GREEN,
                           color=TEXT, font_size=dp(13), bold=True)
        skip_btn.bind(on_press=lambda *_: self._animate('skip'))
        nope_btn.bind(on_press=lambda *_: self._animate('not_interested'))
        watch_btn.bind(on_press=lambda *_: self._animate('accept'))
        btn_row.add_widget(skip_btn)
        btn_row.add_widget(nope_btn)
        btn_row.add_widget(watch_btn)
        root.add_widget(btn_row)

        self.add_widget(root)
        self._show_card()

    def _upd_bg(self, w, _):
        self._bg_rect.pos  = w.pos
        self._bg_rect.size = w.size

    def _show_card(self):
        self._card_area.clear_widgets()
        self._current_card = None
        if self._idx >= len(self._all):
            self._card_area.add_widget(Label(
                text="No more movies!\nReset to start over.",
                font_size=dp(16), color=SUBTEXT, halign='center',
                pos_hint={'center_x': 0.5, 'center_y': 0.5},
                size_hint=(0.8, None), height=dp(60)))
            return
        movie = self._all[self._idx]
        card  = self._make_card(movie)
        self._card_area.add_widget(card)
        self._current_card = card

    def _make_card(self, movie):
        card = BoxLayout(orientation='vertical',
                         size_hint=(None, None), size=(dp(280), dp(400)),
                         pos_hint={'center_x': 0.5, 'center_y': 0.5},
                         spacing=0, padding=0)
        with card.canvas.before:
            Color(*movie.get('poster_color', CARD))
            self._card_bg = RoundedRectangle(pos=card.pos, size=card.size,
                                              radius=[dp(16)])
        card.bind(pos=self._upd_card_bg, size=self._upd_card_bg)
        card._movie = movie

        poster = PosterWidget(movie, h=dp(240))
        card.add_widget(poster)
        # no extra label on top — PosterWidget handles country/rating fallback

        info = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(160),
                         padding=[dp(16), dp(10)], spacing=dp(6))
        with info.canvas.before:
            Color(0.0, 0.0, 0.0, 0.55)
            self._info_bg = RoundedRectangle(pos=info.pos, size=info.size,
                                              radius=[dp(0), dp(0), dp(16), dp(16)])
        info.bind(pos=self._upd_info_bg, size=self._upd_info_bg)

        for text, color, size in [
            (f"[b]{movie['title']}[/b]", TEXT, dp(15)),
            (f"{movie['year']} · {movie.get('genre','?')} · {movie.get('runtime','?')} min",
             SUBTEXT, dp(11)),
            (f"Dir: {movie.get('director','?')}", SUBTEXT, dp(10)),
        ]:
            lbl = Label(text=text, markup=True, font_size=size, color=color,
                        halign='left', valign='middle',
                        size_hint_y=None, height=dp(20))
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            info.add_widget(lbl)

        on_plex = movie.get('source') == 'plex' or movie.get('on_plex', False)
        avail_text  = "● Available on Plex" if on_plex else "● Not on Plex"
        avail_color = GREEN if on_plex else GOLD
        avail = Label(text=avail_text, font_size=dp(10), color=avail_color,
                      halign='left', valign='middle',
                      size_hint_y=None, height=dp(18))
        avail.bind(size=lambda w, s: setattr(w, 'text_size', s))
        info.add_widget(avail)

        if not on_plex:
            dl_btn = Button(text="▼  Queue Download", font_size=dp(10),
                            size_hint_y=None, height=dp(28),
                            background_normal="", background_color=ACCENT2,
                            color=TEXT)
            def _queue(btn, m=movie):
                entry = DownloadQueue.add(m)
                if entry:
                    DownloadQueue.search_and_grab(entry['id'], lambda e: None)
                    btn.text = "● Queued"
                    btn.background_color = SUBTEXT
                else:
                    btn.text = "Already queued"
                    btn.background_color = SUBTEXT
            dl_btn.bind(on_press=_queue)
            info.add_widget(dl_btn)

        card.add_widget(info)
        return card

    def _upd_card_bg(self, w, _):
        movie = getattr(w, '_movie', None)
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*movie.get('poster_color', CARD) if movie else CARD)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(16)])

    def _upd_info_bg(self, w, _):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(0.0, 0.0, 0.0, 0.55)
            RoundedRectangle(pos=w.pos, size=w.size,
                             radius=[dp(0), dp(0), dp(16), dp(16)])

    # ── Touch / Swipe ─────────────────────────────────────────────────────────
    def on_touch_down(self, touch):
        if self._current_card and self._current_card.collide_point(*touch.pos):
            self._touch_start = (touch.x, touch.y)
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        if self._touch_start and not self._animating:
            dx = touch.x - self._touch_start[0]
            dy = touch.y - self._touch_start[1]
            self._touch_start = None
            if abs(dx) > dp(50) or abs(dy) > dp(50):
                if abs(dx) >= abs(dy):
                    self._animate('accept' if dx > 0 else 'skip')
                elif dy < -dp(50):   # finger moved down (y decreases in Kivy)
                    self._animate('not_interested')
                return True
        self._touch_start = None
        return super().on_touch_up(touch)

    def _animate(self, action):
        if self._animating or self._idx >= len(self._all):
            return
        card = self._current_card
        if card is None:
            return
        self._animating = True

        # Pin position, remove pos_hint so Animation drives x/y
        cur_x, cur_y = card.x, card.y
        card.pos_hint  = {}
        card.pos       = (cur_x, cur_y)

        movie = self._all[self._idx]

        if action == 'accept':
            anim_kw = dict(x=Window.width + dp(300), opacity=0)
            msg     = f"Added '{movie['title']}' to watch list!"
        elif action == 'skip':
            anim_kw = dict(x=-card.width - dp(300), opacity=0)
            msg     = None
        else:  # not_interested
            anim_kw = dict(y=-card.height - dp(300), opacity=0)
            msg     = None

        saved_msg = msg

        def on_done(anim, widget):
            self._animating = False
            self._idx += 1
            self._show_card()
            if saved_msg:
                self._show_toast(saved_msg)

        anim = Animation(duration=0.3, transition='out_cubic', **anim_kw)
        anim.bind(on_complete=on_done)
        anim.start(card)

    def _show_toast(self, msg):
        popup = Popup(
            title="",
            content=Label(text=msg, font_size=dp(12), color=TEXT, halign='center'),
            size_hint=(0.85, None), height=dp(80),
            background_color=(0.15, 0.15, 0.20, 1),
            title_color=TEXT, auto_dismiss=True)
        popup.open()
        Clock.schedule_once(popup.dismiss, 2)


# ── Analytics Screen ──────────────────────────────────────────────────────────
class AnalyticsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build_ui()
        _refresh_cbs.append(lambda: Clock.schedule_once(
            lambda dt: self._rebuild(), 0))

    def _rebuild(self):
        self.clear_widgets()
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical')
        with root.canvas.before:
            Color(*BG)
            Rectangle(pos=root.pos, size=root.size)

        root.add_widget(Label(text="[b]Analytics[/b]", markup=True,
                              font_size=dp(20), color=ACCENT,
                              size_hint_y=None, height=dp(50)))

        scroll = ScrollView()
        inner  = BoxLayout(orientation='vertical', size_hint_y=None,
                           spacing=dp(12), padding=[dp(12), dp(8)])
        inner.bind(minimum_height=inner.setter('height'))

        total_w  = len(MOCK_WATCHED)
        total_uw = len(_plex_movies) + len(_lb_movies)
        total    = total_w + total_uw
        pct      = int(total_w / total * 100) if total else 0

        current_year = str(datetime.now().year)
        watchlist_titles = {m['title'] for m in _lb_movies + _plex_movies}
        watched_titles   = {e['title'] for e in MOCK_WATCHED}
        from_watchlist_this_year = sum(
            1 for e in MOCK_WATCHED
            if e.get('date', '').startswith(current_year)
            and e['title'] in watchlist_titles)
        added_watchlist_this_year = sum(
            1 for m in _lb_movies + _plex_movies
            if (m.get('lb_added') or m.get('plex_added', '')).startswith(current_year))
        watched_outside_watchlist = sum(
            1 for e in MOCK_WATCHED if e['title'] not in watchlist_titles)

        # Live LB stats (scraped from profile)
        lb_total_watched   = _lb_stats.get('total_films', None)
        lb_watched_yr      = _lb_stats.get('watched_this_year', None)
        on_both            = sum(1 for m in _plex_movies if m.get('on_lb'))

        lb_total_str = str(lb_total_watched) if lb_total_watched is not None else f"{total_w}*"
        lb_yr_str    = str(lb_watched_yr)   if lb_watched_yr   is not None else f"{from_watchlist_this_year}*"
        stats = [
            ("LB Watched",    lb_total_str,          GREEN),
            (f"This Year",    lb_yr_str,             ACCENT2),
            ("On Plex",       str(len(_plex_movies)), ACCENT2),
            ("Plex + LB",     str(on_both),           GOLD),
        ]
        stat_row = BoxLayout(size_hint_y=None, height=dp(80), spacing=dp(8))
        for label, val, color in stats:
            card = BoxLayout(orientation='vertical', spacing=dp(4), padding=dp(8))
            with card.canvas.before:
                Color(*CARD)
                RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(10)])
            card.bind(pos=lambda w, _: self._redraw(w),
                      size=lambda w, _: self._redraw(w))
            vl = Label(text=f"[b]{val}[/b]", markup=True,
                       font_size=dp(22), color=color,
                       halign='center', valign='middle')
            vl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            ll = Label(text=label, font_size=dp(10), color=SUBTEXT,
                       halign='center', valign='middle')
            ll.bind(size=lambda w, s: setattr(w, 'text_size', s))
            card.add_widget(vl)
            card.add_widget(ll)
            stat_row.add_widget(card)
        inner.add_widget(stat_row)

        # Year stats row
        inner.add_widget(SectionLabel(text=f"THIS YEAR  ({current_year})"))
        year_stats = [
            (f"Watched from\nWatchlist", str(from_watchlist_this_year),  ACCENT2),
            (f"Added to\nWatchlist",     str(added_watchlist_this_year), GOLD),
            (f"Watched\nOutside List",   str(watched_outside_watchlist), GREEN),
        ]
        year_row = BoxLayout(size_hint_y=None, height=dp(80), spacing=dp(8))
        for label, val, color in year_stats:
            card = BoxLayout(orientation='vertical', spacing=dp(4), padding=dp(8))
            with card.canvas.before:
                Color(*CARD)
                RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(10)])
            card.bind(pos=lambda w, _: self._redraw(w),
                      size=lambda w, _: self._redraw(w))
            vl = Label(text=f"[b]{val}[/b]", markup=True,
                       font_size=dp(22), color=color,
                       halign='center', valign='middle')
            vl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            ll = Label(text=label, font_size=dp(9), color=SUBTEXT,
                       halign='center', valign='middle')
            ll.bind(size=lambda w, s: setattr(w, 'text_size', s))
            card.add_widget(vl)
            card.add_widget(ll)
            year_row.add_widget(card)
        inner.add_widget(year_row)

        # ── Watch Progress ────────────────────────────────────────────────────
        lb_watchlist_total = len(_lb_movies)
        lb_watched_count   = _lb_stats.get('total_films', total_w)
        lb_pct = int(lb_watched_count / (lb_watched_count + lb_watchlist_total) * 100) \
                 if (lb_watched_count + lb_watchlist_total) else 0

        plex_total   = len(_plex_movies)
        plex_watched = sum(1 for e in MOCK_WATCHED
                           if any(m['title'] == e['title'] for m in _plex_movies))
        plex_pct = int(plex_watched / (plex_watched + plex_total) * 100) \
                   if (plex_watched + plex_total) else 0

        overlap      = sum(1 for m in _plex_movies if m.get('on_lb'))
        agg_total    = total_w + total_uw
        agg_pct      = int(total_w / agg_total * 100) if agg_total else 0

        inner.add_widget(SectionLabel(text="WATCH PROGRESS"))

        for bar_label, bar_pct, bar_color in [
            (f"Letterboxd  ({lb_pct}%)",   lb_pct,  ACCENT2),
            (f"Plex  ({plex_pct}%)",        plex_pct, GREEN),
            (f"Aggregated  ({agg_pct}%)",   agg_pct, GOLD),
        ]:
            lbl = Label(text=bar_label, font_size=dp(10), color=SUBTEXT,
                        size_hint_y=None, height=dp(16), halign='left', valign='middle')
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            inner.add_widget(lbl)
            prog_box = BoxLayout(size_hint_y=None, height=dp(14))
            with prog_box.canvas.before:
                Color(*CARD)
                RoundedRectangle(pos=prog_box.pos, size=prog_box.size, radius=[dp(7)])
            prog_box.bind(pos=lambda w, _: self._upd_prog(w),
                          size=lambda w, _: self._upd_prog(w))
            fill = BoxLayout(size_hint=(max(bar_pct, 1) / 100, 1))
            fill._fill_color = bar_color
            with fill.canvas.before:
                Color(*bar_color)
                RoundedRectangle(pos=fill.pos, size=fill.size, radius=[dp(7)])
            fill.bind(pos=lambda w, _: self._upd_fill(w),
                      size=lambda w, _: self._upd_fill(w))
            prog_box.add_widget(fill)
            if bar_pct < 100:
                prog_box.add_widget(Widget(size_hint_x=(100 - bar_pct) / 100))
            inner.add_widget(prog_box)

        overlap_lbl = Label(
            text=f"● {overlap} titles on both Plex and Letterboxd watchlist",
            font_size=dp(10), color=GOLD,
            size_hint_y=None, height=dp(20), halign='left', valign='middle')
        overlap_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        inner.add_widget(overlap_lbl)

        inner.add_widget(SectionLabel(text="GENRE BREAKDOWN"))
        genres = {}
        for m in _plex_movies + _lb_movies:
            g = m.get('genre', 'Other')
            genres[g] = genres.get(g, 0) + 1
        for genre, cnt in sorted(genres.items(), key=lambda x: -x[1]):
            row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
            gl = Label(text=genre, font_size=dp(11), color=TEXT,
                       size_hint_x=0.4, halign='left', valign='middle')
            gl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            cl = Label(text=str(cnt), font_size=dp(11), color=SUBTEXT,
                       size_hint_x=0.15, halign='right', valign='middle')
            cl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            row.add_widget(gl)
            row.add_widget(Widget(size_hint_x=0.45))
            row.add_widget(cl)
            inner.add_widget(row)

        inner.add_widget(SectionLabel(text="COUNTRY BREAKDOWN"))
        countries = {}
        for m in _plex_movies + _lb_movies:
            c = m.get('country', '?')
            countries[c] = countries.get(c, 0) + 1
        for country, cnt in sorted(countries.items(), key=lambda x: -x[1]):
            lbl = Label(text=f"[b]{country}[/b]  —  {cnt} titles",
                        markup=True, font_size=dp(12), color=TEXT,
                        size_hint_y=None, height=dp(26),
                        halign='left', valign='middle')
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            inner.add_widget(lbl)

        inner.add_widget(SectionLabel(text="MOST ACTIVE WATCH DAYS"))
        day_counts = {}
        for entry in MOCK_WATCHED:
            try:
                day = datetime.strptime(entry['date'], '%Y-%m-%d').strftime('%A')
                day_counts[day] = day_counts.get(day, 0) + 1
            except Exception:
                pass
        for day, cnt in sorted(day_counts.items(), key=lambda x: -x[1])[:5]:
            lbl = Label(text=f"{day}: {cnt} movies",
                        font_size=dp(12), color=TEXT,
                        size_hint_y=None, height=dp(24),
                        halign='left', valign='middle')
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            inner.add_widget(lbl)

        ratings  = [m['rating'] for m in _plex_movies + _lb_movies if m.get('rating')]
        avg_r    = sum(ratings) / len(ratings) if ratings else 0
        runtimes = [m.get('runtime', 0) for m in _plex_movies + _lb_movies
                    if m.get('runtime')]
        avg_rt   = sum(runtimes) // len(runtimes) if runtimes else 0

        for text, color in [
            (f"Avg Rating: {avg_r:.1f} / 10", GOLD),
            (f"Avg Runtime: {avg_rt} min  ({avg_rt//60}h {avg_rt%60}m)", ACCENT2),
        ]:
            lbl = Label(text=text, markup=True, font_size=dp(13), color=color,
                        size_hint_y=None, height=dp(30),
                        halign='left', valign='middle')
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            inner.add_widget(lbl)

        scroll.add_widget(inner)
        root.add_widget(scroll)
        self.add_widget(root)

    def _upd_prog(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*CARD)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(7)])

    def _upd_fill(self, w):
        w.canvas.before.clear()
        # Inherit color from the fill widget's stored color (set at creation)
        with w.canvas.before:
            Color(*getattr(w, '_fill_color', GREEN))
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(7)])

    def _redraw(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*CARD)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(10)])


# ── Settings Screen ───────────────────────────────────────────────────────────
class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._inputs      = {}   # key -> TextInput
        self._status_lbl  = None
        self._autosave_ev = None
        self._build_ui()

    def on_enter(self):
        self._load_values()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical')
        with root.canvas.before:
            Color(*BG)
            Rectangle(pos=root.pos, size=root.size)

        root.add_widget(Label(text="[b]Settings[/b]", markup=True,
                              font_size=dp(20), color=ACCENT,
                              size_hint_y=None, height=dp(50)))

        self._status_lbl = Label(text="", font_size=dp(10), color=GOLD,
                                 size_hint_y=None, height=dp(24),
                                 halign='center', valign='middle')
        self._status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        root.add_widget(self._status_lbl)

        scroll = ScrollView()
        inner  = BoxLayout(orientation='vertical', size_hint_y=None,
                           spacing=dp(10), padding=[dp(12), dp(8)])
        inner.bind(minimum_height=inner.setter('height'))

        sections = [
            ("PLEX SERVER", [
                ("plex_url",   "Server URL",   "http://192.168.1.100:32400", False),
                ("plex_token", "Plex Token",   "xxxxxxxxxxxxxxxx",           True),
            ]),
            ("LETTERBOXD", [
                ("lb_username", "Username", "@yourusername", False),
            ]),
            ("SYNOLOGY NAS (Services)", [
                ("dsm_port",      "DSM Port",           "5000",                False),
                ("dsm_username",  "NAS Username",       "admin",               False),
                ("dsm_password",  "NAS Password",       "your password",       True),
                ("qbit_project",  "VPN+qBit Project",   "qbittorent-gluetun",  False),
                ("arr_project",   "Arr Stack Project",  "arr-apps",            False),
            ]),
            ("RADARR (Movie Downloads)", [
                ("radarr_url",     "Radarr URL",  "http://192.168.1.100:7878", False),
                ("radarr_api_key", "API Key",     "your-radarr-api-key",       True),
            ]),
            ("PROWLARR (Indexer Proxy — future use)", [
                ("prowlarr_url",     "Prowlarr URL",  "http://192.168.1.100:9696", False),
                ("prowlarr_api_key", "API Key",       "your-prowlarr-api-key",     True),
            ]),
            ("QBITTORRENT (Download Client)", [
                ("qbit_url",      "Web UI URL",   "http://192.168.1.100:8080", False),
                ("qbit_username", "Username",     "admin",                     False),
                ("qbit_password", "Password",     "adminadmin",                True),
            ]),
            ("TMDB (Movie Posters)", [
                ("tmdb_key", "API Key", "Get free key at themoviedb.org", False),
            ]),
            ("STREAMING SERVICES (Coming Soon)", [
                ("netflix_token", "Netflix",    "Not connected", False),
                ("disney_token",  "Disney+",    "Not connected", False),
                ("prime_token",   "Prime Video","Not connected", False),
            ]),
        ]

        for section_title, fields in sections:
            inner.add_widget(SectionLabel(text=section_title))
            for key, field_name, placeholder, is_pass in fields:
                row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
                lbl = Label(text=field_name, font_size=dp(11), color=TEXT,
                            size_hint_x=0.38, halign='left', valign='middle')
                lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
                inp = TextInput(hint_text=placeholder, password=is_pass,
                                size_hint_x=0.62, font_size=dp(11),
                                background_color=CARD, foreground_color=TEXT,
                                cursor_color=ACCENT, multiline=False,
                                padding=[dp(8), dp(8)])
                self._inputs[key] = inp
                row.add_widget(lbl)
                row.add_widget(inp)
                inner.add_widget(row)

        # Services control
        inner.add_widget(SectionLabel(text="SERVICE CONTROL"))
        svc_note = Label(
            text="NAS IP is read from your Plex URL. Requires DSM API Key above.",
            font_size=dp(10), color=SUBTEXT, size_hint_y=None, height=dp(24),
            halign='left', valign='middle')
        svc_note.bind(size=lambda w, s: setattr(w, 'text_size', s))
        inner.add_widget(svc_note)

        self._svc_rows = {}  # service_key -> {'status_lbl': Label}
        for svc_key, svc_label in [('plex',      'Plex Media Server'),
                                    ('qbit_proj', 'VPN + qBittorrent'),
                                    ('arr_proj',  'Prowlarr / Sonarr / Radarr')]:
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(4))
            name_lbl = Label(text=svc_label, font_size=dp(10), color=TEXT,
                             size_hint_x=0.30, halign='left', valign='middle')
            name_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            status_lbl = Label(text="● unknown", font_size=dp(9), color=SUBTEXT,
                               size_hint_x=0.28, halign='left', valign='middle')
            status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            # ▶ play (green), ■ stop (red), ↺ refresh (blue) — all plain BMP symbols
            play_b = Button(text="▶", font_size=dp(14),
                            size_hint_x=None, width=dp(36),
                            background_normal="", background_color=GREEN, color=TEXT)
            stop_b = Button(text="■", font_size=dp(14),
                            size_hint_x=None, width=dp(36),
                            background_normal="", background_color=ACCENT, color=TEXT)
            ref_b  = Button(text="↺", font_size=dp(14),
                            size_hint_x=None, width=dp(36),
                            background_normal="", background_color=CARD, color=ACCENT2)
            _key = svc_key
            play_b.bind(on_press=lambda *_, k=_key: self._svc_action(k, 'start'))
            stop_b.bind(on_press=lambda *_, k=_key: self._svc_action(k, 'stop'))
            ref_b.bind( on_press=lambda *_, k=_key: self._refresh_svc_status_single(k))
            row.add_widget(name_lbl)
            row.add_widget(status_lbl)
            row.add_widget(play_b)
            row.add_widget(stop_b)
            row.add_widget(ref_b)
            inner.add_widget(row)
            self._svc_rows[svc_key] = {'status_lbl': status_lbl}

        refresh_all_btn = Button(text="↺  Refresh All", font_size=dp(11),
                                 size_hint_y=None, height=dp(36),
                                 background_normal="", background_color=CARD,
                                 color=ACCENT2)
        refresh_all_btn.bind(on_press=lambda *_: self._refresh_svc_status())
        inner.add_widget(refresh_all_btn)

        self._svc_status_lbl = Label(
            text="", font_size=dp(10), color=SUBTEXT,
            size_hint_y=None, height=dp(24), halign='left', valign='middle')
        self._svc_status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        inner.add_widget(self._svc_status_lbl)

        save_btn = Button(text="Save & Connect",
                          size_hint_y=None, height=dp(48),
                          background_normal="", background_color=ACCENT2,
                          color=TEXT, font_size=dp(14), bold=True)
        save_btn.bind(on_press=self._save)
        inner.add_widget(save_btn)

        scroll.add_widget(inner)
        root.add_widget(scroll)
        self.add_widget(root)

    def _load_values(self):
        Settings.load()
        for key, inp in self._inputs.items():
            val = Settings.get(key, '')
            if val:
                inp.text = val
            inp.bind(text=self._on_field_change)

    def _on_field_change(self, *_):
        # Debounced auto-save: write to disk 1s after the last keystroke
        if hasattr(self, '_autosave_ev') and self._autosave_ev:
            self._autosave_ev.cancel()
        self._autosave_ev = Clock.schedule_once(self._autosave, 1.0)

    def _autosave(self, *_):
        data = {key: inp.text.strip() for key, inp in self._inputs.items()}
        Settings.save(data)
        self.set_status("Auto-saved", SUBTEXT)

    def set_status(self, msg, color=GOLD):
        if self._status_lbl:
            self._status_lbl.text  = msg
            self._status_lbl.color = color

    def _make_syno_client(self):
        plex_url = Settings.get('plex_url', '')
        nas_ip   = _nas_ip_from_plex_url(plex_url)
        port     = Settings.get('dsm_port', '5000') or '5000'
        username = Settings.get('dsm_username', '')
        password = Settings.get('dsm_password', '')
        if not nas_ip or not username or not password:
            return None, "Set Plex URL + NAS username & password first"
        return SynologyClient(nas_ip, port, username, password), None

    def _set_svc_status(self, key, text, color):
        if key in self._svc_rows:
            self._svc_rows[key]['status_lbl'].text  = text
            self._svc_rows[key]['status_lbl'].color = color

    def _svc_action(self, key, action):
        client, err = self._make_syno_client()
        if not client:
            self._svc_status_lbl.text  = err
            self._svc_status_lbl.color = ACCENT
            return
        self._set_svc_status(key, f"● {action}ing…", GOLD)

        def on_done(result):
            success = result.get('success', False)
            if success:
                self._set_svc_status(key, '● running' if action == 'start' else '● stopped',
                                    GREEN if action == 'start' else SUBTEXT)
            else:
                code = result.get('error', {}).get('code', '?')
                if code == 2104:
                    self._set_svc_status(key, '● build failed', ACCENT)
                    Clock.schedule_once(lambda dt: setattr(
                        self._svc_status_lbl, 'text',
                        'Fix in DSM → Container Manager → Project'), 0)
                    Clock.schedule_once(lambda dt: setattr(
                        self._svc_status_lbl, 'color', GOLD), 0)
                else:
                    self._set_svc_status(key, f'● error {code}', ACCENT)

        def on_error(e):
            msg = "● timed out" if 'timed out' in str(e).lower() or 'timeout' in str(e).lower() else "● error"
            self._set_svc_status(key, msg, ACCENT)
            self._svc_status_lbl.text  = f"{key}: {e}"
            self._svc_status_lbl.color = ACCENT

        if key == 'plex':
            fn = client.plex_start if action == 'start' else client.plex_stop
        elif key == 'qbit_proj':
            proj = Settings.get('qbit_project') or 'qbittorrent-gluetun'
            fn = (lambda p=proj: client.project_start(p)) if action == 'start' \
                 else (lambda p=proj: client.project_stop(p))
        else:  # arr_proj
            proj = Settings.get('arr_project') or 'arr-apps'
            fn = (lambda p=proj: client.project_start(p)) if action == 'start' \
                 else (lambda p=proj: client.project_stop(p))

        syno_action_async(fn, on_done, on_error)

    def _refresh_svc_status(self):
        client, err = self._make_syno_client()
        if not client:
            self._svc_status_lbl.text  = err
            self._svc_status_lbl.color = ACCENT
            return
        for key in ('plex', 'qbit_proj', 'arr_proj'):
            self._set_svc_status(key, "● checking…", GOLD)

        def check_all():
            try:
                status = client.plex_status()
                color  = GREEN if 'running' in status.lower() else SUBTEXT
                Clock.schedule_once(lambda dt, s=status, c=color:
                    self._set_svc_status('plex', f"● {s}", c), 0)
            except Exception:
                Clock.schedule_once(lambda dt:
                    self._set_svc_status('plex', '● unreachable', ACCENT), 0)

            projects  = client._list_projects()
            nas_ip    = client._nas_ip
            qbit_proj = Settings.get('qbit_project') or 'qbittorrent-gluetun'
            arr_proj  = Settings.get('arr_project')  or 'arr-apps'

            for key, proj_name in [('qbit_proj', qbit_proj), ('arr_proj', arr_proj)]:
                try:
                    status = client.project_status_from_list(proj_name, projects, nas_ip=nas_ip)
                    is_up  = status == 'running' or status.startswith('partial')
                    color  = GREEN if status == 'running' else (
                             GOLD  if status.startswith('partial') else SUBTEXT)
                    short  = status if len(status) <= 18 else status[:18] + '…'
                    Clock.schedule_once(
                        lambda dt, k=key, s=short, c=color:
                            self._set_svc_status(k, f"● {s}", c), 0)
                except Exception as e:
                    Clock.schedule_once(
                        lambda dt, k=key, e=str(e): (
                            self._set_svc_status(k, '● error', ACCENT),
                            setattr(self._svc_status_lbl, 'text', f"{k}: {e}"),
                            setattr(self._svc_status_lbl, 'color', ACCENT)), 0)

        threading.Thread(target=check_all, daemon=True).start()

    def _refresh_svc_status_single(self, key):
        client, err = self._make_syno_client()
        if not client:
            self._svc_status_lbl.text  = err
            self._svc_status_lbl.color = ACCENT
            return
        self._set_svc_status(key, "● checking…", GOLD)

        def check_one():
            try:
                if key == 'plex':
                    status = client.plex_status()
                    color  = GREEN if 'running' in status.lower() else SUBTEXT
                    Clock.schedule_once(lambda dt, s=status, c=color:
                        self._set_svc_status('plex', f"● {s}", c), 0)
                else:
                    proj_name = (Settings.get('qbit_project') or 'qbittorrent-gluetun') \
                                if key == 'qbit_proj' else \
                                (Settings.get('arr_project') or 'arr-apps')
                    projects = client._list_projects()
                    nas_ip   = client._nas_ip
                    status   = client.project_status_from_list(proj_name, projects, nas_ip=nas_ip)
                    color    = GREEN if status == 'running' else (
                               GOLD  if status.startswith('partial') else SUBTEXT)
                    short    = status if len(status) <= 18 else status[:18] + '…'
                    Clock.schedule_once(lambda dt, k=key, s=short, c=color:
                        self._set_svc_status(k, f"● {s}", c), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt, k=key:
                    self._set_svc_status(k, '● error', ACCENT), 0)

        threading.Thread(target=check_one, daemon=True).start()

    def _save(self, *_):
        data = {key: inp.text.strip() for key, inp in self._inputs.items()}
        ok   = Settings.save(data)
        self.set_status("Saved!" if ok else "Save failed.", GREEN if ok else ACCENT)

        # Trigger real fetches
        if data.get('plex_url') and data.get('plex_token'):
            self._fetch_plex(data['plex_url'], data['plex_token'])
        if data.get('lb_username'):
            self._fetch_lb(data['lb_username'])
        if data.get('tmdb_key'):
            self._fetch_tmdb_posters(data['tmdb_key'])

    def _fetch_plex(self, url, token):
        self.set_status("Connecting to Plex…")
        def on_done(movies):
            global _plex_movies
            _plex_movies = movies
            self.set_status(f"Plex: {len(movies)} movies loaded", GREEN)
            _notify_refresh()
        def on_err(e):
            self.set_status(f"Plex error: {e}", ACCENT)
        fetch_plex_async(url, token, on_done, on_err)

    def _fetch_lb(self, username):
        self.set_status("Loading Letterboxd watchlist…")
        def on_done(movies):
            global _lb_movies
            _lb_movies = movies
            self.set_status(f"Letterboxd: {len(movies)} movies loaded", GREEN)
            _notify_refresh()
        def on_err(e):
            self.set_status(f"Letterboxd error: {e}", ACCENT)
        fetch_lb_async(username, on_done, on_err)

    def _fetch_tmdb_posters(self, api_key):
        all_movies = _plex_movies + _lb_movies
        missing = [m for m in all_movies if not m.get('poster_url')]
        if not missing:
            return
        self.set_status(f"Fetching {len(missing)} posters from TMDB…")
        def on_done():
            self.set_status("Posters updated", GREEN)
            _notify_refresh()
        fetch_tmdb_posters_async(all_movies, api_key, on_done)


# ── Welcome / Sign-In Screen ──────────────────────────────────────────────────
class WelcomeScreen(Screen):
    def __init__(self, on_connect=None, **kwargs):
        super().__init__(**kwargs)
        self._on_connect = on_connect
        self._inputs     = {}
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical', padding=dp(24), spacing=dp(10))
        with root.canvas.before:
            Color(*BG)
            Rectangle(pos=root.pos, size=root.size)

        root.add_widget(Widget(size_hint_y=0.08))

        title = Label(text="[b]CineQueue[/b]", markup=True,
                      font_size=dp(34), color=ACCENT,
                      size_hint_y=None, height=dp(50),
                      halign='center', valign='middle')
        title.bind(size=lambda w, s: setattr(w, 'text_size', s))
        root.add_widget(title)

        sub = Label(
            text="Your personal movie queue\nPowered by Plex + Letterboxd",
            font_size=dp(13), color=SUBTEXT,
            halign='center', valign='middle',
            size_hint_y=None, height=dp(44))
        sub.bind(size=lambda w, s: setattr(w, 'text_size', s))
        root.add_widget(sub)

        root.add_widget(Widget(size_hint_y=0.04))

        fields = [
            ("plex_url",    "Plex Server URL",   "http://192.168.1.100:32400", False),
            ("plex_token",  "Plex Token",         "xxxxxxxxxxxxxxxx",           True),
            ("lb_username", "Letterboxd Username","@yourusername",              False),
        ]
        for key, label, hint, is_pass in fields:
            lbl = Label(text=label, font_size=dp(11), color=SUBTEXT,
                        size_hint_y=None, height=dp(18),
                        halign='left', valign='middle')
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            inp = TextInput(hint_text=hint, password=is_pass,
                            size_hint_y=None, height=dp(42),
                            font_size=dp(12),
                            background_color=CARD, foreground_color=TEXT,
                            cursor_color=ACCENT, multiline=False,
                            padding=[dp(8), dp(10)])
            self._inputs[key] = inp
            root.add_widget(lbl)
            root.add_widget(inp)

        self._status_lbl = Label(text="", font_size=dp(10), color=ACCENT,
                                  size_hint_y=None, height=dp(20),
                                  halign='center', valign='middle')
        self._status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        root.add_widget(self._status_lbl)

        connect_btn = Button(
            text="Connect", font_size=dp(14), bold=True,
            size_hint_y=None, height=dp(50),
            background_normal="", background_color=ACCENT2, color=TEXT)
        skip_btn = Button(
            text="Skip — use demo data", font_size=dp(12),
            size_hint_y=None, height=dp(38),
            background_normal="", background_color=CARD, color=SUBTEXT)
        connect_btn.bind(on_press=self._connect)
        skip_btn.bind(on_press=lambda *_: self._on_connect and self._on_connect(skip=True))

        root.add_widget(connect_btn)
        root.add_widget(skip_btn)
        root.add_widget(Widget())
        self.add_widget(root)

    def _connect(self, *_):
        data = {k: v.text.strip() for k, v in self._inputs.items()}
        if not any(data.values()):
            self._status_lbl.text = "Enter at least one service to connect"
            return
        Settings.save(data)
        if self._on_connect:
            self._on_connect(skip=False)


# ── Background Syncer ─────────────────────────────────────────────────────────
class _BackgroundSyncer:
    """Fetches fresh data silently without a loading screen.
    Merges with cached data, TMDB-enriches only new movies, saves cache."""

    def __init__(self, plex_url, plex_token, lb_username, tmdb_key,
                 cached_plex, cached_lb, on_done):
        self._plex_url    = plex_url
        self._plex_token  = plex_token
        self._lb_username = lb_username
        self._tmdb_key    = tmdb_key
        self._cached_plex = cached_plex
        self._cached_lb   = cached_lb
        self._on_done     = on_done
        self._done_count  = [0]
        self._total       = [0]
        self._new_plex    = []
        self._new_lb      = []

    def run(self):
        sources = []
        if self._plex_url and self._plex_token:
            sources.append('plex')
        if self._lb_username:
            sources.append('lb')
        self._total[0] = len(sources)
        if not sources:
            return

        if 'plex' in sources:
            fetch_plex_async(self._plex_url, self._plex_token,
                             on_done=self._on_plex, on_error=self._on_plex_err)
        if 'lb' in sources:
            fetch_lb_async(self._lb_username,
                           on_done=self._on_lb, on_error=self._on_lb_err)
            fetch_lb_stats_async(self._lb_username,
                                 on_done=self._on_lb_stats, on_error=lambda e: None)

    def _on_plex(self, movies):
        global _plex_movies
        merged, new = MovieCache.merge(self._cached_plex, movies)
        _plex_movies   = merged
        self._new_plex = new
        self._check()

    def _on_plex_err(self, e):
        #print(f"[BgSync] Plex error: {e}")
        self._check()

    def _on_lb(self, movies):
        global _lb_movies
        merged, new = MovieCache.merge(self._cached_lb, movies)
        _lb_movies   = merged
        self._new_lb = new
        self._check()

    def _on_lb_err(self, e):
        #print(f"[BgSync] LB error: {e}")
        self._check()

    def _on_lb_stats(self, stats):
        global _lb_stats
        _lb_stats = stats

    def _check(self):
        self._done_count[0] += 1
        if self._done_count[0] < self._total[0]:
            return
        _find_intersection(_plex_movies, _lb_movies)
        new_movies = self._new_plex + self._new_lb
        if self._tmdb_key and new_movies:
            #print(f"[BgSync] TMDB-enriching {len(new_movies)} new movies")
            fetch_tmdb_enrich_async(new_movies, self._tmdb_key, self._finish)
        else:
            self._finish()

    def _finish(self):
        MovieCache.save(_plex_movies, _lb_movies, _lb_stats)
        Clock.schedule_once(lambda dt: self._on_done(), 0)


# ── App ───────────────────────────────────────────────────────────────────────
class CineQueueApp(App):
    _REFRESH_INTERVAL = 120  # seconds between background syncs

    def build(self):
        Window.clearcolor = BG

        font_path = resource_find('NotoEmoji-Regular.ttf') or 'NotoEmoji-Regular.ttf'
        LabelBase.register('NotoEmoji', fn_regular=font_path)

        Settings.load()
        DownloadQueue.load()

        self._sm              = ScreenManager(transition=SlideTransition())
        self._settings_screen = SettingsScreen(name='settings')
        self._watch_screen    = WatchScreen(name='watch')
        self._refresh_timer   = None

        has_creds = bool(Settings.get('plex_url') or Settings.get('lb_username'))

        # Add main screens
        for s in [self._watch_screen,
                  RecommendScreen(name='recommend'),
                  AnalyticsScreen(name='analytics'),
                  DownloadsScreen(name='downloads'),
                  self._settings_screen]:
            self._sm.add_widget(s)

        self._nav = NavBar(manager=self._sm)
        self._nav.size_hint_y = None
        self._nav.height      = dp(0)  # hidden until ready

        root = BoxLayout(orientation='vertical')
        root.add_widget(self._sm)
        root.add_widget(self._nav)

        if has_creds:
            # Try loading from cache first
            cached_plex, cached_lb, cached_stats = MovieCache.load()
            if cached_plex or cached_lb:
                # Populate globals from cache and show app immediately
                global _plex_movies, _lb_movies, _lb_stats
                _plex_movies = cached_plex
                _lb_movies   = cached_lb
                _lb_stats    = cached_stats
                _find_intersection(_plex_movies, _lb_movies)
                self._sm.current = 'watch'
                self._nav.height = dp(56)
                # Background sync shortly after launch, then every 2 minutes
                Clock.schedule_once(lambda dt: self._background_sync(), 2.0)
                Clock.schedule_once(lambda dt: self._start_refresh_timer(), 3.0)
            else:
                # First launch — show loading screen
                loading = LoadingScreen(name='loading', on_ready=self._on_load_done)
                self._sm.add_widget(loading)
                self._sm.current = 'loading'
                plex_url   = Settings.get('plex_url')
                plex_token = Settings.get('plex_token')
                lb_user    = Settings.get('lb_username')
                tmdb_key   = Settings.get('tmdb_key')
                Clock.schedule_once(
                    lambda dt: loading.start(plex_url, plex_token, lb_user, tmdb_key), 0.3)
        else:
            welcome = WelcomeScreen(name='welcome', on_connect=self._on_welcome_done)
            self._sm.add_widget(welcome)
            self._sm.current = 'welcome'

        return root

    def _on_load_done(self):
        #print("[App] Loading done — switching to watch screen")
        self._sm.current = 'watch'
        self._nav.height = dp(56)
        # Start periodic refresh
        self._start_refresh_timer()

    def _start_refresh_timer(self):
        if self._refresh_timer:
            self._refresh_timer.cancel()
        self._refresh_timer = Clock.schedule_interval(
            lambda dt: self._background_sync(), self._REFRESH_INTERVAL)

    def _background_sync(self):
        """Silently fetch fresh data in background, only TMDB-enrich new movies."""
        plex_url   = Settings.get('plex_url')
        plex_token = Settings.get('plex_token')
        lb_user    = Settings.get('lb_username')
        tmdb_key   = Settings.get('tmdb_key')
        if not (plex_url or lb_user):
            return
        #print("[App] Background sync starting…")
        # Reuse the LoadingScreen logic but silently (no visible loading screen)
        syncer = _BackgroundSyncer(
            plex_url, plex_token, lb_user, tmdb_key,
            cached_plex=list(_plex_movies),
            cached_lb=list(_lb_movies),
            on_done=self._on_bg_sync_done)
        syncer.run()

    def _on_bg_sync_done(self):
        #print("[App] Background sync done")
        _notify_refresh()
        if not self._refresh_timer:
            self._start_refresh_timer()

    def _on_welcome_done(self, skip=False):
        if skip:
            self._sm.current = 'watch'
            self._nav.height = dp(56)
            return
        # After welcome: use loading screen to preload
        plex_url   = Settings.get('plex_url')
        plex_token = Settings.get('plex_token')
        lb_user    = Settings.get('lb_username')
        tmdb_key   = Settings.get('tmdb_key')
        if 'loading' not in [s.name for s in self._sm.screens]:
            loading = LoadingScreen(name='loading', on_ready=self._on_load_done)
            self._sm.add_widget(loading)
        self._sm.current = 'loading'
        loading = self._sm.get_screen('loading')
        Clock.schedule_once(
            lambda dt: loading.start(plex_url, plex_token, lb_user, tmdb_key), 0.2)


if __name__ == '__main__':
    CineQueueApp().run()
