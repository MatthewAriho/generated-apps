"""qBittorrent Web API v2 client — download tracking and control."""

import json
import ssl
import urllib.parse
import urllib.request


class QBitClient:
    def __init__(self, base_url, username='admin', password='adminadmin'):
        self._base = base_url.rstrip('/')
        self._user = username
        self._pass = password
        self._sid = None

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
        qs = urllib.parse.urlencode(params or {})
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
        """Pause/Stop a torrent by hash so it stops seeding."""
        data = urllib.parse.urlencode({'hashes': hash_str.lower()}).encode()
        headers = {'Cookie': f'SID={self._sid}'} if self._sid else {}
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        req = urllib.request.Request(f"{self._base}/api/v2/torrents/stop",
                                     data=data, method="POST", headers=headers)
        try:
            with urllib.request.urlopen(req, context=self._ctx(), timeout=10) as r:
                return r.read()
        except Exception:
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
