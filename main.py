"""
CineQueue — Movie Picker App
Plex + Letterboxd integration with real API connections
"""

import random, json, os, re, ssl, threading
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
_plex_movies = list(MOCK_PLEX)
_lb_movies   = list(MOCK_LB)
_refresh_cbs = []

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
        return cls._data.get(key, default)

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

    def fetch_watchlist(self):
        url = f"https://letterboxd.com/{self.username}/watchlist/rss/"
        req = urllib.request.Request(url, headers={'User-Agent': 'CineQueue/1.0'})
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()

        raw_str = raw.decode('utf-8', errors='replace')
        m = re.search(r'xmlns:letterboxd=["\']([^"\']+)["\']', raw_str)
        lb_ns = m.group(1) if m else 'https://a.letterboxd.com/dtd/letterboxd-2.0.dtd'

        root    = ET.fromstring(raw)
        channel = root.find('channel')
        if channel is None:
            return []

        movies = []
        for item in channel.findall('item'):
            title = (item.findtext(f'{{{lb_ns}}}filmTitle') or
                     item.findtext('title', '')).strip()
            if not title:
                continue
            year_s = item.findtext(f'{{{lb_ns}}}filmYear', '')
            try:
                year = int(year_s)
            except Exception:
                year = 0

            desc = item.findtext('description', '')
            pm = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', desc)
            poster_url = pm.group(1) if pm else None

            lb_added = ''
            pub = item.findtext('pubDate', '').strip()
            for fmt in ('%a, %d %b %Y %H:%M:%S %z', '%a, %d %b %Y %H:%M:%S %Z'):
                try:
                    lb_added = datetime.strptime(pub, fmt).strftime('%Y-%m-%d')
                    break
                except Exception:
                    pass

            movies.append({
                'title':        title,
                'year':         year,
                'genre':        'Unknown',
                'country':      '?',
                'rating':       0.0,
                'lb_added':     lb_added,
                'poster_url':   poster_url,
                'poster_color': CARD,
                'runtime':      0,
                'director':     'Unknown',
                'source':       'letterboxd',
            })
        return movies

# ── Async Fetch Helpers ───────────────────────────────────────────────────────
def fetch_plex_async(url, token, on_done, on_error):
    def run():
        try:
            movies = PlexClient(url, token).fetch_movies()
            Clock.schedule_once(lambda dt: on_done(movies), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: on_error(str(e)), 0)
    threading.Thread(target=run, daemon=True).start()

def fetch_lb_async(username, on_done, on_error):
    def run():
        try:
            movies = LetterboxdClient(username).fetch_watchlist()
            Clock.schedule_once(lambda dt: on_done(movies), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: on_error(str(e)), 0)
    threading.Thread(target=run, daemon=True).start()

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

# ── TMDB Poster Fetch ─────────────────────────────────────────────────────────
def fetch_tmdb_posters_async(movies, api_key, on_done):
    """Fetch missing poster_url fields via TMDB search for each movie."""
    def run():
        base = "https://api.themoviedb.org/3/search/movie"
        img  = "https://image.tmdb.org/t/p/w342"
        updated = False
        for m in movies:
            if m.get('poster_url'):
                continue
            try:
                title = urllib.parse.quote(m['title'])
                year  = m.get('year', '')
                url   = f"{base}?api_key={api_key}&query={title}&year={year}"
                req   = urllib.request.Request(url, headers={'Accept': 'application/json'})
                with urllib.request.urlopen(req, timeout=10) as r:
                    data = json.loads(r.read())
                results = data.get('results', [])
                if results and results[0].get('poster_path'):
                    m['poster_url'] = img + results[0]['poster_path']
                    updated = True
            except Exception:
                pass
        if updated:
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

class NavBar(BoxLayout):
    def __init__(self, manager, **kwargs):
        super().__init__(**kwargs)
        self.manager = manager
        for label, name in [("Watch","watch"),("Recommend","recommend"),
                             ("Analytics","analytics"),("Settings","settings")]:
            btn = Button(text=label, font_size=dp(11), bold=True,
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
                                       keep_ratio=True, size_hint=(1, 1)))
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


