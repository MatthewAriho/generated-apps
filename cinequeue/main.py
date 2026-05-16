"""
CineQueue — Movie Picker App
Plex + Letterboxd integration with real API connections
"""

import random, json, os, re, ssl, threading, socket, webbrowser, time, hashlib
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.toolbar import MDTopAppBar
from kivymd.uix.bottomnavigation import MDBottomNavigation, MDBottomNavigationItem
from kivymd.uix.dialog import MDDialog
from kivymd.uix.progressbar import MDProgressBar

from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.image import AsyncImage
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.properties import BooleanProperty
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.core.window import Window
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.relativelayout import RelativeLayout
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
                base = MDApp.get_running_app().user_data_dir
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
                    'genre', 'country', 'year', 'local_poster',
                    'tmdb_enriched')
    _EMPTY_VALS  = (None, '', 'Unknown', '?', 0)

    @classmethod
    def _file(cls):
        if cls._path is None:
            try:
                base = MDApp.get_running_app().user_data_dir
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
                    print(f"Data from project query - {r}")
                    if r.get('success'):
                        data = r.get('data', {})
                        print(f"Data from project query - {data}")
                        if isinstance(data, dict):
                            projects = list(data.values())
                            print(f"Projects returned (dict)- {projects}")
                            return projects
                        if isinstance(data, list):
                            print(f"Projects returned (list) - {projects}")
                            return data
                    break
                except (socket.timeout, TimeoutError):
                    print(f"Socket timeout when querying projects - {attempt}")
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
            print("Project found: {pnname}")
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
    
    def stop_torrent(self, hash_str):
        """Pause/Stop a torrent by hash so it stops seeding"""
        data = urllib.parse.urlencode({'hashses': hash_str.lower()}).encode()
        headers = {'Cookie': f'SID={self._sid}'} if self._sid else {}
        headers['Content-Type'] = 'application/x-www-form--urlencoded'
        req = urllib.request.Request(f"{self._base}/api/v2/torrents/stop", 
                                     data=data, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, context=self._ctx(), timeout=10) as r:
                return r.read()
        except Exception as e:
            # Older qbit (<5.0) uses /pause not stop
            req = urllib.request.Request(f"{self._base}/api/v2/torrents/pause", 
                                     data=data, method="POST", headers=headers)
            with urllib.request.urlopen(req, context=self._ctx(), timeout=10) as r:
                return r.read()


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
            'grabbing_since': None,
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
            print("Created Radarr client and searching for movie")

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
            
            print("Movie found on radarr, going through quality profiles and root folder")
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

            print("Adding in Radarr + automatic search via Prowlarr indexers")
            # 3. Add movie to Radarr + trigger automatic search via Prowlarr indexers
            radarr_id = None
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
                print(f"Result from adding movie - {result}")
                DownloadQueue.update(entry_id, status='downloading',
                                      radarr_id=radarr_id, qbit_hash=None)
                Clock.schedule_once(lambda dt: on_update(entry), 0)
            except Exception as e:
                err = str(e)
                # Radarr returns 400 if movie already exists — look it up to get its ID
                if '400' in err or 'already' in err.lower():
                    try:
                        existing = client.lookup(entry['title'], entry.get('year', ''))
                        match = next(
                            (m for m in existing
                            if str(m.get('year', '')) == str(entry.get('year', '')) and m.get('title', '').lower() == entry['title'].lower()),
                                existing[0] if existing else None
                            )
                        radarr_id = match.get('id') if match else None
                    except Exception as e:
                        print("Exception while looking up existing radarr ids")
                        radarr_id = None
                    DownloadQueue.update(entry_id, status='downloading',
                                         radarr_id= radarr_id,
                                          error='Already in Radarr — monitoring active')
                else:
                    DownloadQueue.update(entry_id, status='failed', error=err)
                    Clock.schedule(lambda dt: on_update(entry), 0)
                    return
                Clock.schedule_once(lambda dt: on_update(entry), 0)

            #4. Confirm if Radarr hhas the movie queued for download in qBit
            if radarr_id:
                print("Movie is added to radarr, polling for progress..")
                try:
                    movie_rec = client.get_movie(radarr_id)
                    print(f"Movie data from radarr - {movie_rec}")
                    queue_recs = client.queue(radarr_id)

                    has_file = movie_rec.get('hasFile', False)
                    in_queue = len(queue_recs) > 0
                    if has_file:
                        DownloadQueue.update(entry_id, status='complete', progress=1.0)
                    elif in_queue:
                        q = queue_recs[0]
                        size_tot = q.get('size', 0)
                        size_left = q.get('sizeleft', size_tot)
                        prog = (1.0 - size_left/size_tot) if size_tot else 0.0
                        DownloadQueue(entry_id, status="downloading", 
                                                progress=prog,
                                                qbit_status=q.get('status', '')
                                    )
                    else:
                        # Radarr accepted the movie but hasnt found a release yet
                        DownloadQueue(entry_id, status="grabbing", error="Searching indexers...", grabbing_since=time.time())

                    Clock.schedule_once(lambda dt: on_update(entry), 0)
                except Exception as e:
                    print("Exception while polling download progress")
                    pass # non-fatal - poll_progress will catch it next cycle
            else:
                print("Movie doesnt have a radarr id, failed to  poll")

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
            qb = None
            torrents = []
            if qbit_url:
                try:
                    qb = QBitClient(qbit_url, qbit_user, qbit_pass)
                    if qb.login():
                        torrents = qb.get_torrents()
                    else:
                        qb = None
                except Exception:
                    qb = None

            radarr_client = RadarrClient(radarr_url, radarr_key) if (radarr_key and radarr_url) else None
            # for entry in active:
            #     print(f"Movie entry -{entry}")
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
                stored_hash = (entry.get('qbit_hash') or '').lower()
                if stored_hash:
                    qb_match = next((t for t in torrents
                                     if t['hash'].lower() == stored_hash), None)
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
                    
                # if no qbit or radarr queue match, check movie record for completion
                if not updates and radarr_client and entry.get('radarr_id'):
                    try:
                        movie_rec = radarr_client.get_movie(entry['radarr_id'])
                        if movie_rec.get('hasFile'):
                            updates.update(progress=1.0, status='complete', grabbing_since=None)
                            if qb:
                                hash_to_stop = entry.get('qbit_hash')
                                if hash_to_stop:
                                    try:
                                        qb.stop_torrent(hash_to_stop)
                                    except Exception as e:
                                        print("Failed to stop stale download")
                                        pass
                    except Exception:
                        pass

                if updates:
                    prog   = updates.get('progress', entry.get('progress', 0.0))
                    if 'status' not in updates:
                        updates['status'] = 'complete' if prog >= 1.0 else 'downloading'
                    # Stamp grabbing_since when still at 0% witg bi qBit activity
                    if prog == 0.0 and not updates.get('qbit_hash') and not entry.get('grabbing_since'):
                        updates['grabbing_since'] = time.time()
                    elif prog > 0.0 and 'grabbing_since' not in updates:
                        updates['grabbing_since'] = None
                    
                    #Stop seeding in qbit when complete
                    if prog == 1.0 and qb:
                        hash_to_stop = updates.get('qbit_hash') or entry.get('qbit_hash')
                        if hash_to_stop:
                            try:
                                qb.stop_torrent(hash_to_stop)
                            except Exception as e:
                                print("Failed to stop seeding torrent")
                                pass
                    DownloadQueue.update(entry['id'], **updates)
                    Clock.schedule_once(lambda dt: on_update(), 0)
                else:
                    # No match anywhere - still fire on_update so UI reflects current state
                    Clock.schedule_once(lambda dt: on_update(), 0)
                    if not entry.get('grabbing_since') and entry.get('progress', 0.0) == 0.0:
                        # No match in Radarr queue or qbit - start the stuck clock
                        DownloadQueue.update(entry['id'], grabbing_since=time.time())

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

<SectionLabel>:
    size_hint_y: None
    height: dp(36)
    font_size: dp(13)
    bold: True
    markup: True
    theme_text_color: "Custom"
    text_color: 0.60, 0.60, 0.70, 1
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

# ── Poster Image Cache ────────────────────────────────────────────────────────
class PosterCache:
    """Downloads poster images to local storage so AsyncImage uses a local path.
    Filenames are derived from the URL so re-downloading is never needed."""

    @staticmethod
    def _dir():
        try:
            base = MDApp.get_running_app().user_data_dir
        except Exception:
            base = os.path.dirname(os.path.abspath(__file__))
        d = os.path.join(base, 'cinequeue_posters')
        os.makedirs(d, exist_ok=True)
        return d

    @staticmethod
    def local_path(url):
        """Return the local file path for a remote URL (may not exist yet).
        Uses MD5 (not Python's hash()) so filenames are stable across restarts."""
        name = re.sub(r'[^a-zA-Z0-9._-]', '_', url.split('/')[-1]) or 'poster.jpg'
        prefix = hashlib.md5(url.encode()).hexdigest()[:8]
        return os.path.join(PosterCache._dir(), f"{prefix}_{name}")

    @staticmethod
    def download(url, ctx=None):
        """Download url to local cache. Returns local path, or None on failure."""
        path = PosterCache.local_path(url)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path  # already cached
        try:
            if ctx is None:
                ctx = ssl._create_unverified_context()
            req = urllib.request.Request(url, headers={'User-Agent': 'CineQueue/1.0'})
            with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
                data = r.read()
            with open(path, 'wb') as f:
                f.write(data)
            return path
        except Exception:
            return None

    @staticmethod
    def ensure(movie, ctx=None):
        """Download poster for movie if not already cached. Sets local_poster key."""
        url = movie.get('poster_url')
        if not url:
            return
        if movie.get('local_poster') and os.path.exists(movie['local_poster']):
            return  # already have a valid local copy
        local = PosterCache.download(url, ctx)
        if local:
            movie['local_poster'] = local


