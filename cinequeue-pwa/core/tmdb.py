"""TMDB enrichment and poster caching — fills metadata gaps in movie records."""

import hashlib
import json
import os
import re
import ssl
import urllib.parse
import urllib.request

from .constants import TMDB_COUNTRY


class PosterCache:
    """Downloads poster images to local storage for caching."""

    _base_dir = None

    @classmethod
    def init(cls, base_dir=None):
        if base_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls._base_dir = base_dir

    @classmethod
    def _dir(cls):
        if cls._base_dir is None:
            cls.init()
        d = os.path.join(cls._base_dir, 'cinequeue_posters')
        os.makedirs(d, exist_ok=True)
        return d

    @staticmethod
    def local_path_for_url(url):
        """Return a stable local filename for a remote URL."""
        name = re.sub(r'[^a-zA-Z0-9._-]', '_', url.split('/')[-1]) or 'poster.jpg'
        prefix = hashlib.md5(url.encode()).hexdigest()[:8]
        return f"{prefix}_{name}"

    @classmethod
    def local_path(cls, url):
        """Return the full local file path for a remote URL."""
        return os.path.join(cls._dir(), cls.local_path_for_url(url))

    @classmethod
    def download(cls, url, ctx=None):
        """Download url to local cache. Returns local path, or None on failure."""
        path = cls.local_path(url)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path
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

    @classmethod
    def ensure(cls, movie, ctx=None):
        """Download poster for movie if not already cached. Sets local_poster key."""
        url = movie.get('poster_url')
        if not url:
            return
        if movie.get('local_poster') and os.path.exists(movie['local_poster']):
            return
        local = cls.download(url, ctx)
        if local:
            movie['local_poster'] = local


def is_bad_movie(m):
    """Return True if movie data looks too broken to display."""
    if not m.get('title') or len(m['title'].strip()) < 2:
        return True
    if m.get('runtime', 0) < 1:
        return True
    unknown = sum(1 for v in [m.get('genre'), m.get('director')]
                  if str(v).strip() in ('Unknown', '?', '', 'None'))
    return unknown >= 2


def find_intersection(plex_movies, lb_movies):
    """Tag each movie with on_plex / on_lb flags for intersection highlighting."""
    lb_keys = {m['title'].lower().strip() for m in lb_movies}
    px_keys = {m['title'].lower().strip() for m in plex_movies}
    for m in plex_movies:
        m['on_plex'] = True
        m['on_lb'] = m['title'].lower().strip() in lb_keys
    for m in lb_movies:
        m['on_lb'] = True
        m['on_plex'] = m['title'].lower().strip() in px_keys


def enrich_movies(movies, api_key):
    """Synchronous TMDB enrichment: fills poster, runtime, genre, director, country, year.
    Downloads poster images to local storage."""
    search = "https://api.themoviedb.org/3/search/movie"
    detail = "https://api.themoviedb.org/3/movie"
    img = "https://image.tmdb.org/t/p/w342"

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
            PosterCache.ensure(m, _ctx)
            continue

        try:
            t = urllib.parse.quote(m['title'])
            yr = m.get('year', '')
            url = f"{search}?api_key={api_key}&query={t}&year={yr}&language=en-US"
            req = urllib.request.Request(url, headers={'Accept': 'application/json'})
            with urllib.request.urlopen(req, timeout=10, context=_ctx) as r:
                results = json.loads(r.read()).get('results', [])

            if not results:
                continue

            top = results[0]
            tmdb_id = top.get('id')

            if not m.get('overview') and top.get('overview'):
                m['overview'] = top['overview']
            if top.get('vote_average') and not m.get('rating'):
                m['rating'] = round(top['vote_average'], 1)
            if not m.get('poster_url') and top.get('poster_path'):
                m['poster_url'] = img + top['poster_path']
            if not m.get('year') and top.get('release_date'):
                try:
                    m['year'] = int(top['release_date'][:4])
                except Exception:
                    pass

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
                        m['country'] = TMDB_COUNTRY.get(raw, raw[:2].upper() if raw else '?')

            PosterCache.ensure(m, _ctx)

        except Exception:
            pass