class MoviePosterCard(FloatLayout):
    """Poster tile: image fills card, title overlaid at bottom (Recommend-style)."""
    def __init__(self, movie, on_tap=None, show_lb_badge=False, **kwargs):
        super().__init__(size_hint=(None, None),
                         size=(dp(120), dp(200)), **kwargs)
        self._on_tap     = on_tap
        self._movie      = movie
        self._touch_down = None

        # Solid background colour — shown while image loads or when no poster
        with self.canvas.before:
            Color(*movie.get('poster_color', CARD))
            self._bg = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd_bg, size=self._upd_bg)

        # Poster image — only added when URL exists; no fallback content (avoids artifact)
        url = movie.get('poster_url')
        if url:
            self.add_widget(AsyncImage(
                source=url, allow_stretch=True, keep_ratio=True,
                size_hint=(1, 1), pos_hint={'x': 0, 'y': 0}))

        # Semi-translucent title overlay pinned to the bottom
        overlay_h = dp(58) if show_lb_badge else dp(44)
        overlay = BoxLayout(orientation='vertical',
                            size_hint=(1, None), height=overlay_h,
                            pos_hint={'x': 0, 'y': 0},
                            padding=[dp(4), dp(4)])
        with overlay.canvas.before:
            Color(0, 0, 0, 0.65)
            self._ov = Rectangle(pos=overlay.pos, size=overlay.size)
        overlay.bind(pos=lambda w, _: self._upd_ov(w),
                     size=lambda w, _: self._upd_ov(w))

        title_lbl = Label(text=movie['title'], font_size=dp(9), color=TEXT,
                          halign='center', valign='middle',
                          size_hint=(1, None), height=dp(32))
        title_lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
        overlay.add_widget(title_lbl)

        if show_lb_badge:
            badge = Label(text="LB · Not on Plex", font_size=dp(7), color=GOLD,
                          size_hint=(1, None), height=dp(12),
                          halign='center', valign='middle')
            overlay.add_widget(badge)

        self.add_widget(overlay)

    def _upd_bg(self, *_):
        self._bg.pos  = self.pos
        self._bg.size = self.size

    def _upd_ov(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(0, 0, 0, 0.65)
            Rectangle(pos=w.pos, size=w.size)

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

# ── Watch Screen ──────────────────────────────────────────────────────────────
class WatchScreen(Screen):
    SORT_OPTIONS = ["Plex Date", "LB Date", "Unique", "Foreign/EN", "Random", "Runtime"]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_count = 3
        self.active_sorts = {"Random"}
        self._count_lbl = None
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
        plex_dot = Label(text=f"{E('🔵')} PLEX", markup=True,
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
        inner.add_widget(SectionLabel(text=f"{E('🎬')} WATCH NOW  (on Plex)"))
        self._watch_container = BoxLayout(orientation='horizontal',
                                          size_hint=(None, None),
                                          height=dp(210), width=dp(360),
                                          spacing=dp(8))
        ws = ScrollView(size_hint_y=None, height=dp(210), do_scroll_y=False,
                        do_scroll_x=True)
        ws.add_widget(self._watch_container)
        inner.add_widget(ws)

        # Recommended
        inner.add_widget(SectionLabel(text=f"{E('⭐')} RECOMMENDED  (Plex + Letterboxd)"))
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
        dl_btn = Button(text="⬇ Download  (Coming Soon)", font_size=dp(11),
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
        self._watch_container.clear_widgets()
        self._rec_container.clear_widgets()

        watch = self._sort_movies(_plex_movies)
        rec   = self._sort_movies(_plex_movies + _lb_movies)

        if not watch:
            empty = Label(text="Nothing to show here",
                          font_size=dp(13), color=SUBTEXT,
                          halign='center', valign='middle')
            empty.bind(size=lambda w, s: setattr(w, 'text_size', s))
            self._watch_container.add_widget(empty)
        else:
            for m in watch:
                self._watch_container.add_widget(
                    MoviePosterCard(m, on_tap=self._show_detail))
        self._watch_container.width = max(
            dp(130) * max(len(watch), 1) + dp(8) * max(len(watch)-1, 0), Window.width)

        if not rec:
            empty = Label(text="Nothing to show here",
                          font_size=dp(13), color=SUBTEXT,
                          halign='center', valign='middle')
            empty.bind(size=lambda w, s: setattr(w, 'text_size', s))
            self._rec_container.add_widget(empty)
        else:
            for m in rec:
                is_plex = m.get('source') == 'plex'
                card = MoviePosterCard(m, on_tap=self._show_detail,
                                       show_lb_badge=not is_plex)
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
            f"Rating: {E('⭐')} {movie['rating']}  |  Runtime: {movie.get('runtime','?')} min",
        ]:
            lbl = Label(text=line, markup=True, font_size=dp(12), color=TEXT,
                        halign='left', valign='middle',
                        size_hint_y=None, height=dp(22))
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            content.add_widget(lbl)

        watch_btn = Button(text=f"{E('🎬')} Watch on Plex", markup=True,
                           size_hint_y=None, height=dp(40),
                           background_normal="", background_color=GREEN,
                           color=TEXT, font_size=dp(13), bold=True)
        close_btn = Button(text="Close", size_hint_y=None, height=dp(36),
                           background_normal="", background_color=CARD,
                           color=SUBTEXT, font_size=dp(12))
        content.add_widget(watch_btn)
        content.add_widget(close_btn)

        popup = Popup(title=movie['title'], content=content,
                      size_hint=(0.9, 0.75),
                      background_color=(0.10, 0.10, 0.14, 1), title_color=TEXT)
        watch_btn.bind(on_press=lambda *_: popup.dismiss())
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

        on_plex = movie.get('source') == 'plex'
        avail = Label(
            text=(f"{E('✅')} Available on Plex" if on_plex
                  else f"{E('🚫')} Not on server"),
            markup=True, font_size=dp(10),
            color=GREEN if on_plex else GOLD,
            halign='left', valign='middle',
            size_hint_y=None, height=dp(18))
        avail.bind(size=lambda w, s: setattr(w, 'text_size', s))
        info.add_widget(avail)
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

        stats = [
            ("Watched",   str(total_w),          GREEN),
            ("Unwatched", str(total_uw),          ACCENT),
            ("On Plex",   str(len(_plex_movies)), ACCENT2),
            ("LB Only",   str(len(_lb_movies)),   GOLD),
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

        inner.add_widget(SectionLabel(
            text=f"WATCH PROGRESS  ({pct}% complete)"))
        prog = Widget(size_hint_y=None, height=dp(20))
        with prog.canvas:
            Color(*CARD)
            RoundedRectangle(pos=prog.pos, size=(prog.width, dp(14)),
                             radius=[dp(7)])
            Color(*GREEN)
            RoundedRectangle(pos=prog.pos,
                             size=(prog.width * pct / 100, dp(14)),
                             radius=[dp(7)])
        inner.add_widget(prog)

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
            (f"{E('⭐')} Avg Rating: {avg_r:.1f} / 10", GOLD),
            (f"{E('🕐')} Avg Runtime: {avg_rt} min  ({avg_rt//60}h {avg_rt%60}m)", ACCENT2),
        ]:
            lbl = Label(text=text, markup=True, font_size=dp(13), color=color,
                        size_hint_y=None, height=dp(30),
                        halign='left', valign='middle')
            lbl.bind(size=lambda w, s: setattr(w, 'text_size', s))
            inner.add_widget(lbl)

        scroll.add_widget(inner)
        root.add_widget(scroll)
        self.add_widget(root)

    def _redraw(self, w):
        w.canvas.before.clear()
        with w.canvas.before:
            Color(*CARD)
            RoundedRectangle(pos=w.pos, size=w.size, radius=[dp(10)])


# ── Settings Screen ───────────────────────────────────────────────────────────
class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._inputs     = {}   # key -> TextInput
        self._status_lbl = None
        self._build_ui()
        Clock.schedule_once(lambda dt: self._load_values(), 0.1)

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
            ("DOCKER SERVICES", [
                ("prowlarr_url",    "Prowlarr URL",    "http://localhost:9696", False),
                ("qbit_url",        "qBittorrent URL", "http://localhost:8080", False),
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

        # Docker control
        inner.add_widget(SectionLabel(text="DOCKER CONTROL"))
        docker_note = Label(
            text="Start/stop your Plex, Prowlarr, and qBittorrent containers.",
            font_size=dp(10), color=SUBTEXT, size_hint_y=None, height=dp(30),
            halign='left', valign='middle')
        docker_note.bind(size=lambda w, s: setattr(w, 'text_size', s))
        inner.add_widget(docker_note)

        docker_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        start_btn = Button(text=f"{E('🎬')} Start All", markup=True,
                           background_normal="",
                           background_color=GREEN, color=TEXT,
                           font_size=dp(12), bold=True)
        stop_btn  = Button(text=f"{E('🕐')} Stop All", markup=True,
                           background_normal="",
                           background_color=ACCENT, color=TEXT,
                           font_size=dp(12), bold=True)
        start_btn.bind(on_press=lambda *_: self._docker_action("start"))
        stop_btn.bind(on_press=lambda *_: self._docker_action("stop"))
        docker_row.add_widget(start_btn)
        docker_row.add_widget(stop_btn)
        inner.add_widget(docker_row)

        self._docker_status = Label(
            text="Docker: status unknown", font_size=dp(10), color=SUBTEXT,
            size_hint_y=None, height=dp(24), halign='left', valign='middle')
        self._docker_status.bind(size=lambda w, s: setattr(w, 'text_size', s))
        inner.add_widget(self._docker_status)

        save_btn = Button(text=f"{E('💾')} Save & Connect", markup=True,
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

    def set_status(self, msg, color=GOLD):
        if self._status_lbl:
            self._status_lbl.text  = msg
            self._status_lbl.color = color

    def _docker_action(self, action):
        self._docker_status.text  = f"Docker: '{action}' sent (not yet implemented)"
        self._docker_status.color = GOLD

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


# ── App ───────────────────────────────────────────────────────────────────────
class CineQueueApp(App):
    def build(self):
        Window.clearcolor = BG

        # Register NotoEmoji so [font=NotoEmoji]...[/font] markup works
        font_path = resource_find('NotoEmoji-Regular.ttf') or 'NotoEmoji-Regular.ttf'
        LabelBase.register('NotoEmoji', fn_regular=font_path)

        Settings.load()

        self._sm              = ScreenManager(transition=SlideTransition())
        self._settings_screen = SettingsScreen(name='settings')
        self._watch_screen    = WatchScreen(name='watch')

        has_creds = bool(Settings.get('plex_url') or Settings.get('lb_username'))

        if not has_creds:
            welcome = WelcomeScreen(name='welcome', on_connect=self._on_welcome_done)
            self._sm.add_widget(welcome)
            self._sm.current = 'welcome'

        for s in [self._watch_screen,
                  RecommendScreen(name='recommend'),
                  AnalyticsScreen(name='analytics'),
                  self._settings_screen]:
            self._sm.add_widget(s)

        if has_creds:
            self._sm.current = 'watch'

        self._nav = NavBar(manager=self._sm)
        # Hide nav during welcome screen
        self._nav.size_hint_y = None
        self._nav.height      = dp(0) if not has_creds else dp(56)

        root = BoxLayout(orientation='vertical')
        root.add_widget(self._sm)
        root.add_widget(self._nav)

        if has_creds:
            self._auto_connect()

        return root

    def _on_welcome_done(self, skip=False):
        self._sm.current   = 'watch'
        self._nav.height   = dp(56)
        if not skip:
            plex_url   = Settings.get('plex_url')
            plex_token = Settings.get('plex_token')
            lb_user    = Settings.get('lb_username')
            if plex_url and plex_token:
                Clock.schedule_once(
                    lambda dt: self._settings_screen._fetch_plex(plex_url, plex_token), 0.5)
            if lb_user:
                Clock.schedule_once(
                    lambda dt: self._settings_screen._fetch_lb(lb_user), 1)

    def _auto_connect(self):
        plex_url   = Settings.get('plex_url')
        plex_token = Settings.get('plex_token')
        lb_user    = Settings.get('lb_username')
        tmdb_key   = Settings.get('tmdb_key')
        if plex_url and plex_token:
            Clock.schedule_once(
                lambda dt: self._settings_screen._fetch_plex(plex_url, plex_token), 1)
        if lb_user:
            Clock.schedule_once(
                lambda dt: self._settings_screen._fetch_lb(lb_user), 1.5)
        if tmdb_key:
            Clock.schedule_once(
                lambda dt: self._settings_screen._fetch_tmdb_posters(tmdb_key), 2)


if __name__ == '__main__':
    CineQueueApp().run()
