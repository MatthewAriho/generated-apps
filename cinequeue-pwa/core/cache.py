"""Movie cache — persists movie data across launches to avoid re-fetching."""

import json
import os
from datetime import datetime


class MovieCache:
    _path = None
    _TMDB_FIELDS = ('poster_url', 'poster_color', 'director', 'runtime',
                    'genre', 'country', 'year')
    _EMPTY_VALS = (None, '', 'Unknown', '?', 0)

    @classmethod
    def init(cls, config_dir=None):
        if config_dir is None:
            config_dir = os.path.expanduser('~')
        cls._path = os.path.join(config_dir, 'cinequeue_movies.json')

    @classmethod
    def _file(cls):
        if cls._path is None:
            cls.init()
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
                lb = d.get('lb', [])
                stats = d.get('lb_stats', {})
                if plex or lb:
                    return plex, lb, stats
        except Exception:
            pass
        return [], [], {}

    @classmethod
    def save(cls, plex_movies, lb_movies, lb_stats):
        try:
            with open(cls._file(), 'w') as fp:
                json.dump({
                    'plex': plex_movies,
                    'lb': lb_movies,
                    'lb_stats': lb_stats,
                    'saved_at': datetime.now().isoformat(),
                }, fp)
        except Exception:
            pass

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
                for field in cls._TMDB_FIELDS:
                    if updated.get(field) in cls._EMPTY_VALS and \
                            old.get(field) not in cls._EMPTY_VALS:
                        updated[field] = old[field]
                merged.append(updated)
            else:
                merged.append(m)
                new.append(m)
        return merged, new
