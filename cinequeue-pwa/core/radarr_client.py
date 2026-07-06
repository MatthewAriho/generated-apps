"""Radarr API v3 client — movie management and search.

Flow: lookup(title) -> get quality profile + root folder -> add_movie() ->
      Radarr auto-searches indexers -> sends to download client -> poll queue()
"""

import json
import ssl
import urllib.parse
import urllib.request


class RadarrClient:
    def __init__(self, base_url, api_key):
        self._base = base_url.rstrip('/')
        self._key = api_key

    def _ctx(self):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def _req(self, method, path, params=None, body=None, timeout=15):
        qs = urllib.parse.urlencode(params or {})
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
