"""
Running App — My Runs (Strava/CSV import) + Interval Training
"""
import os, json, csv, time, threading, webbrowser
import sys, ssl
import urllib.request, urllib.parse
from datetime import datetime, timezone
import traceback

# Use certifi's CA bundle on Android where the system store isn't available
try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL_CTX = None

def _urlopen(req, timeout=30):
    if _SSL_CTX:
        return urllib.request.urlopen(req, timeout=timeout, context=_SSL_CTX)
    return urllib.request.urlopen(req, timeout=timeout)

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import StringProperty, BooleanProperty
from kivy.metrics import dp
from kivy.graphics import Color, Line, Rectangle, Ellipse, RoundedRectangle
from kivy.core.text import Label as CoreLabel


# ── Screen subclasses ────────────────────────────────────────────────────────

class HomeScreen(Screen): pass
class RunListScreen(Screen): pass
class RunDetailScreen(Screen): pass
class SplitAnalysisScreen(Screen): pass
class IntervalScreen(Screen): pass


class RunCard(ButtonBehavior, BoxLayout):
    run_name      = StringProperty('Run')
    run_date      = StringProperty('')
    distance_text = StringProperty('0.00 km')
    time_text     = StringProperty('0:00')
    pace_text     = StringProperty('--:-- /km')
    hr_text       = StringProperty('')
    elev_text     = StringProperty('')
    source_badge  = StringProperty('')


# ── Android helpers ──────────────────────────────────────────────────────────

def _android_context():
    from jnius import autoclass
    return autoclass('org.kivy.android.PythonActivity').mActivity

def pulse_vibrate():
    try:
        from jnius import autoclass, cast
        ctx = _android_context()
        Vibrator = autoclass('android.os.Vibrator')
        vib = cast(Vibrator, ctx.getSystemService('vibrator'))
        vib.vibrate(600)
    except Exception:
        pass

def send_notification(title, body):
    try:
        from jnius import autoclass
        ctx = _android_context()
        sdk = autoclass('android.os.Build$VERSION').SDK_INT
        CTX = autoclass('android.content.Context')
        NM  = autoclass('android.app.NotificationManager')
        nm  = ctx.getSystemService(CTX.NOTIFICATION_SERVICE)
        cid = 'running_interval'
        if sdk >= 26:
            NC = autoclass('android.app.NotificationChannel')
            nm.createNotificationChannel(NC(cid, 'Interval Alerts', NM.IMPORTANCE_HIGH))
            NB = autoclass('android.app.Notification$Builder')(ctx, cid)
        else:
            NB = autoclass('android.app.Notification$Builder')(ctx)
        NB.setSmallIcon(17301543)
        NB.setContentTitle(title)
        NB.setContentText(body)
        NB.setAutoCancel(True)
        nm.notify(42, NB.build())
    except Exception:
        pass

def notify_phase_complete(title, body):
    pulse_vibrate()
    send_notification(title, body)


# ── Formatting helpers ───────────────────────────────────────────────────────

def fmt_time(s, dec=False):
    m = int(s) // 60
    sec = s % 60
    return f"{m:02d}:{sec:04.1f}" if dec else f"{m:02d}:{int(sec):02d}"

def fmt_pace(s_per_km):
    if s_per_km <= 0 or s_per_km > 3600:
        return "--:--"
    return f"{int(s_per_km)//60}:{int(s_per_km)%60:02d}"

def fmt_dist(m):
    return f"{m/1000:.2f} km"

def fmt_date(dt):
    if dt is None:
        return ''
    try:
        return dt.strftime('%a %-d %b  %H:%M')
    except Exception:
        return dt.strftime('%a %d %b  %H:%M')

def safe_float(v):
    try:
        return float(v)
    except Exception:
        return 0.0


# ── Data model ───────────────────────────────────────────────────────────────

class RunData:
    def __init__(self):
        self.id               = ''
        self.name             = 'Run'
        self.date             = None
        self.activity_type    = 'Run'
        self.distance_m       = 0.0
        self.elapsed_time_s   = 0.0
        self.moving_time_s    = 0.0
        self.avg_speed_ms     = 0.0
        self.avg_hr           = 0.0
        self.max_hr           = 0.0
        self.elevation_gain_m = 0.0
        self.source           = 'csv'   # 'strava', 'strava_csv', 'samsung', 'fitbit', 'csv'
        self.strava_id        = None
        self.streams          = None    # dict from Strava streams API

    @property
    def avg_pace_s_per_km(self):
        if self.avg_speed_ms > 0:
            return 1000.0 / self.avg_speed_ms
        if self.moving_time_s > 0 and self.distance_m > 0:
            return (self.moving_time_s / self.distance_m) * 1000.0
        return 0.0

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name,
            'date': self.date.isoformat() if self.date else None,
            'activity_type': self.activity_type,
            'distance_m': self.distance_m,
            'elapsed_time_s': self.elapsed_time_s,
            'moving_time_s': self.moving_time_s,
            'avg_speed_ms': self.avg_speed_ms,
            'avg_hr': self.avg_hr, 'max_hr': self.max_hr,
            'elevation_gain_m': self.elevation_gain_m,
            'source': self.source, 'strava_id': self.strava_id,
            'streams': self.streams,
        }

    @classmethod
    def from_dict(cls, d):
        r = cls()
        for k in ('id','name','activity_type','source','strava_id','streams'):
            setattr(r, k, d.get(k, getattr(r, k)))
        for k in ('distance_m','elapsed_time_s','moving_time_s','avg_speed_ms',
                  'avg_hr','max_hr','elevation_gain_m'):
            setattr(r, k, safe_float(d.get(k, 0)))
        ds = d.get('date')
        r.date = datetime.fromisoformat(ds) if ds else None
        return r

    @classmethod
    def from_strava_api(cls, d):
        r = cls()
        r.strava_id     = str(d['id'])
        r.id            = r.strava_id
        r.name          = d.get('name', 'Run')
        r.activity_type = d.get('type', 'Run')
        ds = d.get('start_date_local', d.get('start_date', ''))
        try:
            r.date = datetime.fromisoformat(ds.replace('Z', '+00:00'))
        except Exception:
            r.date = datetime.now()
        r.distance_m       = safe_float(d.get('distance', 0))
        r.elapsed_time_s   = safe_float(d.get('elapsed_time', 0))
        r.moving_time_s    = safe_float(d.get('moving_time', 0))
        r.avg_speed_ms     = safe_float(d.get('average_speed', 0))
        r.avg_hr           = safe_float(d.get('average_heartrate', 0))
        r.max_hr           = safe_float(d.get('max_heartrate', 0))
        r.elevation_gain_m = safe_float(d.get('total_elevation_gain', 0))
        r.source           = 'strava'
        return r


class RunDataStore:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.runs = []
        self._load()

    def _path(self):
        return os.path.join(self.data_dir, 'runs.json')

    def _load(self):
        try:
            with open(self._path()) as f:
                self.runs = [RunData.from_dict(d) for d in json.load(f)]
        except Exception:
            self.runs = []

    def save(self):
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self._path(), 'w') as f:
                json.dump([r.to_dict() for r in self.runs], f)
        except Exception:
            pass

    def add_runs(self, new_runs):
        existing = {r.id for r in self.runs}
        added = 0
        for r in new_runs:
            if r.id and r.id not in existing:
                self.runs.append(r)
                existing.add(r.id)
                added += 1
        _tz_min = datetime.min.replace(tzinfo=timezone.utc)
        def _sort_key(r):
            d = r.date
            if d is None:
                return _tz_min
            if d.tzinfo is None:
                return d.replace(tzinfo=timezone.utc)
            return d
        self.runs.sort(key=_sort_key, reverse=True)
        self.save()
        return added

    def update_streams(self, run_id, streams):
        for r in self.runs:
            if r.id == run_id:
                r.streams = streams
                self.save()
                return


# ── Strava OAuth + API ───────────────────────────────────────────────────────

