"""Prowlarr API v1 client — indexer search proxy.

Currently NOT used in the download pipeline — Radarr handles movie searching.
Kept for future use: manual release browsing, fallback search, health checks.
"""

import json
import ssl
import urllib.parse
import urllib.request


class ProwlarrClient:
    CATEGORIES_MOVIE = [2000, 2010, 2020, 2030, 2040, 2045, 2050, 2060]

    def __init__(self, base_url, api_key):
        self._base = base_url.rstrip('/')
        self._key = api_key

    def _get(self, path, params=None, timeout=15):
        qs = urllib.parse.urlencode(params or {})
        url = f"{self._base}{path}?{qs}" if qs else f"{self._base}{path}"
        req = urllib.request.Request(url, headers={'X-Api-Key': self._key})
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as r:
            return json.loads(r.read().decode())

    def search(self, title, year=None):
        query = f"{title} {year}" if year else title
        cats = ','.join(str(c) for c in self.CATEGORIES_MOVIE)
        results = self._get('/api/v1/search', {
            'query': query, 'type': 'search',
            'indexerIds': '-1', 'categories': cats,
        })
        return results if isinstance(results, list) else []

    def indexers(self):
        return self._get('/api/v1/indexer')
