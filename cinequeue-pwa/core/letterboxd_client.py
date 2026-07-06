"""Letterboxd scraper — watchlist and profile stats."""

import re
import ssl
import urllib.request
from datetime import datetime

from .constants import CARD


class LetterboxdClient:
    def __init__(self, username):
        self.username = username.lstrip('@').strip()
        self._ctx = ssl._create_unverified_context()

    def fetch_watchlist(self):
        movies = []
        page = 1

        while True:
            url = f"https://letterboxd.com/{self.username}/watchlist/page/{page}/"

            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

            try:
                with urllib.request.urlopen(req, timeout=20, context=self._ctx) as r:
                    html = r.read().decode('utf-8', errors='replace')
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    break
                raise

            poster_divs = re.findall(
                r'<div[^>]+class="react-component"[^>]+data-target-link="/film/[^>]+>',
                html
            )

            if not poster_divs:
                break

            for tag in poster_divs:
                slug_m = re.search(r'data-target-link="/film/([^/]+)/"', tag)
                slug = slug_m.group(1) if slug_m else None
                if not slug:
                    continue

                title = slug.replace('-', ' ').title()

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

            if not has_next:
                break

            page += 1

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

            m = re.search(r'data-stat="film-count"[^>]*>\s*<span[^>]*>([\d,]+)', html)
            if m:
                stats['total_films'] = int(m.group(1).replace(',', ''))

            year = datetime.now().year
            year_url = f"https://letterboxd.com/{self.username}/films/year/{year}/"
            req2 = urllib.request.Request(year_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req2, timeout=20, context=self._ctx) as r2:
                year_html = r2.read().decode('utf-8', errors='replace')

            film_divs = re.findall(r'<li[^>]+class="[^"]*poster-container[^"]*"', year_html)
            stats['watched_this_year'] = len(film_divs)
        except Exception:
            pass
        return stats
