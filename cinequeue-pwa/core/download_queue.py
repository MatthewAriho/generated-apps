"""Persistent download queue — manages movie download lifecycle via Radarr + qBittorrent.

Status flow per entry:
  queued -> searching -> results_found / no_results -> grabbing -> downloading -> complete / failed
"""

import json
import os
import re
import time
from datetime import datetime

from .constants import CARD
from .settings import Settings
from .radarr_client import RadarrClient
from .qbit_client import QBitClient


# Module-level queue list (loaded from disk)
_download_queue = []


def get_queue():
    """Return the current download queue list."""
    return _download_queue


class DownloadQueue:
    _FILE = 'cinequeue_downloads.json'

    @staticmethod
    def _path():
        d = os.path.dirname(os.path.abspath(__file__))
        # Store in the app directory, not in core/
        return os.path.join(os.path.dirname(d), DownloadQueue._FILE)

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
                          f"{movie['title']}_{movie.get('year', '')}".lower())
        if any(e['id'] == entry_id for e in _download_queue):
            return None
        entry = {
            'id':           entry_id,
            'title':        movie['title'],
            'year':         movie.get('year', ''),
            'genre':        movie.get('genre', ''),
            'director':     movie.get('director', ''),
            'poster_url':   movie.get('poster_url', ''),
            'poster_color': list(movie.get('poster_color') or CARD),
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
    def search_and_grab(entry_id):
        """Synchronous: Radarr lookup -> add movie -> returns updated entry.
        The caller (FastAPI endpoint) handles async scheduling."""
        radarr_url = Settings.get('radarr_url', '')
        radarr_key = Settings.get('radarr_api_key', '')

        entry = next((e for e in _download_queue if e['id'] == entry_id), None)
        if not entry:
            return None

        if not radarr_url or not radarr_key:
            DownloadQueue.update(entry_id, status='failed',
                                 error='Radarr URL/API key not set in Settings')
            return entry

        client = RadarrClient(radarr_url, radarr_key)

        # 1. Lookup movie in Radarr (TMDB-backed)
        DownloadQueue.update(entry_id, status='searching', error='')
        try:
            candidates = client.lookup(entry['title'], entry.get('year'))
            if not candidates:
                DownloadQueue.update(entry_id, status='no_results',
                                     error='Movie not found in Radarr/TMDB lookup')
                return entry
            year = entry.get('year')
            best_candidate = next(
                (c for c in candidates
                 if str(c.get('year', '')) == str(year)
                 and c.get('title', '').lower() == entry['title'].lower()),
                candidates[0])
            tmdb_id = best_candidate.get('tmdbId') or best_candidate.get('id')
            DownloadQueue.update(entry_id, status='results_found',
                                  chosen={'title': best_candidate.get('title'),
                                          'year': best_candidate.get('year'),
                                          'tmdbId': tmdb_id})
        except Exception as e:
            DownloadQueue.update(entry_id, status='failed', error=str(e))
            return entry

        # 2. Get quality profile + root folder
        try:
            profiles = client.quality_profiles()
            root_folders = client.root_folders()
            if not profiles or not root_folders:
                raise RuntimeError('No quality profiles or root folders in Radarr')
            profile_id = profiles[0]['id']
            root_path = root_folders[0]['path']
        except Exception as e:
            DownloadQueue.update(entry_id, status='failed',
                                  error=f"Radarr config error: {e}")
            return entry

        # 3. Add movie to Radarr + trigger automatic search
        radarr_id = None
        try:
            DownloadQueue.update(entry_id, status='grabbing')
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
        except Exception as e:
            err = str(e)
            if '400' in err or 'already' in err.lower():
                try:
                    existing = client.lookup(entry['title'], entry.get('year', ''))
                    match = next(
                        (m for m in existing
                         if str(m.get('year', '')) == str(entry.get('year', ''))
                         and m.get('title', '').lower() == entry['title'].lower()),
                        existing[0] if existing else None)
                    radarr_id = match.get('id') if match else None
                except Exception:
                    radarr_id = None
                DownloadQueue.update(entry_id, status='downloading',
                                     radarr_id=radarr_id,
                                     error='Already in Radarr — monitoring active')
            else:
                DownloadQueue.update(entry_id, status='failed', error=err)
                return entry

        # 4. Check initial status
        if radarr_id:
            try:
                movie_rec = client.get_movie(radarr_id)
                queue_recs = client.queue(radarr_id)
                has_file = movie_rec.get('hasFile', False)
                in_queue = len(queue_recs) > 0
                if has_file:
                    DownloadQueue.update(entry_id, status='complete', progress=1.0)
                elif in_queue:
                    q = queue_recs[0]
                    size_tot = q.get('size', 0)
                    size_left = q.get('sizeleft', size_tot)
                    prog = (1.0 - size_left / size_tot) if size_tot else 0.0
                    DownloadQueue.update(entry_id, status="downloading",
                                          progress=prog,
                                          qbit_status=q.get('status', ''))
                else:
                    DownloadQueue.update(entry_id, status="grabbing",
                                          error="Searching indexers...",
                                          grabbing_since=time.time())
            except Exception:
                pass

        return entry

    @staticmethod
    def poll_progress():
        """Poll Radarr queue + qBittorrent for download progress on active entries.
        Returns list of updated entry IDs."""
        radarr_url = Settings.get('radarr_url', '')
        radarr_key = Settings.get('radarr_api_key', '')
        qbit_url = Settings.get('qbit_url', '')
        qbit_user = Settings.get('qbit_username', 'admin')
        qbit_pass = Settings.get('qbit_password', 'adminadmin')
        active = [e for e in _download_queue
                  if e['status'] in ('downloading', 'grabbing')]
        if not active:
            return []

        updated_ids = []

        # 1. Poll Radarr queue
        radarr_queue = []
        if radarr_url and radarr_key:
            try:
                radarr_queue = RadarrClient(radarr_url, radarr_key).queue()
            except Exception:
                pass

        # 2. Poll qBittorrent
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

        for entry in active:
            updates = {}

            # Match in Radarr queue
            rq_match = None
            if entry.get('radarr_id'):
                rq_match = next((r for r in radarr_queue
                                 if r.get('movieId') == entry['radarr_id']), None)
            if not rq_match:
                rq_match = next((r for r in radarr_queue
                                 if r.get('title', '').lower() ==
                                    entry['title'].lower()), None)
            if rq_match:
                size_left = rq_match.get('sizeleft', 0)
                size_tot = rq_match.get('size', 0)
                prog = (1.0 - size_left / size_tot) if size_tot else 0.0
                state = rq_match.get('status', '')
                updates.update(progress=prog, qbit_status=state,
                               size_bytes=int(size_tot))

            # Match in qBit
            qb_match = None
            stored_hash = (entry.get('qbit_hash') or '').lower()
            if stored_hash:
                qb_match = next((t for t in torrents
                                 if t['hash'].lower() == stored_hash), None)
            if not qb_match:
                slug = entry['title'].lower().replace(' ', '.')
                qb_match = next((t for t in torrents
                                 if slug[:12] in t.get('name', '').lower()), None)
            if qb_match:
                prog = qb_match.get('progress', updates.get('progress', 0.0))
                state = qb_match.get('state', updates.get('qbit_status', ''))
                updates.update(
                    qbit_hash=qb_match['hash'],
                    progress=prog,
                    qbit_status=state,
                    eta_secs=qb_match.get('eta', -1),
                    size_bytes=qb_match.get('size', updates.get('size_bytes', 0)))

            # Check movie record for completion
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
                                except Exception:
                                    pass
                except Exception:
                    pass

            if updates:
                prog = updates.get('progress', entry.get('progress', 0.0))
                if 'status' not in updates:
                    updates['status'] = 'complete' if prog >= 1.0 else 'downloading'
                if prog == 0.0 and not updates.get('qbit_hash') and not entry.get('grabbing_since'):
                    updates['grabbing_since'] = time.time()
                elif prog > 0.0 and 'grabbing_since' not in updates:
                    updates['grabbing_since'] = None

                if prog == 1.0 and qb:
                    hash_to_stop = updates.get('qbit_hash') or entry.get('qbit_hash')
                    if hash_to_stop:
                        try:
                            qb.stop_torrent(hash_to_stop)
                        except Exception:
                            pass
                DownloadQueue.update(entry['id'], **updates)
                updated_ids.append(entry['id'])
            else:
                if not entry.get('grabbing_since') and entry.get('progress', 0.0) == 0.0:
                    DownloadQueue.update(entry['id'], grabbing_since=time.time())

        return updated_ids