class StravaClient:
    AUTH_URL   = 'https://www.strava.com/oauth/authorize'
    TOKEN_URL  = 'https://www.strava.com/api/v3/oauth/token'
    API_BASE   = 'https://www.strava.com/api/v3'
    try:
        import android  # only exists inside p4a / on-device
        REDIRECT = 'runningapp://auth/callback'
    except ImportError:
        REDIRECT = 'http://localhost:8080/callback'

    def __init__(self, client_id='', client_secret=''):
        self.client_id     = client_id
        self.client_secret = client_secret
        self.access_token  = None
        self.refresh_token = None
        self.token_expiry  = 0

    @property
    def authenticated(self):
        return bool(self.access_token)

    def auth_url(self):
        p = urllib.parse.urlencode({
            'client_id':       self.client_id,
            'redirect_uri':    self.REDIRECT,
            'response_type':   'code',
            'scope':           'activity:read_all',
            'approval_prompt': 'auto',
        })
        return f"{self.AUTH_URL}?{p}"

    def open_browser_for_auth(self):
        """On desktop: start a local HTTP server to catch the OAuth callback.
        On Android: open browser and let the deep-link intent be caught."""
        _on_android = (self.REDIRECT != 'http://localhost:8080/callback')
        if not _on_android:
            import socketserver
            from http.server import BaseHTTPRequestHandler

            class CallbackHandler(BaseHTTPRequestHandler):
                def do_GET(handler):
                    parsed = urllib.parse.urlparse(handler.path)
                    params = urllib.parse.parse_qs(parsed.query)
                    code  = params.get('code',  [None])[0]
                    error = params.get('error', [None])[0]
                    handler.send_response(200)
                    handler.end_headers()
                    handler.wfile.write(b"<h1>Auth complete. Return to the app.</h1>")
                    if code:
                        print(f"Code for clock - {code}")
                        Clock.schedule_once(lambda dt: self._on_desktop_auth(code))
                    else:
                        print(f"Auth error - {error}")
                        Clock.schedule_once(lambda dt: self._on_desktop_auth_error(error))
                def log_message(self, *args): pass

            server = socketserver.TCPServer(('localhost', 8080), CallbackHandler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
        webbrowser.open(self.auth_url())

    def _on_desktop_auth(self, code):
        try:
            self._exchange(code)
            from kivy.app import App
            app = App.get_running_app()
            app.save_strava_creds()
            on_success = getattr(app, '_auth_on_success', None)
            app._auth_on_success = None
            app._auth_on_error   = None
            if on_success:
                on_success()
            else:
                app._recover_after_auth()
        except Exception as e:
            print(f"Auth error: {e}")
            try:
                from kivy.app import App
                app = App.get_running_app()
                on_error = getattr(app, '_auth_on_error', None)
                app._auth_on_success = None
                app._auth_on_error   = None
                if on_error:
                    on_error(str(e))
            except Exception:
                pass

    def _on_desktop_auth_error(self, error):
        print(f"Auth denied: {error}")
        try:
            from kivy.app import App
            app = App.get_running_app()
            on_error = getattr(app, '_auth_on_error', None)
            app._auth_on_success = None
            app._auth_on_error   = None
            if on_error:
                on_error(str(error))
        except Exception:
            pass

    def _exchange(self, code):
        print(f"Code for exchange - {code}")
        t = None
        try:
            data = urllib.parse.urlencode({
                'client_id': self.client_id, 'client_secret': self.client_secret,
                'code': code, 'grant_type': 'authorization_code',
            }).encode()
            print(f"URI data req - {data}")
            with _urlopen(urllib.request.Request(self.TOKEN_URL, data=data)) as r:
                t = json.loads(r.read())
            if t:
                self.access_token  = t['access_token']
                self.refresh_token = t['refresh_token']
                self.token_expiry  = t.get('expires_at', 0)
            print(f"access - {self.access_token}, refresh- {self.refresh_token}, token exp - {self.token_expiry}")
        except Exception as e:
            exc = e
            print(f"Data exchange failed with error: {exc}")
            self.access_token  = None
            self.refresh_token = None
            self.token_expiry  = 0
            raise exc

    def _do_token_refresh(self):
        """Exchange refresh_token for a new access_token."""
        data = urllib.parse.urlencode({
            'client_id': self.client_id, 'client_secret': self.client_secret,
            'refresh_token': self.refresh_token, 'grant_type': 'refresh_token',
        }).encode()
        print(f"Refreshing token: {self.access_token}, {self.refresh_token}")
        with _urlopen(urllib.request.Request(self.TOKEN_URL, data=data)) as r:
            t = json.loads(r.read())
        self.access_token = t['access_token']
        self.refresh_token = t.get('refresh_token', self.refresh_token)
        self.token_expiry = t.get('expires_at', 0)
        # Persist updated tokens immediately so they survive app restarts
        try:
            from kivy.app import App
            App.get_running_app().save_strava_creds()
        except Exception:
            pass

    def _get(self, path):
        # token_expiry==0 means unknown (manually pasted) — treat as expired and refresh first.
        # Also refresh proactively when within 5 minutes of known expiry.
        print(f"Authorization: Bearer {self.access_token}, Refresh {self.refresh_token}")
        if self.refresh_token and (not self.token_expiry or time.time() >= self.token_expiry - 300):
            self._do_token_refresh()
        print("Sending request")
        req = urllib.request.Request(
            f"{self.API_BASE}{path}",
            headers={'Authorization': f'Bearer {self.access_token}'}
        )
        print("Finished sending request")
        try:
            print("Pulling data")
            with _urlopen(req) as r:
                data = r.read()
                print(f"Reading return data: {data[:200]}")
                return json.loads(data)
        except urllib.error.HTTPError as e:
            print(f"Failed to pull data due to {str(e)}")
            if e.code == 401 and self.refresh_token:
                # Access token expired — refresh and retry once
                self._do_token_refresh()
                try:
                    print("Re-attempting data pull with refresh token")
                    req = urllib.request.Request(
                        f"{self.API_BASE}{path}",
                        headers={'Authorization': f'Bearer {self.access_token}'}
                    )
                    with _urlopen(req) as r:
                        data = r.read()
                        print(f"Retry return data: {data[:200]}")
                        return json.loads(data)
                except urllib.error.HTTPError as retry_e:
                    if retry_e.code == 401:
                        raise Exception(
                            '401 Unauthorized — access token expired. '
                            'Add a Refresh Token + Client ID + Client Secret in Settings so it can auto-renew.'
                        )
                    raise retry_e
            if e.code == 401:
                raise Exception(
                    '401 Unauthorized — access token expired. '
                    'Add a Refresh Token + Client ID + Client Secret in Settings so it can auto-renew.'
                )
            raise

    def fetch_activities(self, page=1, per_page=50):
        data = self._get(f'/athlete/activities?page={page}&per_page={per_page}')
        return [RunData.from_strava_api(a) for a in data
                if a.get('type') in ('Run','TrailRun','Walk','Hike','VirtualRun')]

    def fetch_streams(self, strava_id):
        keys = 'time,distance,heartrate,altitude,velocity_smooth,latlng'
        return self._get(f'/activities/{strava_id}/streams?keys={keys}&key_by_type=true')

    def to_dict(self):
        return {k: getattr(self, k) for k in
                ('client_id','client_secret','access_token','refresh_token','token_expiry')}

    @classmethod
    def from_dict(cls, d):
        c = cls(d.get('client_id',''), d.get('client_secret',''))
        c.access_token  = d.get('access_token')
        c.refresh_token = d.get('refresh_token')
        c.token_expiry  = d.get('token_expiry', 0)
        return c


# ── CSV import ───────────────────────────────────────────────────────────────

class CSVImporter:
    @staticmethod
    def detect(headers):
        h = [x.lower().strip() for x in headers]
        if 'activity id' in h or 'activity name' in h:
            return 'strava'
        if any('com.samsung' in x for x in h):
            return 'samsung'
        if 'durationms' in h or ('starttime' in h and 'logtype' in h):
            return 'fitbit'
        return 'generic'

    @classmethod
    def parse(cls, filepath):
        runs = []
        try:
            with open(filepath, newline='', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                fmt = cls.detect(reader.fieldnames or [])
                parsers = {
                    'strava':  cls._strava,
                    'samsung': cls._samsung,
                    'fitbit':  cls._fitbit,
                    'generic': cls._generic,
                }
                parser = parsers[fmt]
                for i, row in enumerate(reader):
                    r = parser(row, i)
                    if r and r.distance_m > 10:
                        runs.append(r)
        except Exception:
            pass
        return runs

    @staticmethod
    def _strava(row, i):
        r = RunData()
        r.source        = 'strava_csv'
        r.id            = row.get('Activity ID', '') or f'csv_{i}'
        r.strava_id     = row.get('Activity ID') or None
        r.name          = row.get('Activity Name', 'Run') or 'Run'
        r.activity_type = row.get('Activity Type', 'Run')
        for fmt in ('%b %d, %Y, %I:%M:%S %p', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
            try:
                r.date = datetime.strptime(row.get('Activity Date',''), fmt); break
            except Exception:
                pass
        else:
            r.date = datetime.now()
        # Distance in Strava CSV is km
        r.distance_m       = safe_float(row.get('Distance', 0)) * 1000
        r.elapsed_time_s   = safe_float(row.get('Elapsed Time', 0))
        r.moving_time_s    = safe_float(row.get('Moving Time', 0)) or r.elapsed_time_s
        # Speed in m/s
        r.avg_speed_ms     = safe_float(row.get('Average Speed', 0))
        r.avg_hr           = safe_float(row.get('Average Heart Rate', 0))
        r.max_hr           = safe_float(row.get('Max Heart Rate', 0))
        r.elevation_gain_m = safe_float(row.get('Elevation Gain', 0))
        return r

    @staticmethod
    def _samsung(row, i):
        r = RunData()
        r.source       = 'samsung'
        r.id           = f'samsung_{i}'
        r.name         = row.get('com.samsung.health.exercise.custom_name','') or 'Run'
        r.distance_m   = safe_float(row.get('com.samsung.health.exercise.distance', 0)) * 1000
        dur_ms         = safe_float(row.get('com.samsung.health.exercise.duration', 0))
        r.elapsed_time_s = dur_ms / 1000
        r.avg_hr       = safe_float(row.get('com.samsung.health.exercise.mean_heart_rate', 0))
        r.max_hr       = safe_float(row.get('com.samsung.health.exercise.max_heart_rate', 0))
        r.elevation_gain_m = safe_float(row.get('com.samsung.health.exercise.altitude_gain', 0))
        ds = row.get('com.samsung.health.exercise.start_time', '')
        try:
            r.date = datetime.fromisoformat(ds.replace('+0000','+00:00'))
        except Exception:
            r.date = datetime.now()
        return r

    @staticmethod
    def _fitbit(row, i):
        r = RunData()
        r.source     = 'fitbit'
        r.id         = f'fitbit_{i}'
        r.name       = row.get('Activities', row.get('Type', 'Run'))
        r.distance_m = safe_float(row.get('Distance (km)', row.get('Distance', 0))) * 1000
        dur = row.get('Duration', row.get('Active Duration', '0:00:00'))
        parts = dur.split(':')
        try:
            if len(parts) == 3:
                r.elapsed_time_s = int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
            elif len(parts) == 2:
                r.elapsed_time_s = int(parts[0])*60 + int(parts[1])
        except Exception:
            pass
        r.avg_hr = safe_float(row.get('Out-of-Range Minutes', row.get('Average Heart Rate', 0)))
        for fmt in ('%Y-%m-%d','%m/%d/%y','%m/%d/%Y'):
            try:
                r.date = datetime.strptime(row.get('Date',''), fmt); break
            except Exception:
                pass
        else:
            r.date = datetime.now()
        return r

    @staticmethod
    def _generic(row, i):
        r = RunData()
        r.source = 'csv'
        r.id     = f'csv_{i}'
        for k in ('name','Name','title','Title','Activity Name'):
            if row.get(k):
                r.name = row[k]; break
        for k in ('distance_km','distance','Distance','Distance (km)'):
            if row.get(k):
                r.distance_m = safe_float(row[k]) * 1000; break
        for k in ('elapsed_time','duration','Duration','Elapsed Time','time'):
            if row.get(k):
                r.elapsed_time_s = safe_float(row[k]); break
        r.avg_hr           = safe_float(row.get('avg_hr', row.get('Average Heart Rate', 0)))
        r.elevation_gain_m = safe_float(row.get('elevation_gain', row.get('Elevation Gain', 0)))
        r.date             = datetime.now()
        return r


# ── Split calculator ─────────────────────────────────────────────────────────

INTERVALS = [
    ('0.1 km',  100.0),
    ('0.25 km', 250.0),
    ('0.5 km',  500.0),
    ('1 km',    1000.0),
    ('0.5 mi',  804.67),
    ('1 mi',    1609.34),
]

def compute_splits(streams, interval_m):
    try:
        distances  = streams.get('distance',  {}).get('data', [])
        times      = streams.get('time',      {}).get('data', [])
        heartrates = streams.get('heartrate', {}).get('data', [])
        altitudes  = streams.get('altitude',  {}).get('data', [])
    except Exception:
        return []
    if len(distances) < 2 or not times:
        return []

    splits, split_num = [], 1
    target = interval_m
    prev_time  = times[0]
    prev_alt   = altitudes[0] if altitudes else 0.0
    prev_idx   = 0
    seg_hrs    = []

    for i in range(1, len(distances)):
        if i < len(heartrates) and heartrates[i]:
            seg_hrs.append(heartrates[i])

        while distances[i] >= target:
            d0, d1 = distances[i-1], distances[i]
            t0, t1 = times[i-1], times[i]
            frac = (target - d0) / (d1 - d0) if d1 != d0 else 1.0
            cross_t = t0 + frac * (t1 - t0)
            a_end   = (altitudes[i] if i < len(altitudes) else prev_alt)

            seg_time = cross_t - prev_time
            seg_dist = target - (splits[-1]['cumul_m'] if splits else 0.0)

            splits.append({
                'num':       split_num,
                'dist_m':    seg_dist,
                'time_s':    seg_time,
                'pace':      seg_time / (seg_dist / 1000) if seg_dist > 0 else 0,
                'avg_hr':    sum(seg_hrs) / len(seg_hrs) if seg_hrs else 0,
                'elev_gain': max(0.0, a_end - prev_alt),
                'cumul_m':   target,
                '_ct':       cross_t,
            })

            split_num += 1
            prev_time  = cross_t
            prev_alt   = a_end
            prev_idx   = i
            seg_hrs    = []
            target    += interval_m

    # Partial last split
    last_cumul = splits[-1]['cumul_m'] if splits else 0.0
    remaining  = distances[-1] - last_cumul
    if remaining > interval_m * 0.02:
        seg_time = times[-1] - prev_time
        a_end    = altitudes[-1] if altitudes else prev_alt
        splits.append({
            'num':       split_num,
            'dist_m':    remaining,
            'time_s':    seg_time,
            'pace':      seg_time / (remaining / 1000) if remaining > 0 else 0,
            'avg_hr':    sum(seg_hrs) / len(seg_hrs) if seg_hrs else 0,
            'elev_gain': max(0.0, a_end - prev_alt),
            'cumul_m':   distances[-1],
            '_ct':       times[-1],
        })

    return splits


def detect_intervals(streams):
    """Auto-detect on/off intervals from velocity stream data.

    Returns a dict:
      on_splits, off_splits  – list of {dist_m, time_s, avg_pace}
      cv                     – coefficient of variation (0-1); low = steady run
    Returns None if data insufficient.
    """
    distances  = streams.get('distance',        {}).get('data', [])
    velocities = streams.get('velocity_smooth', {}).get('data', [])
    times      = streams.get('time',            {}).get('data', [])
    if len(distances) < 30 or not velocities or not times:
        return None

    # Pace in s/km, cap very slow / stopped points
    raw = [min(600.0, 1000.0 / v) if v and v > 0.5 else 600.0 for v in velocities]

    # Rolling-average smoothing (~30 s window)
    W = 30
    smoothed = []
    for i in range(len(raw)):
        s = max(0, i - W // 2);  e = min(len(raw), i + W // 2 + 1)
        smoothed.append(sum(raw[s:e]) / (e - s))

    mean_p = sum(smoothed) / len(smoothed)
    std_p  = (sum((p - mean_p) ** 2 for p in smoothed) / len(smoothed)) ** 0.5
    cv     = std_p / mean_p if mean_p > 0 else 0

    # Median as on/off threshold
    threshold = sorted(smoothed)[len(smoothed) // 2]
    labels    = ['on' if p < threshold else 'off' for p in smoothed]

    # Group consecutive same-label runs
    segs, i = [], 0
    while i < len(labels):
        j = i
        while j < len(labels) and labels[j] == labels[i]:
            j += 1
        segs.append({'type': labels[i], 'si': i, 'ei': j - 1})
        i = j

    # Merge segments shorter than 45 s into their neighbour
    MIN_S = 45
    changed = True
    while changed and len(segs) > 1:
        changed = False
        out = [segs[0]]
        for sg in segs[1:]:
            if (times[sg['ei']] - times[sg['si']]) < MIN_S:
                out[-1]['ei'] = sg['ei']
                changed = True
            else:
                out.append(sg)
        segs = out

    on_splits, off_splits = [], []
    for sg in segs:
        si, ei  = sg['si'], sg['ei']
        s_dist  = distances[ei] - distances[si]
        s_time  = times[ei]     - times[si]
        if s_dist <= 0 or s_time <= 0:
            continue
        entry = {'dist_m': s_dist, 'time_s': s_time,
                 'avg_pace': s_time / (s_dist / 1000.0)}
        (on_splits if sg['type'] == 'on' else off_splits).append(entry)

    return {'on_splits': on_splits, 'off_splits': off_splits, 'cv': cv}


def pace_color(pace, avg_pace):
    """Green = faster than avg, Red = slower. Returns RGBA tuple."""
    if avg_pace <= 0 or pace <= 0:
        return (0.85, 0.85, 0.85, 1)
    diff = (pace - avg_pace) / avg_pace   # + = slower, - = faster
    diff = max(-0.20, min(0.20, diff)) / 0.20   # clamp to ±20%
    if diff < 0:  # faster → green
        return (0.2, 0.5 + 0.4 * (-diff), 0.2 + 0.2 * (-diff), 1)
    else:          # slower → red
        return (0.4 + 0.5 * diff, 0.2, 0.2, 1)


# ── Route map widget ──────────────────────────────────────────────────────────

class RouteMapWidget(Widget):
    """Canvas-drawn GPS route silhouette."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._points = []
        self.bind(size=self._redraw, pos=self._redraw)

    def set_data(self, latlng_list):
        self._points = latlng_list or []
        self._redraw()

    def _redraw(self, *_):
        self.canvas.clear()
        with self.canvas:
            Color(0.09, 0.09, 0.12, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        if len(self._points) < 2:
            lbl = CoreLabel(text='No GPS data', font_size=dp(12))
            lbl.refresh()
            tx = lbl.texture
            with self.canvas:
                Color(0.35, 0.35, 0.42, 1)
                Rectangle(texture=tx,
                          pos=(self.center_x - tx.width / 2,
                               self.center_y - tx.height / 2),
                          size=tx.size)
            return

        lats = [p[0] for p in self._points]
        lngs = [p[1] for p in self._points]
        min_lat, max_lat = min(lats), max(lats)
        min_lng, max_lng = min(lngs), max(lngs)
        lat_span = max_lat - min_lat or 1e-9
        lng_span = max_lng - min_lng or 1e-9

        pad   = dp(18)
        draw_w = self.width  - 2 * pad
        draw_h = self.height - 2 * pad
        scale  = min(draw_w / lng_span, draw_h / lat_span)
        ox = self.x + pad + (draw_w - lng_span * scale) / 2
        oy = self.y + pad + (draw_h - lat_span * scale) / 2

        pts = []
        for lat, lng in self._points:
            pts.append(ox + (lng - min_lng) * scale)
            pts.append(oy + (lat - min_lat) * scale)

        with self.canvas:
            Color(0.99, 0.38, 0.05, 0.9)
            Line(points=pts, width=dp(2.2), joint='round', cap='round')
            r = dp(5)
            Color(0.30, 0.90, 0.42, 1)
            Ellipse(pos=(pts[0] - r, pts[1] - r), size=(r * 2, r * 2))
            Color(0.95, 0.32, 0.32, 1)
            Ellipse(pos=(pts[-2] - r, pts[-1] - r), size=(r * 2, r * 2))


# ── Pace / Speed graph widget ─────────────────────────────────────────────────

class PaceGraphWidget(Widget):
    """Canvas-drawn pace or speed graph with HR overlay, axis labels, and tracker."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._streams      = None
        self._splits       = []
        self._avg_pace     = 0.0
        self._highlight    = None
        self._mode         = 'pace'   # 'pace' | 'speed'
        self._show_hr      = True
        self._tracker_frac = None
        self.bind(size=self._redraw, pos=self._redraw)

    # ── public API ────────────────────────────────────────────────────────────

    def set_data(self, streams, splits, avg_pace):
        self._streams      = streams
        self._splits       = splits
        self._avg_pace     = avg_pace
        self._highlight    = None
        self._tracker_frac = None
        self._redraw()

    def highlight_split(self, split_num):
        self._highlight = split_num
        self._redraw()

    def set_mode(self, mode):
        self._mode         = mode
        self._tracker_frac = None
        self._redraw()

    def toggle_hr(self):
        self._show_hr = not self._show_hr
        self._redraw()
        return self._show_hr

    # ── touch ────────────────────────────────────────────────────────────────

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._handle_touch(touch.x)
            return True
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        if self.collide_point(*touch.pos):
            self._handle_touch(touch.x)
            return True
        return super().on_touch_move(touch)

    def _handle_touch(self, tx):
        pad_l = dp(44)
        gw    = max(1, self.width - pad_l - dp(8))
        self._tracker_frac = max(0.0, min(1.0, (tx - self.x - pad_l) / gw))
        self._redraw()

    # ── helpers ───────────────────────────────────────────────────────────────

    def _layout(self):
        pad_l, pad_r = dp(44), dp(8)
        pad_t, pad_b = dp(18), dp(22)
        gw = max(1, self.width  - pad_l - pad_r)
        gh = max(1, self.height - pad_t - pad_b)
        return self.x + pad_l, self.y + pad_b, gw, gh

    def _label(self, text, x, y, size=9, color=(0.55, 0.55, 0.60, 1), anchor='left'):
        cl  = CoreLabel(text=str(text), font_size=dp(size))
        cl.refresh()
        tex = cl.texture
        tw, th = tex.size
        if anchor == 'right':  x -= tw
        elif anchor == 'center': x -= tw / 2
        Color(*color)
        Rectangle(texture=tex, pos=(x, y - th / 2), size=(tw, th))

    def _hr_overlay(self, x_vals, x_max, x0, y0, gw, gh):
        if not self._show_hr:
            return
        hr_raw = self._streams.get('heartrate', {}).get('data', [])
        if len(hr_raw) < 2:
            return
        HR_MIN, HR_MAX = 40.0, 200.0
        n    = min(len(x_vals), len(hr_raw))
        step = max(1, n // 300)
        xs   = x_vals[:n:step]
        hrs  = hr_raw[:n:step]
        pts  = []
        for xv, hr in zip(xs, hrs):
            if hr and hr > 0:
                pts.extend([x0 + xv / x_max * gw,
                             y0 + (hr - HR_MIN) / (HR_MAX - HR_MIN) * gh])
        if len(pts) >= 4:
            Color(0.90, 0.35, 0.35, 0.60)
            Line(points=pts, width=dp(1.2))
        # HR y-axis hint
        self._label("HR", x0 + gw + dp(2), y0 + gh * 0.8, size=8,
                    color=(0.70, 0.30, 0.30, 1))

    # ── redraw ────────────────────────────────────────────────────────────────

    def _redraw(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(0.10, 0.10, 0.14, 1)
            Rectangle(pos=self.pos, size=self.size)
        if not self._streams or self.width < 30 or self.height < 30:
            return
        if self._mode == 'pace':
            self._draw_pace()
        else:
            self._draw_speed()

    # ── PACE mode ─────────────────────────────────────────────────────────────

    def _draw_pace(self):
        distances  = self._streams.get('distance',        {}).get('data', [])
        velocities = self._streams.get('velocity_smooth', {}).get('data', [])
        if len(distances) < 2 or not velocities:
            return
        PMIN, PMAX = 180.0, 720.0
        x0, y0, gw, gh = self._layout()
        maxd = distances[-1] if distances[-1] > 0 else 1

        def px(d, p):
            return (x0 + d / maxd * gw,
                    y0 + (1.0 - (p - PMIN) / (PMAX - PMIN)) * gh)

        step  = max(1, len(distances) // 300)
        dists = distances[::step]
        vels  = velocities[::step]
        paces = [max(PMIN, min(PMAX, 1000.0 / v if v and v > 0.3 else PMAX)) for v in vels]
        avg   = self._avg_pace if self._avg_pace > 0 else sum(paces) / max(1, len(paces))

        with self.canvas:
            # Y-axis grid + labels
            Color(0.18, 0.18, 0.24, 1)
            for ps in range(240, int(PMAX) + 1, 60):
                _, gy = px(0, ps)
                Line(points=[x0, gy, x0 + gw, gy], width=dp(0.5))
            for ps in range(240, int(PMAX) + 1, 60):
                _, gy = px(0, ps)
                self._label(f"{ps//60}:{ps%60:02d}", x0 - dp(4), gy, anchor='right')

            # X-axis labels (km markers)
            km_step = max(1, int(maxd / 1000 / 5) + 1)
            km = km_step
            while km * 1000 <= maxd:
                gx, _ = px(km * 1000, PMIN)
                self._label(f"{km}km", gx, y0 - dp(10), anchor='center')
                km += km_step

            # Axis titles
            self._label("PACE /km", x0, self.y + self.height - dp(12),
                        size=8, color=(0.45, 0.45, 0.52, 1))
            self._label("DISTANCE", x0 + gw / 2, y0 - dp(18),
                        size=8, color=(0.45, 0.45, 0.52, 1), anchor='center')

            # Highlighted split band
            if self._highlight is not None:
                for s in self._splits:
                    if s['num'] == self._highlight:
                        hx0, _ = px(s['cumul_m'] - s['dist_m'], PMIN)
                        hx1, _ = px(s['cumul_m'], PMIN)
                        Color(0.99, 0.55, 0.01, 0.28)
                        Rectangle(pos=(hx0, y0), size=(max(1, hx1 - hx0), gh))
                        break

            # Split boundary markers
            Color(0.35, 0.35, 0.45, 0.7)
            for s in self._splits:
                sx, _ = px(s['cumul_m'], PMIN)
                Line(points=[sx, y0, sx, y0 + gh], width=dp(0.5))

            # Pace line
            for i in range(1, len(dists)):
                mid = (paces[i - 1] + paces[i]) / 2
                r, g, b, _ = pace_color(mid, avg)
                Color(r, g, b, 1)
                x1, y1 = px(dists[i - 1], paces[i - 1])
                x2, y2 = px(dists[i],     paces[i])
                Line(points=[x1, y1, x2, y2], width=dp(1.5))

            # HR overlay
            self._hr_overlay(distances, maxd, x0, y0, gw, gh)

            # Tracker
            if self._tracker_frac is not None:
                td  = self._tracker_frac * maxd
                idx = min(range(len(distances)), key=lambda i: abs(distances[i] - td))
                tx, _ = px(td, PMIN)
                Color(0.99, 0.80, 0.01, 0.95)
                Line(points=[tx, y0, tx, y0 + gh], width=dp(1.5))
                v       = velocities[idx] if idx < len(velocities) else 0
                pace_s  = 1000.0 / v if v and v > 0.3 else 0
                hr_raw  = self._streams.get('heartrate', {}).get('data', [])
                hr_str  = f"  HR:{int(hr_raw[idx])}" if idx < len(hr_raw) and hr_raw[idx] else ''
                info    = f"{td/1000:.2f} km  {fmt_pace(pace_s)}/km{hr_str}"
                bx = min(tx + dp(4), x0 + gw - dp(145))
                ty = y0 + gh - dp(1)
                Color(0.13, 0.13, 0.18, 0.92)
                Rectangle(pos=(bx - dp(2), ty - dp(15)), size=(dp(150), dp(17)))
                self._label(info, bx, ty - dp(7), size=9, color=(0.95, 0.90, 0.65, 1))

    # ── SPEED mode ────────────────────────────────────────────────────────────

    def _draw_speed(self):
        times      = self._streams.get('time',            {}).get('data', [])
        velocities = self._streams.get('velocity_smooth', {}).get('data', [])
        if len(times) < 2 or not velocities:
            return
        speeds_all = [v * 3.6 if v else 0.0 for v in velocities]
        SMIN = 0.0
        SMAX = min(40.0, max(20.0, max(speeds_all) * 1.15)) if speeds_all else 20.0
        x0, y0, gw, gh = self._layout()
        maxt = times[-1] if times[-1] > 0 else 1

        def px(t, s):
            return (x0 + t / maxt * gw,
                    y0 + (s - SMIN) / (SMAX - SMIN) * gh)

        step   = max(1, len(times) // 300)
        ts     = times[::step]
        speeds = speeds_all[::step]

        with self.canvas:
            # Y-axis grid + labels
            s_step = 5 if SMAX <= 25 else 10
            Color(0.18, 0.18, 0.24, 1)
            for sv in range(s_step, int(SMAX) + 1, s_step):
                _, gy = px(0, sv)
                Line(points=[x0, gy, x0 + gw, gy], width=dp(0.5))
            for sv in range(s_step, int(SMAX) + 1, s_step):
                _, gy = px(0, sv)
                self._label(f"{sv}", x0 - dp(4), gy, anchor='right')

            # X-axis labels (every 5 min)
            min_step = max(1, int(maxt / 60 / 6))
            t = min_step * 60
            while t <= maxt:
                gx, _ = px(t, SMIN)
                self._label(f"{int(t//60)}m", gx, y0 - dp(10), anchor='center')
                t += min_step * 60

            # Axis titles
            self._label("SPEED km/h", x0, self.y + self.height - dp(12),
                        size=8, color=(0.45, 0.45, 0.52, 1))
            self._label("TIME", x0 + gw / 2, y0 - dp(18),
                        size=8, color=(0.45, 0.45, 0.52, 1), anchor='center')

            # Speed line (solid blue-green)
            pts = []
            for tv, sv in zip(ts, speeds):
                xi, yi = px(tv, sv)
                pts.extend([xi, yi])
            if len(pts) >= 4:
                Color(0.25, 0.75, 0.95, 1)
                Line(points=pts, width=dp(1.5))

            # HR overlay
            self._hr_overlay(times, maxt, x0, y0, gw, gh)

            # Tracker
            if self._tracker_frac is not None:
                tt  = self._tracker_frac * maxt
                idx = min(range(len(times)), key=lambda i: abs(times[i] - tt))
                tx, _ = px(tt, SMIN)
                Color(0.99, 0.80, 0.01, 0.95)
                Line(points=[tx, y0, tx, y0 + gh], width=dp(1.5))
                sv     = velocities[idx] * 3.6 if idx < len(velocities) and velocities[idx] else 0
                hr_raw = self._streams.get('heartrate', {}).get('data', [])
                hr_str = f"  HR:{int(hr_raw[idx])}" if idx < len(hr_raw) and hr_raw[idx] else ''
                info   = f"{int(tt//60)}:{int(tt%60):02d}  {sv:.1f} km/h{hr_str}"
                bx = min(tx + dp(4), x0 + gw - dp(145))
                ty = y0 + gh - dp(1)
                Color(0.13, 0.13, 0.18, 0.92)
                Rectangle(pos=(bx - dp(2), ty - dp(15)), size=(dp(155), dp(17)))
                self._label(info, bx, ty - dp(7), size=9, color=(0.95, 0.90, 0.65, 1))


# ── KV string ────────────────────────────────────────────────────────────────

KV = """
#:import dp kivy.metrics.dp

ScreenManager:
    HomeScreen:
    RunListScreen:
    RunDetailScreen:
    SplitAnalysisScreen:
    IntervalScreen:

# ── Shared canvas colour ──────────────────────────────────────────────────────
<_Dark@Widget>:
    canvas.before:
        Color:
            rgba: 0.07, 0.07, 0.09, 1
        Rectangle:
            pos: self.pos
            size: self.size

# ── Reusable nav back button ──────────────────────────────────────────────────
<NavBackBtn@Button>:
    font_size: dp(13)
    bold: True
    size_hint_x: None
    width: dp(68)
    background_color: 0, 0, 0, 0
    color: 0.99, 0.40, 0.05, 1
    canvas.before:
        Color:
            rgba: 0.25, 0.11, 0.02, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8)]

# ── Reusable interval adjust buttons ─────────────────────────────────────────
<MinusBtn@Button>:
    text: '-'
    font_size: dp(20)
    bold: True
    size_hint_x: 0.16
    background_color: 0, 0, 0, 0
    color: 0.85, 0.50, 0.50, 1
    canvas.before:
        Color:
            rgba: 0.24, 0.13, 0.13, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8)]

<PlusBtn@Button>:
    text: '+'
    font_size: dp(20)
    bold: True
    size_hint_x: 0.16
    background_color: 0, 0, 0, 0
    color: 0.50, 0.85, 0.50, 1
    canvas.before:
        Color:
            rgba: 0.13, 0.24, 0.13, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8)]

# ── Run card ─────────────────────────────────────────────────────────────────
<RunCard>:
    orientation: 'vertical'
    size_hint_y: None
    height: dp(128)
    padding: dp(12), dp(8)
    spacing: dp(4)
    canvas.before:
        Color:
            rgba: 0.13, 0.13, 0.17, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(8)]

    # Row 1: type badge + name + date
    BoxLayout:
        size_hint_y: None
        height: dp(26)
        spacing: dp(6)
        Label:
            text: root.source_badge
            font_size: dp(11)
            bold: True
            color: 0.99, 0.30, 0.01, 1
            size_hint_x: None
            width: dp(52)
            canvas.before:
                Color:
                    rgba: 0.25, 0.10, 0.02, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(4)]
        Label:
            text: root.run_name
            font_size: dp(15)
            bold: True
            color: 0.95, 0.95, 0.95, 1
            text_size: self.size
            halign: 'left'
            valign: 'middle'
            shorten: True
        Label:
            text: root.run_date
            font_size: dp(11)
            color: 0.50, 0.50, 0.55, 1
            size_hint_x: None
            width: dp(100)
            text_size: self.size
            halign: 'right'
            valign: 'middle'

    # Row 2: Distance / Time / Pace
    BoxLayout:
        size_hint_y: None
        height: dp(52)
        spacing: dp(4)
        BoxLayout:
            orientation: 'vertical'
            Label:
                text: root.distance_text
                font_size: dp(21)
                bold: True
                color: 1, 1, 1, 1
            Label:
                text: 'DISTANCE'
                font_size: dp(9)
                color: 0.45, 0.45, 0.50, 1
        BoxLayout:
            orientation: 'vertical'
            Label:
                text: root.time_text
                font_size: dp(21)
                bold: True
                color: 1, 1, 1, 1
            Label:
                text: 'TIME'
                font_size: dp(9)
                color: 0.45, 0.45, 0.50, 1
        BoxLayout:
            orientation: 'vertical'
            Label:
                text: root.pace_text
                font_size: dp(21)
                bold: True
                color: 1, 1, 1, 1
            Label:
                text: 'PACE'
                font_size: dp(9)
                color: 0.45, 0.45, 0.50, 1

    # Row 3: HR + elev
    BoxLayout:
        size_hint_y: None
        height: dp(22)
        Label:
            text: root.hr_text
            font_size: dp(12)
            color: 0.90, 0.35, 0.35, 1
            text_size: self.size
            halign: 'left'
            valign: 'middle'
        Label:
            text: root.elev_text
            font_size: dp(12)
            color: 0.40, 0.80, 0.40, 1
            text_size: self.size
            halign: 'left'
            valign: 'middle'

# ── Home ─────────────────────────────────────────────────────────────────────
<HomeScreen>:
    name: 'home'
    canvas.before:
        Color:
            rgba: 0.06, 0.06, 0.08, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: 'vertical'

        # Orange accent strip
        Widget:
            size_hint_y: None
            height: dp(3)
            canvas.before:
                Color:
                    rgba: 0.99, 0.30, 0.01, 1
                Rectangle:
                    pos: self.pos
                    size: self.size

        # Top flex spacer — pushes content toward visual centre
        Widget:
            size_hint_y: 1

        # Brand block
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: dp(86)
            padding: dp(28), 0
            spacing: dp(6)
            Label:
                text: 'RUNNING'
                font_size: dp(48)
                bold: True
                color: 1, 1, 1, 1
                halign: 'left'
                text_size: self.size
                size_hint_y: None
                height: dp(58)
            Label:
                text: 'Track  ·  Analyse  ·  Improve'
                font_size: dp(13)
                color: 0.40, 0.40, 0.50, 1
                halign: 'left'
                text_size: self.size
                size_hint_y: None
                height: dp(20)

        # Cards
        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: dp(242)
            padding: dp(20), dp(18)
            spacing: dp(14)

            RelativeLayout:
                size_hint_y: None
                height: dp(96)
                canvas.before:
                    Color:
                        rgba: 0.18, 0.08, 0.01, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(14)]
                    Color:
                        rgba: 0.99, 0.30, 0.01, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.width, dp(4)
                        radius: [dp(14), dp(14), 0, 0]
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(18), dp(14)
                    spacing: dp(4)
                    Label:
                        text: 'MY RUNS'
                        font_size: dp(18)
                        bold: True
                        color: 1, 1, 1, 1
                        halign: 'left'
                        text_size: self.size
                        size_hint_y: None
                        height: dp(26)
                    Label:
                        text: 'View, analyse and import activities'
                        font_size: dp(12)
                        color: 0.80, 0.60, 0.45, 1
                        halign: 'left'
                        text_size: self.size
                Button:
                    background_color: 0, 0, 0, 0
                    on_press: app.root.current = 'runlist'

            RelativeLayout:
                size_hint_y: None
                height: dp(96)
                canvas.before:
                    Color:
                        rgba: 0.07, 0.10, 0.22, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(14)]
                    Color:
                        rgba: 0.28, 0.48, 0.92, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.width, dp(4)
                        radius: [dp(14), dp(14), 0, 0]
                BoxLayout:
                    orientation: 'vertical'
                    padding: dp(18), dp(14)
                    spacing: dp(4)
                    Label:
                        text: 'INTERVALS'
                        font_size: dp(18)
                        bold: True
                        color: 1, 1, 1, 1
                        halign: 'left'
                        text_size: self.size
                        size_hint_y: None
                        height: dp(26)
                    Label:
                        text: 'Timer with work / rest phases'
                        font_size: dp(12)
                        color: 0.55, 0.68, 0.92, 1
                        halign: 'left'
                        text_size: self.size
                Button:
                    background_color: 0, 0, 0, 0
                    on_press: app.root.current = 'interval'

        # Bottom flex spacer — slightly larger so content sits just above centre
        Widget:
            size_hint_y: 1.4

        Label:
            text: 'v1.2'
            font_size: dp(11)
            color: 0.20, 0.20, 0.26, 1
            size_hint_y: None
            height: dp(28)

# ── Run list ─────────────────────────────────────────────────────────────────
<RunListScreen>:
    name: 'runlist'
    canvas.before:
        Color:
            rgba: 0.07, 0.07, 0.09, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: 'vertical'
        # Header
        BoxLayout:
            size_hint_y: None
            height: dp(54)
            padding: dp(8), dp(6)
            spacing: dp(6)
            canvas.before:
                Color:
                    rgba: 0.10, 0.10, 0.13, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
                Color:
                    rgba: 0.99, 0.30, 0.01, 1
                Rectangle:
                    pos: self.x, self.y
                    size: self.width, dp(2)
            NavBackBtn:
                text: 'Home'
                on_press: app.root.current = 'home'
            Label:
                text: 'My Runs'
                font_size: dp(18)
                bold: True
                color: 0.95, 0.95, 0.95, 1
            Button:
                id: strava_btn
                text: 'Strava'
                font_size: dp(13)
                size_hint_x: None
                width: dp(72)
                background_color: 0.99, 0.30, 0.01, 1
                on_press: app.run_list.tap_strava()
            Button:
                text: 'CSV'
                font_size: dp(13)
                size_hint_x: None
                width: dp(52)
                background_color: 0.22, 0.22, 0.28, 1
                on_press: app.run_list.tap_csv()
        # Sort / filter bar
        BoxLayout:
            size_hint_y: None
            height: dp(36)
            padding: dp(6), dp(3)
            spacing: dp(4)
            canvas.before:
                Color:
                    rgba: 0.09, 0.09, 0.12, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            Label:
                text: 'Sort:'
                font_size: dp(11)
                color: 0.5, 0.5, 0.55, 1
                size_hint_x: None
                width: dp(32)
            Button:
                id: sort_date_btn
                text: 'Date'
                font_size: dp(11)
                background_color: 0.99, 0.30, 0.01, 1
                on_press: app.run_list.set_sort('date')
            Button:
                id: sort_pace_btn
                text: 'Pace'
                font_size: dp(11)
                background_color: 0.22, 0.22, 0.28, 1
                on_press: app.run_list.set_sort('pace')
            Button:
                id: sort_dist_btn
                text: 'Distance'
                font_size: dp(11)
                background_color: 0.22, 0.22, 0.28, 1
                on_press: app.run_list.set_sort('distance')
            Button:
                id: filter_btn
                text: 'Runs'
                font_size: dp(11)
                background_color: 0.18, 0.28, 0.60, 1
                size_hint_x: None
                width: dp(54)
                on_press: app.run_list.toggle_filter()
        # Status bar
        Label:
            id: status_label
            text: ''
            font_size: dp(12)
            color: 0.50, 0.50, 0.55, 1
            size_hint_y: None
            height: dp(22)
        # Run cards
        ScrollView:
            GridLayout:
                id: runs_grid
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(6)
                padding: dp(8)

# ── Run detail ────────────────────────────────────────────────────────────────
<RunDetailScreen>:
    name: 'rundetail'
    canvas.before:
        Color:
            rgba: 0.07, 0.07, 0.09, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: 'vertical'
        # Header
        BoxLayout:
            size_hint_y: None
            height: dp(54)
            padding: dp(8), dp(6)
            spacing: dp(6)
            canvas.before:
                Color:
                    rgba: 0.10, 0.10, 0.13, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
                Color:
                    rgba: 0.99, 0.30, 0.01, 1
                Rectangle:
                    pos: self.x, self.y
                    size: self.width, dp(2)
            NavBackBtn:
                text: 'Runs'
                on_press: app.root.current = 'runlist'
            Label:
                id: detail_title
                text: ''
                font_size: dp(16)
                bold: True
                color: 0.95, 0.95, 0.95, 1
                shorten: True
                text_size: self.size
                halign: 'left'
                valign: 'middle'
        ScrollView:
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: dp(16)
                spacing: dp(14)
                # Date + source
                Label:
                    id: detail_date
                    text: ''
                    font_size: dp(13)
                    color: 0.50, 0.50, 0.55, 1
                    size_hint_y: None
                    height: dp(22)
                    text_size: self.size
                    halign: 'left'
                # Big stats: distance / time / pace
                GridLayout:
                    cols: 3
                    size_hint_y: None
                    height: dp(80)
                    spacing: dp(4)
                    BoxLayout:
                        orientation: 'vertical'
                        canvas.before:
                            Color:
                                rgba: 0.13, 0.13, 0.17, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [dp(8)]
                        Label:
                            id: stat_dist
                            text: '--'
                            font_size: dp(26)
                            bold: True
                            color: 1, 1, 1, 1
                        Label:
                            text: 'DISTANCE'
                            font_size: dp(9)
                            color: 0.45, 0.45, 0.50, 1
                    BoxLayout:
                        orientation: 'vertical'
                        canvas.before:
                            Color:
                                rgba: 0.13, 0.13, 0.17, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [dp(8)]
                        Label:
                            id: stat_time
                            text: '--'
                            font_size: dp(26)
                            bold: True
                            color: 1, 1, 1, 1
                        Label:
                            text: 'TIME'
                            font_size: dp(9)
                            color: 0.45, 0.45, 0.50, 1
                    BoxLayout:
                        orientation: 'vertical'
                        canvas.before:
                            Color:
                                rgba: 0.13, 0.13, 0.17, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [dp(8)]
                        Label:
                            id: stat_pace
                            text: '--'
                            font_size: dp(26)
                            bold: True
                            color: 1, 1, 1, 1
                        Label:
                            text: 'PACE /km'
                            font_size: dp(9)
                            color: 0.45, 0.45, 0.50, 1
                # Secondary stats: elev / avg HR / max HR
                GridLayout:
                    cols: 3
                    size_hint_y: None
                    height: dp(70)
                    spacing: dp(4)
                    BoxLayout:
                        orientation: 'vertical'
                        canvas.before:
                            Color:
                                rgba: 0.13, 0.13, 0.17, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [dp(8)]
                        Label:
                            id: stat_elev
                            text: '--'
                            font_size: dp(20)
                            bold: True
                            color: 0.40, 0.80, 0.40, 1
                        Label:
                            text: 'ELEV GAIN'
                            font_size: dp(9)
                            color: 0.45, 0.45, 0.50, 1
                    BoxLayout:
                        orientation: 'vertical'
                        canvas.before:
                            Color:
                                rgba: 0.13, 0.13, 0.17, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [dp(8)]
                        Label:
                            id: stat_avg_hr
                            text: '--'
                            font_size: dp(20)
                            bold: True
                            color: 0.90, 0.35, 0.35, 1
                        Label:
                            text: 'AVG HR'
                            font_size: dp(9)
                            color: 0.45, 0.45, 0.50, 1
                    BoxLayout:
                        orientation: 'vertical'
                        canvas.before:
                            Color:
                                rgba: 0.13, 0.13, 0.17, 1
                            RoundedRectangle:
                                pos: self.pos
                                size: self.size
                                radius: [dp(8)]
                        Label:
                            id: stat_max_hr
                            text: '--'
                            font_size: dp(20)
                            bold: True
                            color: 0.90, 0.35, 0.35, 1
                        Label:
                            text: 'MAX HR'
                            font_size: dp(9)
                            color: 0.45, 0.45, 0.50, 1
                # Route map
                RouteMapWidget:
                    id: route_map
                    size_hint_y: None
                    height: dp(200)
                # Splits button
                Button:
                    id: splits_btn
                    text: 'View Splits'
                    font_size: dp(16)
                    bold: True
                    size_hint_y: None
                    height: dp(52)
                    background_color: 0.99, 0.30, 0.01, 1
                    on_press: app.run_detail.tap_splits()
                Label:
                    id: splits_hint
                    text: ''
                    font_size: dp(12)
                    color: 0.45, 0.45, 0.50, 1
                    size_hint_y: None
                    height: dp(20)
                    text_size: self.size
                    halign: 'center'

# ── Route map ─────────────────────────────────────────────────────────────────
<RouteMapWidget>:
    canvas.before:
        Color:
            rgba: 0.09, 0.09, 0.12, 1
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [dp(10)]

# ── Split analysis ─────────────────────────────────────────────────────────
<PaceGraphWidget>:
    canvas.before:
        Color:
            rgba: 0.10, 0.10, 0.14, 1
        Rectangle:
            pos: self.pos
            size: self.size

<SplitAnalysisScreen>:
    name: 'splits'
    canvas.before:
        Color:
            rgba: 0.07, 0.07, 0.09, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: 'vertical'
        # Header
        BoxLayout:
            size_hint_y: None
            height: dp(54)
            padding: dp(8), dp(6)
            spacing: dp(6)
            canvas.before:
                Color:
                    rgba: 0.10, 0.10, 0.13, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
                Color:
                    rgba: 0.99, 0.30, 0.01, 1
                Rectangle:
                    pos: self.x, self.y
                    size: self.width, dp(2)
            NavBackBtn:
                text: 'Detail'
                on_press: app.root.current = 'rundetail'
            Label:
                text: 'Split Analysis'
                font_size: dp(17)
                bold: True
                color: 0.95, 0.95, 0.95, 1
        # Graph mode / HR toggle row
        BoxLayout:
            size_hint_y: None
            height: dp(34)
            padding: dp(6), dp(3)
            spacing: dp(4)
            canvas.before:
                Color:
                    rgba: 0.09, 0.09, 0.12, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            Button:
                id: graph_pace_btn
                text: 'Pace'
                font_size: dp(11)
                background_color: 0.99, 0.30, 0.01, 1
                on_press: app.split_analysis.set_graph_mode('pace')
            Button:
                id: graph_speed_btn
                text: 'Speed'
                font_size: dp(11)
                background_color: 0.22, 0.22, 0.28, 1
                on_press: app.split_analysis.set_graph_mode('speed')
            Button:
                id: hr_toggle_btn
                text: 'HR On'
                font_size: dp(11)
                size_hint_x: None
                width: dp(62)
                background_color: 0.55, 0.18, 0.18, 1
                on_press: app.split_analysis.toggle_hr()
        # Pace graph
        PaceGraphWidget:
            id: pace_graph
            size_hint_y: None
            height: dp(185)
        # Interval selector
        ScrollView:
            size_hint_y: None
            height: dp(44)
            do_scroll_y: False
            BoxLayout:
                id: interval_btns
                orientation: 'horizontal'
                size_hint_x: None
                width: self.minimum_width
                spacing: dp(6)
                padding: dp(8), dp(4)
        # Table header
        GridLayout:
            id: table_header
            cols: 5
            size_hint_y: None
            height: dp(28)
            padding: dp(8), 0
            spacing: dp(2)
        Label:
            id: splits_status
            text: ''
            font_size: dp(12)
            color: 0.50, 0.50, 0.55, 1
            size_hint_y: None
            height: dp(22)
        # Split rows + interval summary (shared scroll)
        ScrollView:
            BoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                GridLayout:
                    id: splits_table
                    cols: 5
                    size_hint_y: None
                    height: self.minimum_height
                    padding: dp(8), 0
                    spacing: dp(2), dp(3)
                BoxLayout:
                    id: interval_summary
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    padding: dp(10), dp(6)
                    spacing: dp(5)

# ── Interval training ─────────────────────────────────────────────────────────
<IntervalScreen>:
    name: 'interval'
    canvas.before:
        Color:
            rgba: 0.08, 0.08, 0.12, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: 'vertical'
        padding: dp(12)
        spacing: dp(8)

        BoxLayout:
            size_hint_y: None
            height: dp(54)
            padding: dp(8), dp(6)
            spacing: dp(6)
            canvas.before:
                Color:
                    rgba: 0.10, 0.10, 0.13, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
                Color:
                    rgba: 0.99, 0.30, 0.01, 1
                Rectangle:
                    pos: self.x, self.y
                    size: self.width, dp(2)
            NavBackBtn:
                text: 'Home'
                on_press: app.go_home()
            Label:
                text: 'INTERVALS'
                font_size: dp(18)
                bold: True
                color: 0.95, 0.95, 0.95, 1
            Widget:
                size_hint_x: None
                width: dp(68)

        Label:
            id: phase_label
            text: 'READY'
            font_size: dp(32)
            bold: True
            color: 0.3, 0.8, 0.4, 1
            size_hint_y: None
            height: dp(50)

        Label:
            id: interval_timer_label
            text: '00:00'
            font_size: dp(68)
            bold: True
            color: 0.95, 0.95, 0.95, 1
            size_hint_y: None
            height: dp(100)

        BoxLayout:
            size_hint_y: None
            height: dp(30)
            Label:
                id: rep_label
                text: ''
                font_size: dp(16)
                color: 0.7, 0.7, 0.7, 1
            Label:
                id: next_label
                text: ''
                font_size: dp(14)
                color: 0.4, 0.7, 1, 1

        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: dp(308)
            spacing: dp(6)
            padding: dp(12), dp(8)
            canvas.before:
                Color:
                    rgba: 0.11, 0.11, 0.15, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(14)]

            Label:
                text: 'CONFIGURE'
                font_size: dp(11)
                color: 0.38, 0.38, 0.45, 1
                size_hint_y: None
                height: dp(20)

            BoxLayout:
                size_hint_y: None
                height: dp(42)
                Label:
                    text: 'WARMUP'
                    font_size: dp(12)
                    color: 0.80, 0.62, 0.18, 1
                    size_hint_x: 0.28
                MinusBtn:
                    on_press: app.interval_screen.adjust_warmup(-60)
                Label:
                    id: warmup_time_label
                    text: '5:00'
                    font_size: dp(19)
                    bold: True
                    color: 0.9, 0.9, 0.9, 1
                PlusBtn:
                    on_press: app.interval_screen.adjust_warmup(60)

            BoxLayout:
                size_hint_y: None
                height: dp(42)
                Label:
                    text: 'WORK'
                    font_size: dp(12)
                    color: 0.28, 0.72, 0.36, 1
                    size_hint_x: 0.28
                MinusBtn:
                    on_press: app.interval_screen.adjust_work(-30)
                Label:
                    id: work_time_label
                    text: '3:00'
                    font_size: dp(19)
                    bold: True
                    color: 0.9, 0.9, 0.9, 1
                PlusBtn:
                    on_press: app.interval_screen.adjust_work(30)

            BoxLayout:
                size_hint_y: None
                height: dp(42)
                Label:
                    text: 'REST'
                    font_size: dp(12)
                    color: 0.75, 0.28, 0.28, 1
                    size_hint_x: 0.28
                MinusBtn:
                    on_press: app.interval_screen.adjust_rest(-30)
                Label:
                    id: rest_time_label
                    text: '1:00'
                    font_size: dp(19)
                    bold: True
                    color: 0.9, 0.9, 0.9, 1
                PlusBtn:
                    on_press: app.interval_screen.adjust_rest(30)

            BoxLayout:
                size_hint_y: None
                height: dp(42)
                Label:
                    text: 'COOLDOWN'
                    font_size: dp(12)
                    color: 0.38, 0.62, 0.92, 1
                    size_hint_x: 0.28
                MinusBtn:
                    on_press: app.interval_screen.adjust_cooldown(-60)
                Label:
                    id: cooldown_time_label
                    text: '5:00'
                    font_size: dp(19)
                    bold: True
                    color: 0.9, 0.9, 0.9, 1
                PlusBtn:
                    on_press: app.interval_screen.adjust_cooldown(60)

            BoxLayout:
                size_hint_y: None
                height: dp(42)
                Label:
                    text: 'REPS'
                    font_size: dp(12)
                    color: 0.62, 0.45, 0.82, 1
                    size_hint_x: 0.28
                MinusBtn:
                    on_press: app.interval_screen.adjust_reps(-1)
                Label:
                    id: reps_label
                    text: '6'
                    font_size: dp(19)
                    bold: True
                    color: 0.9, 0.9, 0.9, 1
                PlusBtn:
                    on_press: app.interval_screen.adjust_reps(1)

        ScrollView:
            size_hint_y: 1
            GridLayout:
                id: interval_log_grid
                cols: 1
                size_hint_y: None
                height: self.minimum_height

        BoxLayout:
            size_hint_y: None
            height: dp(66)
            spacing: dp(10)
            Button:
                id: interval_start_btn
                text: 'START'
                font_size: dp(22)
                bold: True
                background_color: 0, 0, 0, 0
                color: 1, 1, 1, 1
                canvas.before:
                    Color:
                        rgba: 0.16, 0.36, 0.70, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(14)]
                on_press: app.interval_screen.toggle_interval()
            Button:
                text: 'RESET'
                font_size: dp(18)
                background_color: 0, 0, 0, 0
                color: 1, 1, 1, 1
                size_hint_x: 0.38
                canvas.before:
                    Color:
                        rgba: 0.50, 0.16, 0.16, 1
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(14)]
                on_press: app.interval_screen.reset_interval()
"""


# ── Run list logic ────────────────────────────────────────────────────────────

def _make_card(run, on_tap):
    pace = run.avg_pace_s_per_km
    card = RunCard(
        run_name      = run.name,
        run_date      = fmt_date(run.date),
        distance_text = fmt_dist(run.distance_m),
        time_text     = fmt_time(run.moving_time_s or run.elapsed_time_s),
        pace_text     = fmt_pace(pace) + ' /km',
        hr_text       = f'HR {int(run.avg_hr)} bpm' if run.avg_hr else '',
        elev_text     = f'+{int(run.elevation_gain_m)} m' if run.elevation_gain_m else '',
        source_badge  = run.source.upper()[:7],
    )
    card.bind(on_press=on_tap)
    card._run = run
    return card


_RUN_TYPES = {'Run', 'TrailRun', 'VirtualRun'}

class RunListLogic:
    def __init__(self, screen, store, strava):
        self.screen     = screen
        self.store      = store
        self.strava     = strava
        self._sort      = 'date'   # 'date' | 'pace' | 'distance'
        self._runs_only = True
        try:
            self._refresh()
        except Exception:
            pass

    def _sorted_runs(self):
        runs = self.store.runs
        if self._runs_only:
            runs = [r for r in runs if r.activity_type in _RUN_TYPES]
        if self._sort == 'pace':
            return sorted(runs, key=lambda r: r.avg_pace_s_per_km if r.avg_pace_s_per_km > 0 else 9999)
        if self._sort == 'distance':
            return sorted(runs, key=lambda r: r.distance_m, reverse=True)
        return runs  # store maintains date order

    def set_sort(self, key):
        self._sort = key
        self._update_sort_buttons()
        self._refresh()

    def toggle_filter(self):
        self._runs_only = not self._runs_only
        self._update_filter_button()
        self._refresh()

    def _update_sort_buttons(self):
        on  = (0.99, 0.30, 0.01, 1)
        off = (0.22, 0.22, 0.28, 1)
        ids = self.screen.ids
        ids.sort_date_btn.background_color = on  if self._sort == 'date'     else off
        ids.sort_pace_btn.background_color = on  if self._sort == 'pace'     else off
        ids.sort_dist_btn.background_color = on  if self._sort == 'distance' else off

    def _update_filter_button(self):
        btn = self.screen.ids.filter_btn
        if self._runs_only:
            btn.text = 'Runs';  btn.background_color = (0.18, 0.28, 0.60, 1)
        else:
            btn.text = 'All';   btn.background_color = (0.40, 0.20, 0.55, 1)

    def _refresh(self):
        grid = self.screen.ids.runs_grid
        grid.clear_widgets()
        runs = self._sorted_runs()
        if not runs:
            lbl = Label(
                text='No runs yet.\nTap Strava to connect or CSV to import.',
                font_size=dp(14), color=(0.5, 0.5, 0.55, 1),
                size_hint_y=None, height=dp(80), halign='center',
                text_size=(dp(300), None),
            )
            grid.add_widget(lbl)
            return
        for run in runs:
            card = _make_card(run, self._on_tap)
            grid.add_widget(card)

    def _on_tap(self, card):
        App.get_running_app().open_run_detail(card._run)

    def _status(self, msg):
        self.screen.ids.status_label.text = msg

    # ── Strava flow ──────────────────────────────────────────────────────

    def tap_strava(self):
        if self.strava.authenticated:
            self._sync_strava()
        else:
            self._show_strava_credentials_popup()

    def _show_strava_credentials_popup(self):
        content = BoxLayout(orientation='vertical', spacing=dp(8), padding=dp(12))

        content.add_widget(Label(
            text='strava.com/settings/api',
            font_size=dp(12), color=(0.5, 0.5, 0.55, 1),
            size_hint_y=None, height=dp(20), halign='center',
            text_size=(dp(280), None),
        ))

        cid  = TextInput(hint_text='Client ID',     multiline=False,
                         size_hint_y=None, height=dp(38), text=self.strava.client_id)
        csec = TextInput(hint_text='Client Secret', multiline=False, password=True,
                         size_hint_y=None, height=dp(38), text=self.strava.client_secret)
        content.add_widget(cid)
        content.add_widget(csec)

        # Divider
        content.add_widget(Label(
            text='── or paste tokens directly (personal use) ──',
            font_size=dp(11), color=(0.45, 0.45, 0.50, 1),
            size_hint_y=None, height=dp(20), halign='center',
            text_size=(dp(280), None),
        ))

        atk  = TextInput(hint_text='Access Token (from API page)',  multiline=False,
                         size_hint_y=None, height=dp(38),
                         text=self.strava.access_token or '')
        rtk  = TextInput(hint_text='Refresh Token (from API page)', multiline=False,
                         size_hint_y=None, height=dp(38),
                         text=self.strava.refresh_token or '')
        content.add_widget(atk)
        content.add_widget(rtk)

        popup = Popup(title='Connect Strava', content=content,
                      size_hint=(0.93, None), height=dp(380))

        btns = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))

        def save_tokens(_):
            """Save manually-pasted tokens — no OAuth dance needed."""
            self.strava.client_id     = cid.text.strip()
            self.strava.client_secret = csec.text.strip()
            self.strava.access_token  = atk.text.strip() or None
            self.strava.refresh_token = rtk.text.strip() or None
            App.get_running_app().save_strava_creds()
            popup.dismiss()
            if self.strava.authenticated:
                self.screen.ids.strava_btn.text = 'Sync'
                self._status('Tokens saved. Fetching runs…')
                self._sync_strava()
            else:
                self._status('Tokens saved (no access token yet)')

        def connect_browser(_):
            self.strava.client_id     = cid.text.strip()
            self.strava.client_secret = csec.text.strip()
            App.get_running_app().save_strava_creds()
            popup.dismiss()
            self._do_strava_auth()

        btn_tokens  = Button(text='Save Tokens',   background_color=(0.20, 0.50, 0.20, 1))
        btn_browser = Button(text='Browser OAuth', background_color=(0.99, 0.30, 0.01, 1))
        btn_cancel  = Button(text='Cancel',        background_color=(0.30, 0.30, 0.30, 1),
                             size_hint_x=0.4)
        btn_tokens.bind(on_press=save_tokens)
        btn_browser.bind(on_press=connect_browser)
        btn_cancel.bind(on_press=lambda _: popup.dismiss())
        btns.add_widget(btn_tokens)
        btns.add_widget(btn_browser)
        btns.add_widget(btn_cancel)
        content.add_widget(btns)
        popup.open()

    def _do_strava_auth(self):
        self._status('Opening browser — authorize then return here')
        self.screen.ids.strava_btn.text = 'Waiting…'
        # Store callbacks so RunningApp._on_new_intent can fire them
        app = App.get_running_app()
        app._auth_on_success = self._on_auth_success
        app._auth_on_error   = self._on_auth_error
        self.strava.open_browser_for_auth()
        self._status('Completed authorization')
        self.screen.ids.strava_btn.text = 'Ready to pull'

    def _on_auth_success(self):
        App.get_running_app().save_strava_creds()
        self.screen.ids.strava_btn.text = 'Sync'
        self._status('Connected! Fetching runs…')
        self._sync_strava()

    def _on_auth_error(self, msg):
        self._status(f'Auth failed: {msg}')
        self.screen.ids.strava_btn.text = 'Strava'

    def _sync_strava(self):
        self._status('Fetching activities from Strava…')

        def fetch():
            try:
                runs = self.strava.fetch_activities()
                added = self.store.add_runs(runs)
                Clock.schedule_once(lambda dt: self._on_strava_synced(added))
            except Exception as e:
                msg = f'Sync error: {e}'
                print(traceback.format_exc())
                Clock.schedule_once(lambda dt: self._status(msg))

        threading.Thread(target=fetch, daemon=True).start()

    def _on_strava_synced(self, added):
        self._status(f'Synced — {added} new run(s) added')
        try:
            self._refresh()
        except Exception as e:
            self._status(f'Display error: {e}')

    # ── CSV import ───────────────────────────────────────────────────────

    def tap_csv(self):
        content = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(12))
        content.add_widget(Label(
            text='Paste the full path to your CSV file\n(Strava, Samsung Health, Fitbit, or generic)',
            font_size=dp(13), color=(0.8, 0.8, 0.8, 1),
            size_hint_y=None, height=dp(50), halign='center',
            text_size=(dp(280), None),
        ))
        path_input = TextInput(
            hint_text='/storage/emulated/0/Download/activities.csv',
            multiline=False, size_hint_y=None, height=dp(44),
        )
        content.add_widget(path_input)
        status_lbl = Label(text='', font_size=dp(12), color=(0.7, 0.7, 0.7, 1),
                           size_hint_y=None, height=dp(24))
        content.add_widget(status_lbl)
        btns = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        popup = Popup(title='Import CSV', content=content,
                      size_hint=(0.92, None), height=dp(240))

        def load(_):
            path = path_input.text.strip()
            if not os.path.exists(path):
                status_lbl.text = 'File not found'
                return
            runs = CSVImporter.parse(path)
            if not runs:
                status_lbl.text = 'No valid runs found in file'
                return
            added = self.store.add_runs(runs)
            popup.dismiss()
            self._status(f'Imported {added} run(s) from CSV')
            self._refresh()

        ok = Button(text='Load', background_color=(0.99, 0.30, 0.01, 1))
        ok.bind(on_press=load)
        cancel = Button(text='Cancel', background_color=(0.3, 0.3, 0.3, 1))
        cancel.bind(on_press=lambda _: popup.dismiss())
        btns.add_widget(ok); btns.add_widget(cancel)
        content.add_widget(btns)
        popup.open()


# ── Run detail logic ──────────────────────────────────────────────────────────

class RunDetailLogic:
    def __init__(self, screen, store, strava):
        self.screen = screen
        self.store  = store
        self.strava = strava
        self.run    = None

    def load(self, run):
        self.run = run
        ids = self.screen.ids
        ids.detail_title.text = run.name
        ids.detail_date.text  = (fmt_date(run.date) if run.date else '') + f'  [{run.source}]'
        ids.stat_dist.text    = fmt_dist(run.distance_m)
        ids.stat_time.text    = fmt_time(run.moving_time_s or run.elapsed_time_s)
        ids.stat_pace.text    = fmt_pace(run.avg_pace_s_per_km)
        ids.stat_elev.text    = f'{int(run.elevation_gain_m)} m' if run.elevation_gain_m else '--'
        ids.stat_avg_hr.text  = f'{int(run.avg_hr)} bpm' if run.avg_hr else '--'
        ids.stat_max_hr.text  = f'{int(run.max_hr)} bpm' if run.max_hr else '--'

        latlng = run.streams.get('latlng', {}).get('data', []) if run.streams else []
        ids.route_map.set_data(latlng)

        if run.streams:
            ids.splits_btn.text        = 'View Splits'
            ids.splits_btn.disabled    = False
            ids.splits_hint.text       = 'Detailed stream data available'
        elif run.strava_id and self.strava.authenticated:
            ids.splits_btn.text        = 'Load Splits from Strava'
            ids.splits_btn.disabled    = False
            ids.splits_hint.text       = 'Will fetch per-second GPS data'
        else:
            ids.splits_btn.text        = 'Splits unavailable'
            ids.splits_btn.disabled    = True
            ids.splits_hint.text       = 'Connect Strava to enable detailed splits'

    def tap_splits(self):
        if self.run is None:
            return
        if self.run.streams:
            App.get_running_app().open_split_analysis(self.run)
        elif self.run.strava_id and self.strava.authenticated:
            self.screen.ids.splits_btn.text     = 'Loading…'
            self.screen.ids.splits_btn.disabled = True

            def fetch():
                try:
                    streams = self.strava.fetch_streams(self.run.strava_id)
                    self.store.update_streams(self.run.id, streams)
                    self.run.streams = streams
                    latlng = streams.get('latlng', {}).get('data', [])
                    Clock.schedule_once(lambda dt, ll=latlng: self.screen.ids.route_map.set_data(ll))
                    Clock.schedule_once(lambda dt: App.get_running_app().open_split_analysis(self.run))
                except Exception as e:
                    msg = str(e)
                    Clock.schedule_once(lambda dt: self._on_fetch_error(msg))

            threading.Thread(target=fetch, daemon=True).start()

    def _on_fetch_error(self, msg):
        self.screen.ids.splits_btn.text     = 'Load Splits from Strava'
        self.screen.ids.splits_btn.disabled = False
        self.screen.ids.splits_hint.text    = f'Error: {msg}'


# ── Split analysis logic ──────────────────────────────────────────────────────

class SplitAnalysisLogic:
    def __init__(self, screen):
        self.screen       = screen
        self.run          = None
        self.active_interval_m = 1000.0
        self._build_interval_buttons()
        self._build_table_header()

    def _build_interval_buttons(self):
        btn_row = self.screen.ids.interval_btns
        btn_row.clear_widgets()
        for label, dist_m in INTERVALS:
            btn = Button(
                text=label, font_size=dp(13),
                size_hint=(None, None), width=dp(70), height=dp(34),
                background_color=(0.22, 0.22, 0.28, 1),
            )
            btn._dist = dist_m
            btn.bind(on_press=self._select_interval)
            btn_row.add_widget(btn)
        self._highlight_btn(1000.0)

    def _select_interval(self, btn):
        self.active_interval_m = btn._dist
        self._highlight_btn(btn._dist)
        self._render_splits()

    def _highlight_btn(self, dist_m):
        for btn in self.screen.ids.interval_btns.children:
            btn.background_color = (
                (0.99, 0.30, 0.01, 1) if btn._dist == dist_m
                else (0.22, 0.22, 0.28, 1)
            )

    def _build_table_header(self):
        hdr = self.screen.ids.table_header
        hdr.clear_widgets()
        for col, w in [('#', 0.08), ('DIST', 0.18), ('TIME', 0.18), ('PACE /km', 0.30), ('HR', 0.20)]:
            lbl = Label(text=col, font_size=dp(11), color=(0.50, 0.50, 0.55, 1),
                        size_hint_x=w)
            hdr.add_widget(lbl)

    def load(self, run):
        self.run = run
        self._render_splits()

    def set_graph_mode(self, mode):
        self.screen.ids.pace_graph.set_mode(mode)
        on, off = (0.99, 0.30, 0.01, 1), (0.22, 0.22, 0.28, 1)
        self.screen.ids.graph_pace_btn.background_color  = on  if mode == 'pace'  else off
        self.screen.ids.graph_speed_btn.background_color = on  if mode == 'speed' else off

    def toggle_hr(self):
        showing = self.screen.ids.pace_graph.toggle_hr()
        btn = self.screen.ids.hr_toggle_btn
        btn.text             = 'HR On'  if showing else 'HR Off'
        btn.background_color = (0.55, 0.18, 0.18, 1) if showing else (0.22, 0.22, 0.28, 1)

    def _select_split(self, split_num):
        self.screen.ids.pace_graph.highlight_split(split_num)

    def _render_splits(self):
        table   = self.screen.ids.splits_table
        status  = self.screen.ids.splits_status
        graph   = self.screen.ids.pace_graph
        summary = self.screen.ids.interval_summary
        table.clear_widgets()
        summary.clear_widgets()

        if self.run is None or not self.run.streams:
            status.text = 'No stream data available'
            graph.set_data(None, [], 0)
            return

        splits = compute_splits(self.run.streams, self.active_interval_m)
        if not splits:
            status.text = 'Not enough data for this interval size'
            graph.set_data(self.run.streams, [], self.run.avg_pace_s_per_km)
            return

        status.text  = f'{len(splits)} splits  ·  tap # to highlight on graph'
        avg_pace     = self.run.avg_pace_s_per_km
        graph.set_data(self.run.streams, splits, avg_pace)

        for s in splits:
            color      = pace_color(s['pace'], avg_pace)
            dist_label = (f"{s['dist_m']/1000:.2f} km"
                          if s['dist_m'] < self.active_interval_m * 0.99
                          else f"{self.active_interval_m/1000:.2f} km")

            num = s['num']
            num_btn = Button(
                text=str(num), font_size=dp(12),
                size_hint_x=0.08, size_hint_y=None, height=dp(32),
                background_color=(0.18, 0.18, 0.22, 1), color=(0.7, 0.7, 0.8, 1),
            )
            num_btn.bind(on_press=lambda _, n=num: self._select_split(n))
            table.add_widget(num_btn)

            row_data = [
                (dist_label,                   0.18, (0.85, 0.85, 0.85, 1)),
                (fmt_time(s['time_s']),        0.18, (0.95, 0.95, 0.95, 1)),
                (fmt_pace(s['pace']),          0.30, color),
                (f"{int(s['avg_hr'])}" if s['avg_hr'] else '--', 0.26, (0.90, 0.35, 0.35, 1)),
            ]
            for text, w, c in row_data:
                lbl = Label(text=text, font_size=dp(13), color=c,
                            size_hint_x=w, size_hint_y=None, height=dp(32))
                table.add_widget(lbl)

        self._render_interval_summary(summary)

    def _render_interval_summary(self, box):
        """Detect on/off intervals and render a summary card below the splits table."""
        if self.run is None or not self.run.streams:
            return

        result = detect_intervals(self.run.streams)

        def _sep():
            sep = BoxLayout(size_hint_y=None, height=dp(1))
            with sep.canvas.before:
                Color(0.22, 0.22, 0.28, 1)
                Rectangle(pos=sep.pos, size=sep.size)
            sep.bind(pos=lambda w, _: w.canvas.before.clear() or
                     w.canvas.before.add(Color(0.22, 0.22, 0.28, 1)) or
                     w.canvas.before.add(Rectangle(pos=w.pos, size=w.size)))
            return sep

        def _heading(text):
            return Label(text=text, font_size=dp(11), bold=True,
                         color=(0.55, 0.55, 0.62, 1),
                         size_hint_y=None, height=dp(22),
                         halign='left', text_size=(dp(320), None))

        def _row(text, value_text, val_color=(0.95, 0.95, 0.95, 1)):
            row = BoxLayout(size_hint_y=None, height=dp(26))
            row.add_widget(Label(text=text, font_size=dp(12),
                                 color=(0.65, 0.65, 0.70, 1),
                                 halign='left', text_size=(dp(180), None)))
            row.add_widget(Label(text=value_text, font_size=dp(13), bold=True,
                                 color=val_color,
                                 halign='right', text_size=(dp(130), None)))
            return row

        # Section header
        box.add_widget(Widget(size_hint_y=None, height=dp(6)))
        box.add_widget(_sep())
        box.add_widget(_heading('DETECTED INTERVALS'))

        if result is None or (not result['on_splits'] and not result['off_splits']):
            box.add_widget(Label(text='Not enough data for interval detection.',
                                 font_size=dp(12), color=(0.50, 0.50, 0.55, 1),
                                 size_hint_y=None, height=dp(30),
                                 halign='left', text_size=(dp(300), None)))
            return

        on_s   = result['on_splits']
        off_s  = result['off_splits']
        cv     = result['cv']
        all_s  = on_s + off_s

        if cv < 0.06:
            box.add_widget(Label(
                text='Steady-state run — no clear on/off intervals detected.',
                font_size=dp(12), color=(0.55, 0.55, 0.60, 1),
                size_hint_y=None, height=dp(30),
                halign='left', text_size=(dp(300), None)))

        def _avg_pace(splits):
            if not splits: return 0
            t = sum(s['time_s'] for s in splits)
            d = sum(s['dist_m'] for s in splits)
            return t / (d / 1000.0) if d > 0 else 0

        def _fastest(splits):
            if not splits: return 0
            return min(s['avg_pace'] for s in splits)

        def _avg_time(splits):
            if not splits: return 0
            return sum(s['time_s'] for s in splits) / len(splits)

        # ON (work) section
        if on_s:
            box.add_widget(_heading(f'ON / WORK  ({len(on_s)} reps)'))
            box.add_widget(_row('Avg duration', fmt_time(_avg_time(on_s))))
            box.add_widget(_row('Avg distance', fmt_dist(sum(s['dist_m'] for s in on_s) / len(on_s))))
            box.add_widget(_row('Avg pace', fmt_pace(_avg_pace(on_s)) + ' /km',
                                val_color=(0.30, 0.85, 0.45, 1)))
            box.add_widget(_row('Fastest pace', fmt_pace(_fastest(on_s)) + ' /km',
                                val_color=(0.30, 0.95, 0.50, 1)))

        # OFF (rest) section
        if off_s:
            box.add_widget(_heading(f'OFF / REST  ({len(off_s)} reps)'))
            box.add_widget(_row('Avg duration', fmt_time(_avg_time(off_s))))
            box.add_widget(_row('Avg distance', fmt_dist(sum(s['dist_m'] for s in off_s) / len(off_s))))
            box.add_widget(_row('Avg pace', fmt_pace(_avg_pace(off_s)) + ' /km',
                                val_color=(0.90, 0.55, 0.30, 1)))
            box.add_widget(_row('Fastest pace', fmt_pace(_fastest(off_s)) + ' /km',
                                val_color=(0.95, 0.65, 0.30, 1)))

        # Overall fastest
        if all_s:
            fastest = min(all_s, key=lambda s: s['avg_pace'])
            box.add_widget(_sep())
            box.add_widget(_row('Fastest split overall',
                                fmt_pace(fastest['avg_pace']) + ' /km  ' + fmt_time(fastest['time_s']),
                                val_color=(0.99, 0.80, 0.20, 1)))


# ── Interval training logic (unchanged) ──────────────────────────────────────

def fmt_cfg(secs):
    return f"{secs // 60}:{secs % 60:02d}"


class IntervalScreenLogic:
    PHASE_STYLE = {
        'warmup':   ('WARMUP',   (0.9, 0.7, 0.2, 1)),
        'work':     ('WORK',     (0.2, 0.9, 0.4, 1)),
        'rest':     ('REST',     (0.9, 0.3, 0.3, 1)),
        'cooldown': ('COOLDOWN', (0.4, 0.7, 1.0, 1)),
        'idle':     ('READY',    (0.3, 0.8, 0.4, 1)),
        'paused':   ('PAUSED',   (0.8, 0.8, 0.2, 1)),
        'done':     ('DONE!',    (0.9, 0.8, 0.2, 1)),
    }

    def __init__(self, screen):
        self.screen = screen
        self.warmup_secs = 300; self.work_secs = 180
        self.rest_secs = 60;    self.cooldown_secs = 300
        self.total_reps = 6
        self.running = False; self.current_rep = 0
        self.phase = 'idle'; self.phase_remaining = 0.0
        self.phase_start = 0.0; self._clock_event = None
        self._update_config()

    def _update_config(self):
        ids = self.screen.ids
        ids.warmup_time_label.text   = fmt_cfg(self.warmup_secs)
        ids.work_time_label.text     = fmt_cfg(self.work_secs)
        ids.rest_time_label.text     = fmt_cfg(self.rest_secs)
        ids.cooldown_time_label.text = fmt_cfg(self.cooldown_secs)
        ids.reps_label.text          = str(self.total_reps)

    def adjust_warmup(self, d):
        if not self.running: self.warmup_secs = max(0, self.warmup_secs+d); self._update_config()
    def adjust_work(self, d):
        if not self.running: self.work_secs = max(30, self.work_secs+d); self._update_config()
    def adjust_rest(self, d):
        if not self.running: self.rest_secs = max(0, self.rest_secs+d); self._update_config()
    def adjust_cooldown(self, d):
        if not self.running: self.cooldown_secs = max(0, self.cooldown_secs+d); self._update_config()
    def adjust_reps(self, d):
        if not self.running: self.total_reps = max(1, self.total_reps+d); self._update_config()

    def toggle_interval(self):
        if self.running:           self._pause()
        elif self.phase == 'idle': self._begin()
        else:                      self._resume()

    def _begin(self):
        self.current_rep = 0
        self.screen.ids.interval_log_grid.clear_widgets()
        if self.warmup_secs > 0: self._start_phase('warmup', self.warmup_secs)
        else: self._next_work()

    def _next_work(self):
        self.current_rep += 1
        if self.current_rep > self.total_reps:
            if self.cooldown_secs > 0: self._start_phase('cooldown', self.cooldown_secs)
            else: self._finish()
        else:
            self._start_phase('work', self.work_secs)

    def _start_phase(self, phase, dur):
        self.phase = phase; self.phase_remaining = dur
        self.phase_start = time.monotonic(); self.running = True
        label, color = self.PHASE_STYLE[phase]
        ids = self.screen.ids
        ids.phase_label.text  = f'{label}  #{self.current_rep}' if phase == 'work' else label
        ids.phase_label.color = color
        if phase == 'work':   ids.rep_label.text = f'Rep {self.current_rep} / {self.total_reps}'
        elif phase == 'warmup': ids.rep_label.text = f'0 / {self.total_reps} reps'
        elif phase == 'cooldown': ids.rep_label.text = f'{self.total_reps} / {self.total_reps} reps'
        ids.interval_start_btn.text = 'PAUSE'
        ids.interval_start_btn.background_color = (0.7, 0.4, 0.1, 1)
        ids.next_label.text = self._next_up()
        if self._clock_event: self._clock_event.cancel()
        self._clock_event = Clock.schedule_interval(self._tick, 0.1)

    def _next_up(self):
        if self.phase == 'warmup':   return f'Next: WORK #1'
        if self.phase == 'work':
            if self.rest_secs > 0:   return 'Next: REST'
            if self.current_rep < self.total_reps: return f'Next: WORK #{self.current_rep+1}'
            return 'Next: COOLDOWN' if self.cooldown_secs > 0 else 'Next: DONE'
        if self.phase == 'rest':
            if self.current_rep < self.total_reps: return f'Next: WORK #{self.current_rep+1}'
            return 'Next: COOLDOWN' if self.cooldown_secs > 0 else 'Next: DONE'
        return ''

    def _pause(self):
        self.running = False
        if self._clock_event: self._clock_event.cancel()
        elapsed = time.monotonic() - self.phase_start
        self.phase_remaining = max(0, self.phase_remaining - elapsed)
        ids = self.screen.ids
        ids.phase_label.text  = 'PAUSED'; ids.phase_label.color = self.PHASE_STYLE['paused'][1]
        ids.interval_start_btn.text = 'RESUME'
        ids.interval_start_btn.background_color = (0.2, 0.4, 0.8, 1)

    def _resume(self):
        self.running = True; self.phase_start = time.monotonic()
        label, color = self.PHASE_STYLE.get(self.phase, ('', (1,1,1,1)))
        ids = self.screen.ids
        ids.phase_label.text  = f'{label}  #{self.current_rep}' if self.phase=='work' else label
        ids.phase_label.color = color
        ids.interval_start_btn.text = 'PAUSE'
        ids.interval_start_btn.background_color = (0.7, 0.4, 0.1, 1)
        self._clock_event = Clock.schedule_interval(self._tick, 0.1)

    def _finish(self):
        self.running = False; self.phase = 'idle'
        if self._clock_event: self._clock_event.cancel()
        ids = self.screen.ids
        ids.phase_label.text  = 'DONE!'; ids.phase_label.color = self.PHASE_STYLE['done'][1]
        ids.interval_timer_label.text = '00:00'; ids.next_label.text = ''
        ids.interval_start_btn.text = 'START'
        ids.interval_start_btn.background_color = (0.2, 0.4, 0.8, 1)
        self._log('Workout complete!')
        notify_phase_complete('Workout complete!', 'All reps done. Great work!')

    def reset_interval(self):
        if self._clock_event: self._clock_event.cancel()
        self.running = False; self.phase = 'idle'; self.current_rep = 0
        ids = self.screen.ids
        ids.phase_label.text  = 'READY'; ids.phase_label.color = self.PHASE_STYLE['idle'][1]
        ids.interval_timer_label.text = '00:00'
        ids.rep_label.text = ''; ids.next_label.text = ''
        ids.interval_start_btn.text = 'START'
        ids.interval_start_btn.background_color = (0.2, 0.4, 0.8, 1)
        ids.interval_log_grid.clear_widgets()

    def _tick(self, dt):
        elapsed   = time.monotonic() - self.phase_start
        remaining = max(0.0, self.phase_remaining - elapsed)
        self.screen.ids.interval_timer_label.text = fmt_time(remaining)
        if remaining > 0:
            return
        self._clock_event.cancel()
        phase = self.phase
        if phase == 'warmup':
            self._log('Warmup done')
            notify_phase_complete('Warmup done', f'Starting Rep 1 / {self.total_reps}')
            self._next_work()
        elif phase == 'work':
            self._log(f'Rep {self.current_rep} done')
            next_msg = ('Rest next' if self.rest_secs > 0
                        else f'Rep {self.current_rep+1}' if self.current_rep < self.total_reps
                        else 'Cooldown' if self.cooldown_secs > 0 else 'Done!')
            notify_phase_complete(f'Rep {self.current_rep} done', next_msg)
            if self.rest_secs > 0: self._start_phase('rest', self.rest_secs)
            else: self._next_work()
        elif phase == 'rest':
            self._log('Rest done')
            notify_phase_complete('Rest done', f'Rep {self.current_rep+1}')
            self._next_work()
        elif phase == 'cooldown':
            self._log('Cooldown done')
            notify_phase_complete('Cooldown done', 'Workout complete!')
            self._finish()

    def _log(self, text):
        lbl = Label(text=text, font_size=dp(13), color=(0.65, 0.65, 0.65, 1),
                    size_hint_y=None, height=dp(28))
        self.screen.ids.interval_log_grid.add_widget(lbl)


# ── App ───────────────────────────────────────────────────────────────────────

class RunningApp(App):
    def build(self):
        self._strava_file     = os.path.join(self.user_data_dir, 'strava_auth.json')
        self.strava           = self._load_strava()
        self.store            = RunDataStore(self.user_data_dir)
        self._auth_on_success = None
        self._auth_on_error   = None
        self._last_oauth_code = None  # deduplicate cold-start + new-intent

        root = Builder.load_string(KV)

        self.run_list        = RunListLogic(root.get_screen('runlist'), self.store, self.strava)
        self.run_detail      = RunDetailLogic(root.get_screen('rundetail'), self.store, self.strava)
        self.split_analysis  = SplitAnalysisLogic(root.get_screen('splits'))
        self.interval_screen = IntervalScreenLogic(root.get_screen('interval'))

        # Bind to onNewIntent (fires when app is already running and deep link arrives)
        # Use a free closure — bound-method signature causes arg-count mismatches on some p4a builds
        try:
            from android.activity import bind as android_bind
            app_ref = self
            def _new_intent_handler(intent):
                app_ref._handle_oauth_intent(intent)
            android_bind(on_new_intent=_new_intent_handler)
        except Exception:
            pass

        return root

    def on_start(self):
        # Cold-start via deep link: getIntent() holds the URI on first launch
        Clock.schedule_once(lambda dt: self._check_cold_start_intent(), 0.5)

    def on_resume(self):
        # Warm-start via deep link: onNewIntent fires but android.activity.bind
        # may not relay it; re-reading getIntent() after resume is reliable.
        Clock.schedule_once(lambda dt: self._check_cold_start_intent(), 0.1)

    def _check_cold_start_intent(self):
        try:
            from jnius import autoclass
            intent = autoclass('org.kivy.android.PythonActivity').mActivity.getIntent()
            self._handle_oauth_intent(intent)
        except Exception:
            pass

    def _handle_oauth_intent(self, intent):
        """Shared handler for both cold-start and new-intent paths."""
        # ── Step 1: extract URI data — isolated so setData can't kill this ──
        code, error = None, None
        try:
            uri = intent.getData()
            if uri is None or uri.getScheme() != 'runningapp':
                return
            code  = uri.getQueryParameter('code')
            error = uri.getQueryParameter('error')
        except Exception:
            return

        if not code and not error:
            return

        # ── Step 2: deduplicate ───────────────────────────────────────────
        if code and code == self._last_oauth_code:
            return
        self._last_oauth_code = code

        # ── Step 3: clear intent — best-effort, must NOT kill code ────────
        try:
            intent.setData(None)
            from jnius import autoclass
            autoclass('org.kivy.android.PythonActivity').mActivity.setIntent(intent)
        except Exception:
            pass  # dedup flag is the safety net

        # ── Step 4: grab stored callbacks (may be None if app was killed) ─
        on_success = self._auth_on_success
        on_error   = self._auth_on_error
        self._auth_on_success = None
        self._auth_on_error   = None

        def _ui_error(msg):
            try:
                self.run_list.screen.ids.strava_btn.text = 'Strava'
                self.run_list._status(f'Auth error: {msg}')
            except Exception:
                pass
            if on_error:
                on_error(msg)

        if error:
            Clock.schedule_once(lambda dt: _ui_error(f'Strava denied: {error}'))
            return

        # ── Step 5: exchange code for token in background thread ──────────
        def exchange():
            try:
                self.strava._exchange(code)
                self.save_strava_creds()
                if on_success:
                    Clock.schedule_once(lambda dt: on_success())
                else:
                    Clock.schedule_once(lambda dt: self._recover_after_auth())
            except Exception as e:
                msg = str(e)
                Clock.schedule_once(lambda dt: _ui_error(msg))

        threading.Thread(target=exchange, daemon=True).start()

    def _recover_after_auth(self):
        self.root.current = 'runlist'
        self.run_list.screen.ids.strava_btn.text = 'Sync'
        self.run_list._status('Connected! Fetching runs…')
        self.run_list._sync_strava()

    def _load_strava(self):
        try:
            with open(self._strava_file) as f:
                return StravaClient.from_dict(json.load(f))
        except Exception:
            return StravaClient()

    def save_strava_creds(self):
        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            with open(self._strava_file, 'w') as f:
                json.dump(self.strava.to_dict(), f)
        except Exception:
            pass

    def open_run_detail(self, run):
        self.run_detail.load(run)
        self.root.current = 'rundetail'

    def open_split_analysis(self, run):
        self.split_analysis.load(run)
        self.root.current = 'splits'

    def go_home(self):
        if self.interval_screen.running:
            self.interval_screen._pause()
        self.root.current = 'home'


if __name__ == '__main__':
    RunningApp().run()
