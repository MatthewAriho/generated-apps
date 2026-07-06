"""Synology DSM 7 REST API client — Plex package and Docker project control."""

import json
import socket
import ssl
import urllib.parse
import urllib.request


class SynologyClient:
    """Controls Plex (package) and Docker containers via DSM 7 REST API."""

    _AUTH_ERRORS = {
        400: "Wrong username or password",
        401: "Account disabled",
        402: "Permission denied — add user to administrators group in DSM Control Panel",
        403: "2FA is enabled — create a DSM user without 2FA for the app",
        404: "2FA code incorrect",
        407: "Account locked (too many attempts) — unlock in DSM Control Panel",
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
    }

    def __init__(self, nas_ip, port, username, password):
        self._nas_ip = nas_ip
        self._port = str(port)
        self.username = username
        self.password = password
        self._sid = None
        self._ctx = ssl._create_unverified_context()
        self.base = self._resolve_base()

    def _resolve_base(self):
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
            raise
        except OSError:
            https_base = f"https://{self._nas_ip}:{int(self._port)+1}/webapi/entry.cgi"
            alt_url = url.replace(self.base, https_base)
            with urllib.request.urlopen(
                    urllib.request.Request(alt_url), timeout=timeout,
                    context=self._ctx) as r:
                data = json.loads(r.read())
            self.base = https_base
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
            msg = self._AUTH_ERRORS.get(code, f"code {code}")
            raise Exception(msg)

    def _req(self, params, timeout=10):
        if not self._sid:
            self._login()
        result = self._get(self._url(dict(params, _sid=self._sid)), timeout)
        if not result.get('success'):
            code = result.get('error', {}).get('code')
            if code in (106, 119):
                self._sid = None
                self._login()
                result = self._get(self._url(dict(params, _sid=self._sid)), timeout)
        return result

    # ── Plex package ─────────────────────────────────────────────────────────
    def plex_status(self):
        d = self._req({'api': 'SYNO.Core.Package', 'method': 'list',
                       'version': '2', 'additional': '["status"]'}, timeout=60)
        for pkg in d.get('data', {}).get('packages', []):
            if pkg.get('id') == 'PlexMediaServer':
                return pkg.get('additional', {}).get('status', 'unknown')
        return 'not installed'

    def _try_pkg_control(self, action, timeout):
        params = {
            'api': 'SYNO.Core.Package.Control',
            'method': action,
            'version': '1',
            'id': 'PlexMediaServer',
        }
        return self._req(params, timeout=timeout)

    def plex_start(self):
        return self._try_pkg_control('start', timeout=60)

    def plex_stop(self):
        return self._try_pkg_control('stop', timeout=60)

    # ── Docker Compose projects ──────────────────────────────────────────────
    _PROJECT_APIS = ('SYNO.Docker.Project',)

    def _list_projects(self):
        for api in self._PROJECT_APIS:
            for attempt in range(2):
                try:
                    r = self._req({'api': api, 'method': 'list', 'version': '1'}, timeout=20)
                    if r.get('success'):
                        data = r.get('data', {})
                        if isinstance(data, dict):
                            return list(data.values())
                        if isinstance(data, list):
                            return data
                    break
                except (socket.timeout, TimeoutError):
                    if attempt == 0:
                        continue
                except Exception:
                    break
        return []

    def _project_by_name(self, name):
        for p in self._list_projects():
            pname = (p.get('name') or p.get('project_name') or
                     p.get('compose_project_name') or '')
            if pname == name:
                return p
        return None

    def project_status(self, name):
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
                results[name] = 'running'
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
        return self._req({
            'api': 'SYNO.Docker.Project',
            'method': method,
            'version': '1',
            'id': project_id,
        }, timeout=timeout)

    def project_start(self, name):
        return self._project_action('start', name, timeout=60)

    def project_stop(self, name):
        return self._project_action('stop', name, timeout=60)


def nas_ip_from_plex_url(plex_url):
    """Extract hostname/IP from the stored Plex URL."""
    try:
        return urllib.parse.urlparse(plex_url).hostname or ''
    except Exception:
        return ''
