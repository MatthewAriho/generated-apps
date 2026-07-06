"""Plex Media Server API client."""

import json
import ssl
import urllib.request
from datetime import datetime

from .constants import CARD


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
        self.url = url.rstrip('/')
        self.token = token
        self._ctx = ssl._create_unverified_context()

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