def fetch_tmdb_enrich_async(movies, api_key, on_done):
    """Enrich movies using TMDB: fills poster, runtime, genre, director, country, year.
    Downloads poster images to local storage. Skips already-enriched movies."""
    def run():
        search  = "https://api.themoviedb.org/3/search/movie"
        detail  = "https://api.themoviedb.org/3/movie"
        img     = "https://image.tmdb.org/t/p/w342"

        _ctx = ssl._create_unverified_context()
        for m in movies:
            if m.get('tmdb_enriched'):
                if not (m.get('local_poster') and os.path.exists(m['local_poster'])):
                    PosterCache.ensure(m, _ctx)
                continue

            needs = (
                not m.get('poster_url') or
                m.get('runtime', 0) < 1 or
                m.get('genre') in ('Unknown', '?', '', None) or
                m.get('director') in ('Unknown', '?', '', None) or
                not m.get('year')
            )
            if not needs:
                m['tmdb_enriched'] = True
                if not (m.get('local_poster') and os.path.exists(m['local_poster'])):
                    PosterCache.ensure(m, _ctx)
                continue

            try:
                t   = urllib.parse.quote(m['title'])
                yr  = m.get('year', '')
                url = f"{search}?api_key={api_key}&query={t}&year={yr}&language=en-US"
                req = urllib.request.Request(url, headers={'Accept': 'application/json'})
                with urllib.request.urlopen(req, timeout=10, context=_ctx) as r:
                    results = json.loads(r.read()).get('results', [])

                if not results:
                    m['tmdb_enriched'] = True
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

                PosterCache.ensure(m, _ctx)

            except Exception:
                pass

            m['tmdb_enriched'] = True

        Clock.schedule_once(lambda dt: on_done(), 0)

    threading.Thread(target=run, daemon=True).start()

# ── Emoji helper ──────────────────────────────────────────────────────────────
def E(s):
    """No-op: previously wrapped in NotoEmoji markup which breaks on Android
    (FreeType in p4a does not support CBDT/CBLC color bitmap tables).
    Returns the raw string — callers should use plain BMP symbols instead."""
    return s

# ── Shared Widgets ────────────────────────────────────────────────────────────
# Flag emoji use Regional Indicator pairs — NotoEmoji renders each indicator
# as a styled letter square (e.g. 🇯🇵 → squared J + squared P), which looks
# good and is clearly readable without needing ligature shaping.
FLAG = {"JP": "🇯🇵", "KR": "🇰🇷", "FR": "🇫🇷", "UK": "🇬🇧", "US": "🇺🇸",
        "DE": "🇩🇪", "IT": "🇮🇹", "SE": "🇸🇪", "AU": "🇦🇺", "CN": "🇨🇳",
        "IN": "🇮🇳", "BR": "🇧🇷", "MX": "🇲🇽", "DK": "🇩🇰", "NO": "🇳🇴"}

class SectionLabel(MDLabel):
    pass

# ── Downloads Screen ──────────────────────────────────────────────────────────
class DownloadsScreen(MDScreen):
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
        'queued':        '• Queued',
        'searching':     '• Searching Radarr…',
        'results_found': '• Release found',
        'no_results':    '• No releases found',
        'grabbing':      '• Sending to qBit…',
        'downloading':   '• Downloading',
        'complete':      '• Complete',
        'failed':        '• Failed',
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._poll_ev    = None
        self._list_box   = None
        self._empty_lbl  = None
        self._build_ui()

    def on_enter(self):
        self._rebuild_list()
        self._poll()
        self._poll_ev = Clock.schedule_interval(lambda dt: self._poll(), 30)

    def on_leave(self):
        if self._poll_ev:
            self._poll_ev.cancel()
            self._poll_ev = None

    def _build_ui(self):
        root = BoxLayout(orientation='vertical')

        hdr = MDTopAppBar(
            title="Downloads",
            md_bg_color=(0.10, 0.10, 0.14, 1),
            specific_text_color=ACCENT,
            elevation=0,
            right_action_items=[["refresh", lambda x: (self._poll(), self._rebuild_list())]],
        )
        root.add_widget(hdr)

        scroll = ScrollView()
        self._list_box = BoxLayout(orientation='vertical', size_hint_y=None,
                                   spacing=dp(8), padding=[dp(8), dp(8)])
        self._list_box.bind(minimum_height=self._list_box.setter('height'))
        self._empty_lbl = MDLabel(
            text="No downloads queued.\nTap Download on any movie not available on Plex.",
            font_size=dp(13), theme_text_color="Custom", text_color=SUBTEXT,
            halign='center', valign='middle',
            size_hint_y=None, height=dp(120))
        self._empty_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        self._list_box.add_widget(self._empty_lbl)
        scroll.add_widget(self._list_box)
        root.add_widget(scroll)
        self.add_widget(root)

    def _rebuild_list(self):
        self._list_box.clear_widgets()
        if not _download_queue:
            self._list_box.add_widget(self._empty_lbl)
            return
        for entry in reversed(_download_queue):  # newest first
            self._list_box.add_widget(self._make_entry_card(entry))

    def _make_entry_card(self, entry):
        card = MDCard(
            orientation='vertical',
            size_hint_y=None,
            height=dp(110),
            padding=[dp(10), dp(8)],
            spacing=dp(4),
            md_bg_color=CARD,
            radius=[dp(10)],
        )

        # Row 1: title + status badge
        row1 = BoxLayout(size_hint_y=None, height=dp(22))
        title_lbl = MDLabel(
            text=f"[b]{entry['title']}[/b]  ({entry.get('year','')})",
            markup=True, font_size=dp(13),
            theme_text_color="Custom", text_color=TEXT,
            halign='left', valign='middle')
        title_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        status = entry.get('status', 'queued')
        status_lbl = MDLabel(
            text=self._STATUS_LABEL.get(status, status),
            font_size=dp(10),
            theme_text_color="Custom",
            text_color=self._STATUS_COLOR.get(status, SUBTEXT),
            size_hint_x=None, width=dp(130),
            halign='right', valign='middle')
        status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        row1.add_widget(title_lbl)
        row1.add_widget(status_lbl)
        card.add_widget(row1)

        # Row 2: genre · director · added
        meta = f"{entry.get('genre','')}  ·  {entry.get('director','')}  ·  {entry.get('added_at','')}"
        meta_lbl = MDLabel(text=meta, font_size=dp(9),
                           theme_text_color="Custom", text_color=SUBTEXT,
                           size_hint_y=None, height=dp(16),
                           halign='left', valign='middle')
        meta_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        card.add_widget(meta_lbl)

        # Row 3: progress bar or error/result info
        if status in ('downloading', 'grabbing'):
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
            info_lbl = MDLabel(
                text=f"{pct_txt}{eta_txt}{size_txt}",
                font_size=dp(10), theme_text_color="Custom", text_color=ACCENT2,
                size_hint_y=None, height=dp(16),
                halign='left', valign='middle')
            info_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            card.add_widget(info_lbl)
            prog_bar = MDProgressBar(
                value=int(prog * 100),
                max=100,
                color=ACCENT2,
                size_hint_y=None,
                height=dp(8),
            )
            card.add_widget(prog_bar)

            # Show Radarr link is stuck at 0% with no qBit activity for > 10 min
            grabbing_since = entry.get('grabbing_since')
            is_stuck = (
                prog == 0.0
                and not entry.get('qbit_hash')
                and grabbing_since
                and (time.time() - grabbing_since) > 600
            )
            if is_stuck:
                radarr_base = Settings.get('radarr_url', '').rstrip('/')
                # radarr_id = entry.get('radarr_id')
                if radarr_base:
                    # url = (f"{radarr_base}/movie/{radarr_id}"
                    #        if radarr_id else f"{radarr_base}/activity/queuee")
                    url = f"{radarr_base}/activity/queue"
                    stuck_row = BoxLayout(size_hint_y=None, height=dp(24), spacing=dp(6))
                    stuck_lbl = MDLabel(
                        text = "Stuck - no activity",
                        font_size=dp(9), theme_text_color="Custom", text_color=GOLD,
                        size_hint_y=None, height=dp(24),
                        halign='left', valign='middle',
                    )
                    stuck_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
                    radarr_btn = MDFlatButton(
                        text="Open in Raadarr",
                        theme_text_color="Custom", text_color=ACCENT2,
                        size_hint_x=None
                    )
                    radarr_btn.bind(on_press=lambda *_, u=url: webbrowser.open(u))
                    stuck_row.add_widget(stuck_lbl)
                    stuck_row.add_widget(radarr_btn)
                    card.height = dp(140)
                    card.add_widget(stuck_row)
        elif status == 'failed' and entry.get('error'):
            err_lbl = MDLabel(text=entry['error'], font_size=dp(9),
                              theme_text_color="Custom", text_color=ACCENT,
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
            info_lbl = MDLabel(
                text=f"{rel_title}  ·  {seeders} seeders  {size_txt}",
                font_size=dp(9), theme_text_color="Custom", text_color=ACCENT2,
                size_hint_y=None, height=dp(16), halign='left', valign='middle')
            info_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            card.add_widget(info_lbl)
        elif status == 'no_results':
            retry_row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
            retry_btn = MDFlatButton(
                text="Retry Search",
                theme_text_color="Custom", text_color=ACCENT2,
            )
            retry_btn.bind(on_press=lambda *_, eid=entry['id']: self._retry(eid))
            retry_row.add_widget(retry_btn)
            card.add_widget(retry_row)

        # Row: remove button
        btn_row = BoxLayout(size_hint_y=None, height=dp(28), spacing=dp(8))
        btn_row.add_widget(Widget())
        remove_btn = MDFlatButton(
            text="Remove",
            theme_text_color="Custom", text_color=ACCENT,
        )
        remove_btn.bind(on_press=lambda *_, eid=entry['id']: self._remove(eid))
        btn_row.add_widget(remove_btn)
        card.add_widget(btn_row)
        return card

    def _retry(self, entry_id):
        DownloadQueue.search_and_grab(entry_id, lambda e: self._rebuild_list())

    def _remove(self, entry_id):
        DownloadQueue.remove(entry_id)
        self._rebuild_list()

    def _poll(self):
        DownloadQueue.poll_progress(self._rebuild_list)
        self._rebuild_list()


# NavBar replaced by MDBottomNavigation — see CineQueueApp._launch_main()


class PosterWidget(FloatLayout):
    def __init__(self, movie, h=dp(160), **kwargs):
        super().__init__(size_hint_y=None, height=h, **kwargs)
        with self.canvas.before:
            Color(*movie.get('poster_color', CARD))
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)

        local = movie.get('local_poster')
        url = (local if local and os.path.exists(local) else None) or movie.get('poster_url')
        if url:
            img = AsyncImage(
                source=url,
                allow_stretch=True,
                keep_ratio=True,
                fit_mode='fill',
                size_hint=(1, 1),
                pos_hint={'x': 0, 'y': 0}
            )
            if local and os.path.exists(local) and movie.get('poster_url'):
                img.bind(on_error=lambda *a: setattr(img, 'source', movie['poster_url']))
            self.add_widget(img)
        else:
            cc     = movie.get('country', '?')
            rating = movie.get('rating', 0)
            text   = f"{cc}\n{rating:.1f}/10" if rating else cc
            self.add_widget(Label(
                text=text, markup=True, font_size=dp(18),
                bold=True, color=TEXT,
                halign='center', valign='middle',
                size_hint=(1, 1),
                pos_hint={'x': 0, 'y': 0}
            ))

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

        local = movie.get('local_poster')
        url = (local if local and os.path.exists(local) else None) or movie.get('poster_url')
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

        title_lbl = Label(text=movie['title'], font_size=dp(11), color=TEXT,
                          halign='center', valign='middle',
                          size_hint=(1, None), height=dp(34))
        title_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        overlay.add_widget(title_lbl)

        if badge_text:
            badge = Label(text=badge_text, font_size=dp(9), color=badge_color,
                          size_hint=(1, None), height=dp(14),
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


class FilterChip(Button):
    """ Toggle chip that works reliably across KivyMD versions. """
    active = BooleanProperty(False)
    def __init__(self, text, active=False, **kwargs):
        super().__init__(
            text=text,
            size_hint=(None, None),
            size=(dp(95), dp(40)),
            background_normal='',
            background_down='',
            font_size=dp(13),
            color=(1,1,1,1),
            **kwargs,
        )
        self.active = active
        self._update_color()
        self.bind(active=lambda *_: self._update_color())

    def on_release(self):
        self.active = not self.active

    def _update_color(self, *_):
        self.background_color = ACCENT if self.active else CARD


# ── Loading Screen ────────────────────────────────────────────────────────────
class LoadingScreen(MDScreen):
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
        root = BoxLayout(orientation='vertical', padding=dp(32), spacing=dp(16))
        root.add_widget(Widget(size_hint_y=0.08))

        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.png')
        logo = AsyncImage(source=logo_path,
                          size_hint=(None, None), size=(dp(120), dp(120)),
                          pos_hint={'center_x': 0.5},
                          allow_stretch=True, keep_ratio=True)
        root.add_widget(logo)
        root.add_widget(Widget(size_hint_y=None, height=dp(8)))

        title = MDLabel(text="[b]CineQueue[/b]", markup=True,
                        font_size=dp(36),
                        theme_text_color="Custom", text_color=ACCENT,
                        size_hint_y=None, height=dp(54),
                        halign='center', valign='middle')
        title.bind(size=lambda w, s: setattr(w, 'text_size', s))
        root.add_widget(title)

        sub = MDLabel(text="Loading your movies…", font_size=dp(13),
                      theme_text_color="Custom", text_color=SUBTEXT,
                      size_hint_y=None, height=dp(28),
                      halign='center', valign='middle')
        sub.bind(size=lambda w, s: setattr(w, 'text_size', s))
        root.add_widget(sub)

        # Deterministic progress bar — value driven by poster download progress
        self._progress_bar = MDProgressBar(
            value=0, max=100,
            size_hint_y=None, height=dp(6),
        )
        root.add_widget(self._progress_bar)

        # Percentage label
        self._pct_lbl = MDLabel(text="0%", font_size=dp(12),
                                theme_text_color="Custom", text_color=SUBTEXT,
                                size_hint_y=None, height=dp(20),
                                halign='center', valign='middle')
        root.add_widget(self._pct_lbl)

        self._status_lbl = MDLabel(text="", font_size=dp(12),
                                   theme_text_color="Custom", text_color=GOLD,
                                   size_hint_y=None, height=dp(28),
                                   halign='center', valign='middle')
        self._status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        root.add_widget(self._status_lbl)

        self._poster_lbl = MDLabel(text="", font_size=dp(12),
                                   theme_text_color="Custom", text_color=SUBTEXT,
                                   size_hint_y=None, height=dp(24),
                                   halign='center', valign='middle')
        self._poster_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        root.add_widget(self._poster_lbl)

        self._skip_btn = MDFlatButton(
            text="Skip",
            theme_text_color="Custom", text_color=SUBTEXT,
            size_hint_y=None, height=dp(40),
            opacity=0, disabled=True,
        )
        self._skip_btn.bind(on_press=self._on_skip)
        skip_row = BoxLayout(size_hint_y=None, height=dp(48))
        skip_row.add_widget(Widget())
        skip_row.add_widget(self._skip_btn)
        skip_row.add_widget(Widget())
        root.add_widget(skip_row)

        root.add_widget(Widget(size_hint_y=0.05))
        self.add_widget(root)

    def _log(self, msg):
        self._status_lbl.text = msg

    def start(self, plex_url, plex_token, lb_username, tmdb_key, cached_plex=None, cached_lb=None):
        """Fetch fresh data. If cached_* lists are provided, only TMDB-enrich new movies."""
        self._progress_bar.start()
        self._skipped = False
        self._tmdb_key    = tmdb_key
        self._cached_plex = cached_plex or []
        self._cached_lb   = cached_lb   or []
        self._new_plex    = []
        self._new_lb      = []
        sources = []
        if plex_url and plex_token:
            sources.append('plex')
        if lb_username:
            sources.append('lb')
        self._total[0] = len(sources)

        Clock.schedule_once(lambda dt: self._show_skip_if_needed(), 8)
        Clock.schedule_once(lambda dt: self._auto_skip(), 60)

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
        self._new_plex = []
        if self._cached_plex:
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
        self._new_lb = []
        if self._cached_lb:
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
            tmdb_key   = self._tmdb_key
            new_movies = self._new_plex + self._new_lb
            if tmdb_key and new_movies:
                self._log(f"Enriching {len(new_movies)} new movies via TMDB…")
                fetch_tmdb_enrich_async(new_movies, tmdb_key, self._on_tmdb_done)
            else:
                if tmdb_key and not new_movies:
                    self._log("All movies up to date.")
                self._save_and_finish()

    def _on_tmdb_done(self):
        if self._skipped:
            return
        self._log("Metadata ready. Downloading posters…")
        self._save_and_finish()

    def _save_and_finish(self):
        MovieCache.save(_plex_movies, _lb_movies, _lb_stats)
        self._finish()

    def _finish(self):
        """Data fetch complete — now download posters with progress, then enter app."""
        if self._skipped:
            return
        self._progress_bar.stop()
        self._progress_bar.value = 0
        _notify_refresh()
        movies = [m for m in (_plex_movies + _lb_movies) if m.get('poster_url')]
        total = len(movies)
        if total == 0:
            Clock.schedule_once(lambda dt: self._on_ready(), 0.3)
            return

        missing = [m for m in movies
                   if not (m.get('local_poster') and os.path.exists(m['local_poster']))]

        if not missing:
            self._log("All posters cached.")
            Clock.schedule_once(lambda dt: self._on_ready(), 0.2)
            return

        self._skip_btn.opacity = 1
        self._skip_btn.disabled = False
        self._log(f"Downloading {len(missing)} poster(s)…")

        done = [0]

        def run():
            ctx = ssl._create_unverified_context()
            for m in missing:
                PosterCache.ensure(m, ctx)
                done[0] += 1
                pct = int(done[0] / len(missing) * 100)
                Clock.schedule_once(lambda dt, p=pct, d=done[0], t=len(missing):
                    self._update_progress(p, d, t), 0)
            Clock.schedule_once(lambda dt: self._on_ready(), 0.3)

        threading.Thread(target=run, daemon=True).start()

    def _update_progress(self, pct, done, total):
        self._progress_bar.value = pct
        self._pct_lbl.text = f"{pct}%"
        self._poster_lbl.text = f"Posters {done}/{total}"

    def _show_skip_if_needed(self):
        if not self._skipped:
            self._skip_btn.opacity = 1
            self._skip_btn.disabled = False

    def _auto_skip(self):
        if not self._skipped:
            self._log("Loading timed out — entering app with cached data")
            self._on_skip()

    def _on_skip(self, *_):
        if self._skipped:
            return
        self._skipped = True
        self._skip_btn.disabled = True
        MovieCache.save(_plex_movies, _lb_movies, _lb_stats)
        Clock.schedule_once(lambda dt: self._on_ready(), 0.1)


# ── Watch Screen ──────────────────────────────────────────────────────────────
class WatchScreen(MDScreen):
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

        header = MDTopAppBar(
            title="CineQueue",
            md_bg_color=(0.10, 0.10, 0.14, 1),
            specific_text_color=ACCENT,
            elevation=0,
        )
        root.add_widget(header)

        # Status bar
        self._status_lbl = MDLabel(text="", font_size=dp(12),
                                   theme_text_color="Custom", text_color=GOLD,
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
        count_row = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(0))
        minus_btn = MDIconButton(
            icon="minus",
            theme_icon_color="Custom",
            icon_color=TEXT,
            md_bg_color=CARD,
        )
        self._count_lbl = MDLabel(text=str(self.selected_count),
                                  font_size=dp(24), bold=True,
                                  theme_text_color="Custom", text_color=TEXT,
                                  halign='center', valign='middle')
        plus_btn = MDIconButton(
            icon="plus",
            theme_icon_color="Custom",
            icon_color=TEXT,
            md_bg_color=CARD,
        )
        minus_btn.bind(on_press=self._decrement_count)
        plus_btn.bind(on_press=self._increment_count)
        count_row.add_widget(Widget())
        count_row.add_widget(minus_btn)
        count_row.add_widget(self._count_lbl)
        count_row.add_widget(plus_btn)
        count_row.add_widget(Widget())
        inner.add_widget(count_row)

        # Sort chips — horizontal scroll so they never overflow on any screen width
        inner.add_widget(SectionLabel(text="SORT / FILTER BY"))
        n = len(self.SORT_OPTIONS)
        chip_w, chip_gap = dp(95), dp(6)
        sort_row = BoxLayout(orientation='horizontal',
                             size_hint=(None, None),
                             size=(n * chip_w + (n - 1) * chip_gap, dp(44)),
                             spacing=chip_gap)
        self._sort_chips = []
        for opt in self.SORT_OPTIONS:
            chip = FilterChip(text=opt, active=(opt in self.active_sorts))
            chip.bind(active=lambda c, val, o=opt: self._on_chip_active(c, val, o))
            sort_row.add_widget(chip)
            self._sort_chips.append(chip)
        sort_scroll = ScrollView(size_hint_y=None, height=dp(44),
                                 do_scroll_y=False, do_scroll_x=True,
                                 bar_width=0)
        sort_scroll.add_widget(sort_row)
        inner.add_widget(sort_scroll)

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

        scroll.add_widget(inner)
        root.add_widget(scroll)
        self.add_widget(root)
        self._refresh_movies()

    def set_status(self, msg, color=GOLD):
        self._status_lbl.text = msg
        self._status_lbl.text_color = color
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

    def _on_chip_active(self, chip, is_active, opt):
        # Lock prevents recursive callbacks when we deselect other chips
        if getattr(self, '_chip_lock', False):
            return
        self._chip_lock = True
        if is_active:
            # Single-select: deselect every other chip
            self.active_sorts = {opt}
            for c in self._sort_chips:
                if c.text != opt and c.active:
                    c.active = False
        else:
            self.active_sorts.discard(opt)
            if not self.active_sorts:
                # Nothing selected — fall back to Random
                self.active_sorts = {'Random'}
                for c in self._sort_chips:
                    if c.text == 'Random':
                        c.active = True
        self._chip_lock = False
        self._refresh_movies()

    def _sort_movies(self, movies):
        # Cache result — skip re-sort if inputs haven't changed (except Random)
        is_random = "Random" in self.active_sorts
        cache_key = (
            tuple(m['title'] for m in movies),
            frozenset(self.active_sorts),
            self.selected_count,
        )
        if not is_random and getattr(self, '_sort_cache_key', None) == cache_key:
            return self._sort_cache_val

        result = list(movies)
        if is_random:
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
        result = result[:self.selected_count]
        if not is_random:
            self._sort_cache_key = cache_key
            self._sort_cache_val = result
        return result

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
            empty = MDLabel(text="Nothing to show here",
                            font_size=dp(13), theme_text_color="Custom",
                            text_color=SUBTEXT, halign='center', valign='middle')
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
            empty = MDLabel(text="Nothing to show here",
                            font_size=dp(13), theme_text_color="Custom",
                            text_color=SUBTEXT, halign='center', valign='middle')
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
        on_plex = movie.get('source') == 'plex' or movie.get('on_plex', False)

        content = BoxLayout(orientation='vertical', spacing=dp(8),
                            size_hint_y=None, height=dp(520))

        poster = PosterWidget(movie, h=dp(300))
        content.add_widget(poster)

        for line in [
            f"[b]{movie['title']}[/b] ({movie['year']})",
            f"Director: {movie.get('director','N/A')}",
            f"Genre: {movie.get('genre','?')}  |  Country: {movie.get('country','?')}",
            f"Rating: {movie['rating']}  |  Runtime: {movie.get('runtime','?')} min",
        ]:
            lbl = MDLabel(text=line, markup=True, font_size=dp(12),
                          theme_text_color="Custom", text_color=TEXT,
                          halign='left', valign='middle',
                          size_hint_y=None, height=dp(24))
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            content.add_widget(lbl)

        if not on_plex:
            avail_lbl = MDLabel(
                text="Not available on Plex — queue via Radarr",
                font_size=dp(10), theme_text_color="Custom", text_color=GOLD,
                size_hint_y=None, height=dp(20),
                halign='center', valign='middle')
            avail_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            content.add_widget(avail_lbl)

        close_btn = MDFlatButton(text="Close",
                                 theme_text_color="Custom", text_color=SUBTEXT)
        if on_plex:
            action_btn = MDRaisedButton(text="Watch on Plex", md_bg_color=GREEN)
        else:
            action_btn = MDRaisedButton(text="Queue Download", md_bg_color=ACCENT2)

        dialog = MDDialog(
            title=movie['title'],
            type="custom",
            content_cls=content,
            buttons=[close_btn, action_btn],
            md_bg_color=(0.10, 0.10, 0.14, 1),
        )

        close_btn.bind(on_press=lambda *_: dialog.dismiss())

        if on_plex:
            def _open_plex(*args, m=movie):
                plex_url = Settings.get('plex_url', '').rstrip('/')
                if plex_url:
                    webbrowser.open(plex_url + '/web/index.html')
                dialog.dismiss()
            action_btn.bind(on_press=_open_plex)
        else:
            def _queue_dl(*args, m=movie):
                entry = DownloadQueue.add(m)
                if entry:
                    DownloadQueue.search_and_grab(entry['id'], lambda e: None)
                    dialog.dismiss()
                    app = MDApp.get_running_app()
                    if app and hasattr(app, '_nav'):
                        app._nav.switch_tab('downloads')
                else:
                    action_btn.text = "Already queued"
                    action_btn.md_bg_color = SUBTEXT
            action_btn.bind(on_press=_queue_dl)

        dialog.open()


# ── Recommend Screen ──────────────────────────────────────────────────────────
class RecommendScreen(MDScreen):
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
        new_titles = [m['title'] for m in _plex_movies + _lb_movies]
        old_titles = [m['title'] for m in getattr(self, '_all', [])]
        if new_titles != old_titles:
            # Movie list changed — reshuffle and restart from card 0
            self._all = list(_plex_movies + _lb_movies)
            random.shuffle(self._all)
            self._idx = 0
        self._animating = False
        if hasattr(self, '_card_area'):
            self._show_card()

    def _build_ui(self):
        # Use BoxLayout (vertical) so layout adapts to screen height on all devices.
        # FloatLayout with pos_hint percentages causes gaps on tall mobile screens
        # because centre_y=0.55 and y=0.04 are fractions of the full screen height,
        # not of the space between the elements — they drift apart at 800+dp heights.
        root = BoxLayout(orientation='vertical')
        with root.canvas.before:
            Color(*BG)
            self._bg_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=self._upd_bg, size=self._upd_bg)

        # Header: title + help icon (instructions moved into dialog)
        header_row = BoxLayout(size_hint_y=None, height=dp(48))
        header_row.add_widget(Widget(size_hint_x=None, width=dp(48)))  # balance help btn
        header_row.add_widget(MDLabel(
            text="[b]Swipe to Decide[/b]", markup=True,
            font_size=dp(20), theme_text_color="Custom", text_color=TEXT,
            halign='center', valign='middle'))
        help_btn = MDIconButton(
            icon="help-circle-outline",
            theme_icon_color="Custom", icon_color=SUBTEXT,
            size_hint_x=None,
        )
        help_btn.bind(on_press=self._show_swipe_help)
        header_row.add_widget(help_btn)
        root.add_widget(header_row)

        # Card area: flexible height, fills whatever remains after header + buttons
        self._card_area = FloatLayout(size_hint=(1, 1))
        root.add_widget(self._card_area)

        btn_row = BoxLayout(size_hint_y=None, height=dp(80),
                            padding=[dp(8), dp(4)], spacing=dp(8))

        def _action_col(icon, label_text, color, action):
            col = BoxLayout(orientation='vertical', size_hint_x=None,
                            width=dp(72), spacing=dp(2))
            btn = MDIconButton(icon=icon, theme_icon_color="Custom",
                               icon_color=color, icon_size=dp(34))
            btn.bind(on_press=lambda *_: self._animate(action))
            lbl = MDLabel(text=label_text, font_size=dp(11),
                          theme_text_color="Custom", text_color=color,
                          halign='center', size_hint_y=None, height=dp(18))
            col.add_widget(btn)
            col.add_widget(lbl)
            return col

        btn_row.add_widget(Widget())
        btn_row.add_widget(_action_col("skip-next", "Skip", ACCENT, 'skip'))
        btn_row.add_widget(_action_col("thumb-down-outline", "Nope", GOLD, 'not_interested'))
        btn_row.add_widget(_action_col("check-circle-outline", "Watch", GREEN, 'accept'))
        btn_row.add_widget(Widget())
        root.add_widget(btn_row)

        self._toast_lbl = MDLabel(
            text="", font_size=dp(12),
            theme_text_color="Custom", text_color=GREEN,
            size_hint_y=None, height=dp(24),
            halign='center', valign='middle', opacity=0)
        root.add_widget(self._toast_lbl)

        self.add_widget(root)
        self._show_card()

    def _show_swipe_help(self, *_):
        if not hasattr(self, '_help_dialog'):
            close_btn = MDFlatButton(text="GOT IT")
            self._help_dialog = MDDialog(
                title="Swipe Controls",
                text=(
                    "Swipe RIGHT  \u2192  Watch\n"
                    "Swipe LEFT   \u2190  Skip\n"
                    "Swipe DOWN   \u2193  Not Interested"
                ),
                buttons=[close_btn],
            )
            close_btn.bind(on_press=lambda *_: self._help_dialog.dismiss())
        self._help_dialog.open()

    def _upd_bg(self, w, _):
        self._bg_rect.pos  = w.pos
        self._bg_rect.size = w.size

    def _show_card(self):
        self._card_area.clear_widgets()
        self._current_card = None
        if self._idx >= len(self._all):
            self._card_area.add_widget(MDLabel(
                text="No more movies!\nReset to start over.",
                font_size=dp(16), theme_text_color="Custom", text_color=SUBTEXT,
                halign='center',
                pos_hint={'center_x': 0.5, 'center_y': 0.5},
                size_hint=(0.8, None), height=dp(60)))
            return
        movie = self._all[self._idx]
        card  = self._make_card(movie)
        self._card_area.add_widget(card)
        self._current_card = card

    def _make_card(self, movie):
        # Card height = poster (dp(360)) + info panel (dp(160)) = dp(520).
        # Previously dp(400) caused the info section to overflow below the card
        # and get clipped, hiding avail_text and the download button on device.
        card = BoxLayout(orientation='vertical',
                         size_hint=(None, None), size=(dp(280), dp(520)),
                         pos_hint={'center_x': 0.5, 'center_y': 0.5},
                         spacing=0, padding=0)
        with card.canvas.before:
            Color(*movie.get('poster_color', CARD))
            self._card_bg = RoundedRectangle(pos=card.pos, size=card.size,
                                              radius=[dp(16)])
        card.bind(pos=self._upd_card_bg, size=self._upd_card_bg)
        card._movie = movie

        poster = PosterWidget(movie, h=dp(360))
        card.add_widget(poster)
        # no extra label on top — PosterWidget handles country/rating fallback

        info = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(160),
                         padding=[dp(16), dp(10)], spacing=dp(6))
        with info.canvas.before:
            Color(0.0, 0.0, 0.0, 0.55)
            self._info_bg = RoundedRectangle(pos=info.pos, size=info.size,
                                              radius=[dp(0), dp(0), dp(16), dp(16)])
        info.bind(pos=self._upd_info_bg, size=self._upd_info_bg)

        def _val(key, fallback='?'):
            v = movie.get(key)
            return fallback if not v or str(v).strip() in ('Unknown', '?', '', 'None', '0') else v

        year    = _val('year', '?')
        genre   = _val('genre')
        runtime = _val('runtime')
        director = _val('director')
        runtime_str = f" · {runtime} min" if runtime != '?' else ''
        for text, color, size in [
            (f"[b]{movie['title']}[/b]", TEXT, dp(16)),
            (f"{year} · {genre}{runtime_str}", SUBTEXT, dp(13)),
            (f"Dir: {director}", SUBTEXT, dp(12)),
        ]:
            lbl = MDLabel(text=text, markup=True, font_size=size,
                          theme_text_color="Custom", text_color=color,
                          halign='left', valign='middle',
                          size_hint_y=None, height=dp(22))
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            info.add_widget(lbl)

        on_plex = movie.get('source') == 'plex' or movie.get('on_plex', False)
        avail_text  = "• Available on Plex" if on_plex else "• Not on Plex"
        avail_color = GREEN if on_plex else GOLD
        avail = MDLabel(text=avail_text, font_size=dp(12),
                        theme_text_color="Custom", text_color=avail_color,
                        halign='left', valign='middle',
                        size_hint_y=None, height=dp(18))
        avail.bind(size=lambda w, s: setattr(w, 'text_size', s))
        info.add_widget(avail)

        if not on_plex:
            dl_btn = MDRaisedButton(
                text="Queue Download",
                font_size=dp(11),
                size_hint=(None, None),
                md_bg_color=ACCENT2,
                theme_text_color="Custom", text_color=TEXT,
            )
            def _queue(btn, m=movie):
                entry = DownloadQueue.add(m)
                if entry:
                    DownloadQueue.search_and_grab(entry['id'], lambda e: None)
                    btn.text = "Queued"
                    btn.md_bg_color = SUBTEXT
                else:
                    btn.text = "Already queued"
                    btn.md_bg_color = SUBTEXT
            dl_btn.bind(on_press=_queue)
            dl_row = BoxLayout(size_hint_y=None, height=dp(38))
            dl_row.add_widget(Widget())
            dl_row.add_widget(dl_btn)
            dl_row.add_widget(Widget())
            info.add_widget(dl_row)

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
        lbl = self._toast_lbl
        lbl.text    = msg
        lbl.opacity = 1
        Animation(opacity=0, duration=0.5).start  # cancel any pending
        def _fade(*_):
            Animation(opacity=0, duration=0.6).start(lbl)
        Clock.schedule_once(_fade, 1.8)


# ── Analytics Screen ──────────────────────────────────────────────────────────
class AnalyticsScreen(MDScreen):
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

        root.add_widget(MDTopAppBar(
            title="Analytics",
            md_bg_color=(0.10, 0.10, 0.14, 1),
            specific_text_color=ACCENT,
            elevation=0,
        ))

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
        stat_row = BoxLayout(size_hint_y=None, height=dp(88), spacing=dp(8))
        for label, val, color in stats:
            card = MDCard(
                orientation='vertical',
                spacing=dp(4),
                padding=dp(8),
                md_bg_color=CARD,
                radius=[dp(10)],
            )
            vl = MDLabel(text=f"[b]{val}[/b]", markup=True,
                         font_size=dp(22), theme_text_color="Custom", text_color=color,
                         halign='center', valign='middle')
            vl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            ll = MDLabel(text=label, font_size=dp(10),
                         theme_text_color="Custom", text_color=SUBTEXT,
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
        year_row = BoxLayout(size_hint_y=None, height=dp(88), spacing=dp(8))
        for label, val, color in year_stats:
            card = MDCard(
                orientation='vertical',
                spacing=dp(4),
                padding=dp(8),
                md_bg_color=CARD,
                radius=[dp(10)],
            )
            vl = MDLabel(text=f"[b]{val}[/b]", markup=True,
                         font_size=dp(22), theme_text_color="Custom", text_color=color,
                         halign='center', valign='middle')
            vl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            ll = MDLabel(text=label, font_size=dp(9),
                         theme_text_color="Custom", text_color=SUBTEXT,
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
            lbl = MDLabel(text=bar_label, font_size=dp(10),
                          theme_text_color="Custom", text_color=SUBTEXT,
                          size_hint_y=None, height=dp(16), halign='left', valign='middle')
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            inner.add_widget(lbl)
            prog_bar = MDProgressBar(
                value=bar_pct,
                max=100,
                color=bar_color,
                size_hint_y=None,
                height=dp(14),
            )
            inner.add_widget(prog_bar)

        overlap_lbl = MDLabel(
            text=f"• {overlap} titles on both Plex and Letterboxd watchlist",
            font_size=dp(10), theme_text_color="Custom", text_color=GOLD,
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
            gl = MDLabel(text=genre, font_size=dp(11),
                         theme_text_color="Custom", text_color=TEXT,
                         size_hint_x=0.4, halign='left', valign='middle')
            gl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            cl = MDLabel(text=str(cnt), font_size=dp(11),
                         theme_text_color="Custom", text_color=SUBTEXT,
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
            lbl = MDLabel(text=f"[b]{country}[/b]  —  {cnt} titles",
                          markup=True, font_size=dp(12),
                          theme_text_color="Custom", text_color=TEXT,
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
            lbl = MDLabel(text=f"{day}: {cnt} movies",
                          font_size=dp(12), theme_text_color="Custom", text_color=TEXT,
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
            lbl = MDLabel(text=text, markup=True, font_size=dp(13),
                          theme_text_color="Custom", text_color=color,
                          size_hint_y=None, height=dp(30),
                          halign='left', valign='middle')
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            inner.add_widget(lbl)

        scroll.add_widget(inner)
        root.add_widget(scroll)
        self.add_widget(root)


# ── Settings Screen ───────────────────────────────────────────────────────────
class SettingsScreen(MDScreen):
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

        root.add_widget(MDTopAppBar(
            title="Settings",
            md_bg_color=(0.10, 0.10, 0.14, 1),
            specific_text_color=ACCENT,
            elevation=0,
        ))

        self._status_lbl = MDLabel(text="", font_size=dp(10),
                                   theme_text_color="Custom", text_color=GOLD,
                                   size_hint_y=None, height=dp(20),
                                   halign='center', valign='middle')
        self._status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        root.add_widget(self._status_lbl)

        scroll = ScrollView()
        inner  = BoxLayout(orientation='vertical', size_hint_y=None,
                           spacing=dp(6), padding=[dp(10), dp(6)])
        inner.bind(minimum_height=inner.setter('height'))

        sections = [
            ("PLEX SERVER", [
                ("plex_url",   "Plex Server URL",   "http://192.168.1.100:32400", False),
                ("plex_token", "Plex Token",         "xxxxxxxxxxxxxxxx",           True),
            ]),
            ("LETTERBOXD", [
                ("lb_username", "Letterboxd Username", "@yourusername", False),
            ]),
            ("SYNOLOGY NAS (Services)", [
                ("dsm_port",      "DSM Port",           "5000",                False),
                ("dsm_username",  "NAS Username",       "admin",               False),
                ("dsm_password",  "NAS Password",       "your password",       True),
                ("qbit_project",  "VPN+qBit Project",   "qbittorrent-gluetun",  False),
                ("arr_project",   "Arr Stack Project",  "arr-apps",            False),
            ]),
            ("RADARR (Movie Downloads)", [
                ("radarr_url",     "Radarr URL",  "http://192.168.4.201:7878", False),
                ("radarr_api_key", "Radarr API Key", "your-radarr-api-key",    True),
            ]),
            ("PROWLARR (Indexer Proxy)", [
                ("prowlarr_url",     "Prowlarr URL",     "http://192.168.4.201:9696", False),
                ("prowlarr_api_key", "Prowlarr API Key", "your-prowlarr-api-key",     True),
            ]),
            ("QBITTORRENT (Download Client)", [
                ("qbit_url",      "qBit Web UI URL", "http://192.168.4.201:8080", False),
                ("qbit_username", "qBit Username",   "admin",                     False),
                ("qbit_password", "qBit Password",   "adminadmin",                True),
            ]),
            ("TMDB (Movie Posters)", [
                ("tmdb_key", "TMDB API Key", "Get free key at themoviedb.org", False),
            ]),
            ("STREAMING SERVICES (Coming Soon)", [
                ("netflix_token", "Netflix Token",      "Not connected", False),
                ("disney_token",  "Disney+ Token",      "Not connected", False),
                ("prime_token",   "Prime Video Token",  "Not connected", False),
            ]),
        ]

        for section_title, fields in sections:
            inner.add_widget(SectionLabel(text=section_title))
            for key, field_name, placeholder, is_pass in fields:
                inp = MDTextField(
                    hint_text=field_name,
                    helper_text=placeholder,
                    helper_text_mode="on_focus",
                    password=is_pass,
                    mode="rectangle",
                    font_size=dp(12),
                    size_hint_y=None,
                    height=dp(46),
                    line_color_normal=(*SUBTEXT[:3], 0.5),
                    line_color_focus=ACCENT,
                    hint_text_color_normal=SUBTEXT,
                    text_color_normal=TEXT,
                )
                self._inputs[key] = inp
                inner.add_widget(inp)

        # Services control
        inner.add_widget(Widget(size_hint_y=None, height=dp(8)))
        inner.add_widget(SectionLabel(text="SERVICE CONTROL"))
        svc_note = MDLabel(
            text="NAS IP is read from your Plex URL. Requires DSM credentials above.",
            font_size=dp(10), theme_text_color="Custom", text_color=SUBTEXT,
            size_hint_y=None, height=dp(24),
            halign='left', valign='middle')
        svc_note.bind(size=lambda w, s: setattr(w, 'text_size', s))
        inner.add_widget(svc_note)

        self._svc_rows = {}
        for svc_key, svc_label in [('plex',      'Plex Media Server'),
                                    ('qbit_proj', 'VPN + qBittorrent'),
                                    ('arr_proj',  'Prowlarr / Sonarr / Radarr')]:
            wrapper = BoxLayout(orientation='vertical', size_hint_y=None,
                                height=dp(64), spacing=dp(2),
                                padding=[dp(4), dp(4), dp(4), 0])
            name_lbl = MDLabel(text=svc_label, font_size=dp(13),
                               theme_text_color="Custom", text_color=TEXT,
                               size_hint_y=None, height=dp(22),
                               halign='left', valign='bottom')
            name_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            ctrl_row = BoxLayout(size_hint_y=None, height=dp(36), spacing=dp(2))
            status_lbl = MDLabel(text="• unknown", font_size=dp(11),
                                 theme_text_color="Custom", text_color=SUBTEXT,
                                 halign='left', valign='middle')
            status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            play_b = MDIconButton(icon="play",   theme_icon_color="Custom",
                                  icon_color=GREEN,   size_hint_x=None)
            stop_b = MDIconButton(icon="stop",   theme_icon_color="Custom",
                                  icon_color=ACCENT,  size_hint_x=None)
            ref_b  = MDIconButton(icon="refresh", theme_icon_color="Custom",
                                  icon_color=ACCENT2, size_hint_x=None)
            _key = svc_key
            play_b.bind(on_press=lambda *_, k=_key: self._svc_action(k, 'start'))
            stop_b.bind(on_press=lambda *_, k=_key: self._svc_action(k, 'stop'))
            ref_b.bind( on_press=lambda *_, k=_key: self._refresh_svc_status_single(k))
            ctrl_row.add_widget(status_lbl)
            ctrl_row.add_widget(play_b)
            ctrl_row.add_widget(stop_b)
            ctrl_row.add_widget(ref_b)
            wrapper.add_widget(name_lbl)
            wrapper.add_widget(ctrl_row)
            inner.add_widget(wrapper)
            self._svc_rows[svc_key] = {'status_lbl': status_lbl}

        refresh_all_btn = MDRaisedButton(
            text="Refresh All",
            md_bg_color=CARD,
            theme_text_color="Custom", text_color=ACCENT2,
            size_hint=(None, None), height=dp(36),
        )
        refresh_all_btn.bind(on_press=lambda *_: self._refresh_svc_status())
        ref_row = BoxLayout(size_hint_y=None, height=dp(44))
        ref_row.add_widget(Widget())
        ref_row.add_widget(refresh_all_btn)
        ref_row.add_widget(Widget())
        inner.add_widget(ref_row)

        self._svc_status_lbl = MDLabel(
            text="", font_size=dp(9), theme_text_color="Custom", text_color=SUBTEXT,
            size_hint_y=None, height=dp(20), halign='center', valign='middle')
        self._svc_status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        inner.add_widget(self._svc_status_lbl)

        save_btn = MDRaisedButton(
            text="Save & Connect",
            md_bg_color=ACCENT2,
            theme_text_color="Custom", text_color=TEXT,
            size_hint=(None, None), height=dp(44),
        )
        save_btn.bind(on_press=self._save)
        save_row = BoxLayout(size_hint_y=None, height=dp(56))
        save_row.add_widget(Widget())
        save_row.add_widget(save_btn)
        save_row.add_widget(Widget())
        inner.add_widget(save_row)

        # Export / Import settings
        inner.add_widget(SectionLabel(text="BACKUP & RESTORE"))

        export_btn = MDRaisedButton(
            text="Export Settings",
            md_bg_color=CARD,
            theme_text_color="Custom", text_color=ACCENT2,
            size_hint=(None, None), height=dp(36),
        )
        export_btn.bind(on_press=self._export_settings)
        export_row = BoxLayout(size_hint_y=None, height=dp(44))
        export_row.add_widget(Widget())
        export_row.add_widget(export_btn)
        export_row.add_widget(Widget())
        inner.add_widget(export_row)

        export_hint = MDLabel(
            text="Saves to /sdcard/Download/cinequeue_settings.json",
            font_size=dp(11), theme_text_color="Custom", text_color=SUBTEXT,
            size_hint_y=None, height=dp(22), halign='center', valign='middle')
        export_hint.bind(size=lambda w, s: setattr(w, 'text_size', s))
        inner.add_widget(export_hint)

        self._import_path_inp = MDTextField(
            hint_text="Import from file path",
            helper_text="e.g. /sdcard/Download/cinequeue_settings.json",
            helper_text_mode="on_focus",
            mode="rectangle",
            font_size=dp(12),
            size_hint_y=None,
            height=dp(46),
            line_color_normal=(*SUBTEXT[:3], 0.5),
            line_color_focus=ACCENT,
            hint_text_color_normal=SUBTEXT,
            text_color_normal=TEXT,
        )
        inner.add_widget(self._import_path_inp)

        import_btn = MDRaisedButton(
            text="Import Settings",
            md_bg_color=CARD,
            theme_text_color="Custom", text_color=GREEN,
            size_hint=(None, None), height=dp(36),
        )
        import_btn.bind(on_press=self._import_settings)
        import_row = BoxLayout(size_hint_y=None, height=dp(44))
        import_row.add_widget(Widget())
        import_row.add_widget(import_btn)
        import_row.add_widget(Widget())
        inner.add_widget(import_row)

        scroll.add_widget(inner)
        root.add_widget(scroll)
        self.add_widget(root)

    def _ensure_storage_permission(self):
        """Request MANAGE_EXTERNAL_STORAGE on Android 11+, legacy perms on older.
        Returns True if permission is already granted (or not on Android)."""
        try:
            from android.permissions import Permission, check_permission, request_permissions
            import android
            if android.api_version >= 30:
                # Android 11+: check MANAGE_EXTERNAL_STORAGE via Environment
                from jnius import autoclass
                Environment = autoclass('android.os.Environment')
                if Environment.isExternalStorageManager():
                    return True
                # Redirect user to the all-files-access settings page
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                Settings = autoclass('android.provider.Settings')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                intent.setData(Uri.parse('package:org.cinequeue.cinequeue'))
                PythonActivity.mActivity.startActivity(intent)
                self.set_status("Grant 'All files access', then retry", ACCENT2)
                return False
            else:
                # Android 10 and below
                if not check_permission(Permission.READ_EXTERNAL_STORAGE):
                    request_permissions([Permission.READ_EXTERNAL_STORAGE,
                                         Permission.WRITE_EXTERNAL_STORAGE])
                    self.set_status("Storage permission requested — retry", ACCENT2)
                    return False
                return True
        except Exception:
            # Not on Android, proceed
            return True

    def _export_settings(self, *_):
        if not self._ensure_storage_permission():
            return
        try:
            src = Settings._file()
            if not os.path.exists(src):
                self._autosave()
            dst_dir = '/sdcard/Download'
            if not os.path.isdir(dst_dir):
                dst_dir = os.path.expanduser('~')
            dst = os.path.join(dst_dir, 'cinequeue_settings.json')
            import shutil
            shutil.copy2(src, dst)
            self.set_status(f"Exported to {dst}", GREEN)
        except Exception as e:
            self.set_status(f"Export failed: {e}", ACCENT)

    def _import_settings(self, *_):
        if not self._ensure_storage_permission():
            return
        path = self._import_path_inp.text.strip()
        if not path:
            path = '/sdcard/Download/cinequeue_settings.json'
        try:
            if not os.path.exists(path):
                self.set_status(f"File not found: {path}", ACCENT)
                return
            with open(path) as fp:
                data = json.load(fp)
            if not isinstance(data, dict):
                self.set_status("Invalid settings file", ACCENT)
                return
            Settings.save(data)
            for key, inp in self._inputs.items():
                val = data.get(key, '')
                inp.text = val if val else ''
            self.set_status("Settings imported — tap Save & Connect", GREEN)
        except Exception as e:
            self.set_status(f"Import failed: {e}", ACCENT)

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
            self._status_lbl.text       = msg
            self._status_lbl.text_color = color

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
            self._svc_rows[key]['status_lbl'].text       = text
            self._svc_rows[key]['status_lbl'].text_color = color

    def _svc_action(self, key, action):
        client, err = self._make_syno_client()
        if not client:
            self._svc_status_lbl.text  = err
            self._svc_status_lbl.text_color = ACCENT
            return
        self._set_svc_status(key, f"• {action}ing…", GOLD)

        def on_done(result):
            success = result.get('success', False)
            if success:
                self._set_svc_status(key, '• running' if action == 'start' else '• stopped',
                                    GREEN if action == 'start' else SUBTEXT)
            else:
                code = result.get('error', {}).get('code', '?')
                if code == 2104:
                    self._set_svc_status(key, '• build failed', ACCENT)
                    Clock.schedule_once(lambda dt: setattr(
                        self._svc_status_lbl, 'text',
                        'Fix in DSM → Container Manager → Project'), 0)
                    Clock.schedule_once(lambda dt: setattr(
                        self._svc_status_lbl, 'text_color', GOLD), 0)
                else:
                    self._set_svc_status(key, f'• error {code}', ACCENT)

        def on_error(e):
            msg = "• timed out" if 'timed out' in str(e).lower() or 'timeout' in str(e).lower() else "• error"
            self._set_svc_status(key, msg, ACCENT)
            self._svc_status_lbl.text  = f"{key}: {e}"
            self._svc_status_lbl.text_color = ACCENT

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
            self._svc_status_lbl.text_color = ACCENT
            return
        for key in ('plex', 'qbit_proj', 'arr_proj'):
            self._set_svc_status(key, "• checking…", GOLD)

        def check_all():
            try:
                status = client.plex_status()
                color  = GREEN if 'running' in status.lower() else SUBTEXT
                Clock.schedule_once(lambda dt, s=status, c=color:
                    self._set_svc_status('plex', f"• {s}", c), 0)
            except Exception:
                Clock.schedule_once(lambda dt:
                    self._set_svc_status('plex', '• unreachable', ACCENT), 0)

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
                            self._set_svc_status(k, f"• {s}", c), 0)
                except Exception as e:
                    Clock.schedule_once(
                        lambda dt, k=key, e=str(e): (
                            self._set_svc_status(k, '• error', ACCENT),
                            setattr(self._svc_status_lbl, 'text', f"{k}: {e}"),
                            setattr(self._svc_status_lbl, 'text_color', ACCENT)), 0)

        threading.Thread(target=check_all, daemon=True).start()

    def _refresh_svc_status_single(self, key):
        client, err = self._make_syno_client()
        if not client:
            self._svc_status_lbl.text  = err
            self._svc_status_lbl.text_color = ACCENT
            return
        self._set_svc_status(key, "• checking…", GOLD)

        def check_one():
            try:
                if key == 'plex':
                    status = client.plex_status()
                    color  = GREEN if 'running' in status.lower() else SUBTEXT
                    Clock.schedule_once(lambda dt, s=status, c=color:
                        self._set_svc_status('plex', f"• {s}", c), 0)
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
                        self._set_svc_status(k, f"• {s}", c), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt, k=key:
                    self._set_svc_status(k, '• error', ACCENT), 0)

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
            merged, new = MovieCache.merge(_plex_movies, movies)
            _plex_movies = merged
            _find_intersection(_plex_movies, _lb_movies)
            MovieCache.save(_plex_movies, _lb_movies, _lb_stats)
            self.set_status(f"Plex: {len(merged)} movies (+{len(new)} new)", GREEN)
            _notify_refresh()
        def on_err(e):
            self.set_status(f"Plex error: {e}", ACCENT)
        fetch_plex_async(url, token, on_done, on_err)

    def _fetch_lb(self, username):
        self.set_status("Loading Letterboxd watchlist…")
        def on_done(movies):
            global _lb_movies
            merged, new = MovieCache.merge(_lb_movies, movies)
            _lb_movies = merged
            _find_intersection(_plex_movies, _lb_movies)
            MovieCache.save(_plex_movies, _lb_movies, _lb_stats)
            self.set_status(f"Letterboxd: {len(merged)} movies (+{len(new)} new)", GREEN)
            _notify_refresh()
        def on_err(e):
            self.set_status(f"Letterboxd error: {e}", ACCENT)
        fetch_lb_async(username, on_done, on_err)

    def _fetch_tmdb_posters(self, api_key):
        all_movies = _plex_movies + _lb_movies
        missing = [m for m in all_movies
                   if not m.get('tmdb_enriched') and not m.get('poster_url')]
        if not missing:
            return
        self.set_status(f"Fetching {len(missing)} posters from TMDB…")
        def on_done():
            self.set_status("Posters updated", GREEN)
            _notify_refresh()
        fetch_tmdb_posters_async(all_movies, api_key, on_done)


# ── Welcome / Sign-In Screen ──────────────────────────────────────────────────
class WelcomeScreen(MDScreen):
    def __init__(self, on_connect=None, **kwargs):
        super().__init__(**kwargs)
        self._on_connect = on_connect
        self._inputs     = {}
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical', padding=dp(24), spacing=dp(12))

        root.add_widget(Widget(size_hint_y=0.08))

        title = MDLabel(text="[b]CineQueue[/b]", markup=True,
                        font_size=dp(34),
                        theme_text_color="Custom", text_color=ACCENT,
                        size_hint_y=None, height=dp(50),
                        halign='center', valign='middle')
        title.bind(size=lambda w, s: setattr(w, 'text_size', s))
        root.add_widget(title)

        sub = MDLabel(
            text="Your personal movie queue\nPowered by Plex + Letterboxd",
            font_size=dp(13), theme_text_color="Custom", text_color=SUBTEXT,
            halign='center', valign='middle',
            size_hint_y=None, height=dp(44))
        sub.bind(size=lambda w, s: setattr(w, 'text_size', s))
        root.add_widget(sub)

        root.add_widget(Widget(size_hint_y=0.04))

        fields = [
            ("plex_url",    "Plex Server URL",    "http://192.168.1.100:32400", False),
            ("plex_token",  "Plex Token",          "xxxxxxxxxxxxxxxx",           True),
            ("lb_username", "Letterboxd Username", "@yourusername",              False),
        ]
        for key, label, hint, is_pass in fields:
            inp = MDTextField(
                hint_text=label,
                helper_text=hint,
                helper_text_mode="on_focus",
                password=is_pass,
                mode="rectangle",
                size_hint_y=None,
                height=dp(56),
                line_color_normal=(*SUBTEXT[:3], 0.5),
                line_color_focus=ACCENT,
                hint_text_color_normal=SUBTEXT,
                text_color_normal=TEXT,
            )
            self._inputs[key] = inp
            root.add_widget(inp)

        self._status_lbl = MDLabel(text="", font_size=dp(10),
                                    theme_text_color="Custom", text_color=ACCENT,
                                    size_hint_y=None, height=dp(20),
                                    halign='center', valign='middle')
        self._status_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        root.add_widget(self._status_lbl)

        connect_btn = MDRaisedButton(
            text="Connect",
            md_bg_color=ACCENT2,
            theme_text_color="Custom", text_color=TEXT,
            size_hint_y=None, height=dp(52),
            size_hint_x=1,
        )
        skip_btn = MDFlatButton(
            text="Skip — use demo data",
            theme_text_color="Custom", text_color=SUBTEXT,
            size_hint_y=None, height=dp(40),
            size_hint_x=1,
        )
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
        self._changed = bool(new_movies)
        if self._tmdb_key and new_movies:
            fetch_tmdb_enrich_async(new_movies, self._tmdb_key, self._finish)
        else:
            self._finish()

    def _finish(self):
        MovieCache.save(_plex_movies, _lb_movies, _lb_stats)
        Clock.schedule_once(lambda dt: self._on_done(self._changed), 0)


# ── App ───────────────────────────────────────────────────────────────────────
class CineQueueApp(MDApp):
    _REFRESH_INTERVAL = 120  # seconds between background syncs

    def build(self):
        # ── Theme — must be configured BEFORE any KivyMD widget is created ───
        self.theme_cls.theme_style   = "Dark"
        self.theme_cls.primary_palette = "Red"
        self.theme_cls.accent_palette  = "Blue"
        self.theme_cls.material_style  = "M3"

        Window.clearcolor = BG

        font_path = resource_find('NotoEmoji-Regular.ttf') or 'NotoEmoji-Regular.ttf'
        LabelBase.register('NotoEmoji', fn_regular=font_path)

        Settings.load()
        DownloadQueue.load()

        self._settings_screen = SettingsScreen(name='settings')
        self._watch_screen    = WatchScreen(name='watch')
        self._downloads_screen = DownloadsScreen(name='downloads')
        self._refresh_timer   = None
        self._prev_tab        = None

        # Root switches between _pre_sm (welcome/loading) and _nav (main tabs)
        self._root = BoxLayout(orientation='vertical')

        # Pre-auth ScreenManager (Welcome / Loading — no bottom nav)
        self._pre_sm = ScreenManager(transition=SlideTransition())
        self._root.add_widget(self._pre_sm)

        has_creds = bool(Settings.get('plex_url') or Settings.get('lb_username'))

        if has_creds:
            cached_plex, cached_lb, cached_stats = MovieCache.load()
            if cached_plex or cached_lb:
                global _plex_movies, _lb_movies, _lb_stats
                _plex_movies = cached_plex
                _lb_movies   = cached_lb
                _lb_stats    = cached_stats
                _find_intersection(_plex_movies, _lb_movies)

            loading = LoadingScreen(name='loading', on_ready=self._on_load_done)
            self._pre_sm.add_widget(loading)
            self._pre_sm.current = 'loading'
            plex_url   = Settings.get('plex_url')
            plex_token = Settings.get('plex_token')
            lb_user    = Settings.get('lb_username')
            tmdb_key   = Settings.get('tmdb_key')
            Clock.schedule_once(
                lambda dt: loading.start(
                    plex_url, plex_token, lb_user, tmdb_key,
                    cached_plex=cached_plex, cached_lb=cached_lb), 0.3)
        else:
            welcome = WelcomeScreen(name='welcome', on_connect=self._on_welcome_done)
            self._pre_sm.add_widget(welcome)
            self._pre_sm.current = 'welcome'

        return self._root

    def _launch_main(self):
        """Swap pre_sm out of root and insert MDBottomNavigation."""
        nav = MDBottomNavigation()
        nav.md_bg_color = (0.10, 0.10, 0.14, 1)
        self._nav = nav

        tab_defs = [
            ('watch',     'Watch',     'television-play', self._watch_screen),
            ('recommend', 'Suggest',   'cards',           RecommendScreen(name='recommend')),
            ('analytics', 'Stats',     'chart-bar',       AnalyticsScreen(name='analytics')),
            ('downloads', 'Downloads', 'download',        self._downloads_screen),
            ('settings',  'Settings',  'cog',             self._settings_screen),
        ]
        self._tab_screens = {}
        for tab_name, tab_text, tab_icon, screen in tab_defs:
            item = MDBottomNavigationItem(
                name=tab_name,
                text=tab_text,
                icon=tab_icon,
            )
            item.add_widget(screen)
            nav.add_widget(item)
            self._tab_screens[tab_name] = screen

        nav.bind(on_switch_tabs=self._relay_lifecycle)

        self._root.clear_widgets()
        self._root.add_widget(nav)

    def _relay_lifecycle(self, nav, tab, *args):
        """Forward on_enter / on_leave to screens when tabs switch."""
        if self._prev_tab:
            screen = self._tab_screens.get(self._prev_tab.name)
            if screen and hasattr(screen, 'on_leave'):
                screen.on_leave()
        screen = self._tab_screens.get(tab.name)
        if screen and hasattr(screen, 'on_enter'):
            screen.on_enter()
        self._prev_tab = tab

    def _on_load_done(self):
        self._launch_main()
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
        syncer = _BackgroundSyncer(
            plex_url, plex_token, lb_user, tmdb_key,
            cached_plex=list(_plex_movies),
            cached_lb=list(_lb_movies),
            on_done=self._on_bg_sync_done)
        syncer.run()

    def _on_bg_sync_done(self, changed=False):
        if changed:
            _notify_refresh()
            missing = [m for m in list(_plex_movies + _lb_movies)
                       if m.get('poster_url') and not (
                           m.get('local_poster') and os.path.exists(m['local_poster']))]
            if missing:
                def _fetch_new():
                    ctx = ssl._create_unverified_context()
                    for m in missing:
                        PosterCache.ensure(m, ctx)
                    MovieCache.save(_plex_movies, _lb_movies, _lb_stats)
                threading.Thread(target=_fetch_new, daemon=True).start()
        if not self._refresh_timer:
            self._start_refresh_timer()

    def _on_welcome_done(self, skip=False):
        if skip:
            self._launch_main()
            return
        # After welcome: use loading screen to preload
        plex_url   = Settings.get('plex_url')
        plex_token = Settings.get('plex_token')
        lb_user    = Settings.get('lb_username')
        tmdb_key   = Settings.get('tmdb_key')
        if 'loading' not in [s.name for s in self._pre_sm.screens]:
            loading = LoadingScreen(name='loading', on_ready=self._on_load_done)
            self._pre_sm.add_widget(loading)
        self._pre_sm.current = 'loading'
        loading = self._pre_sm.get_screen('loading')
        Clock.schedule_once(
            lambda dt: loading.start(plex_url, plex_token, lb_user, tmdb_key), 0.2)


if __name__ == '__main__':
    CineQueueApp().run()
