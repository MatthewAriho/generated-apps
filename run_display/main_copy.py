"""
Running App — My Runs (Strava/CSV import) + Interval Training
"""
import os, json, csv, time, threading, webbrowser
import urllib.request, urllib.parse
from datetime import datetime, timezone

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
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import StringProperty, BooleanProperty
from kivy.metrics import dp


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
    TOKEN_URL  = 'https://www.strava.com/oauth/token'
    API_BASE   = 'https://www.strava.com/api/v3'
    REDIRECT   = 'runningapp://auth/callback'

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
        """Open the Strava auth page. The deep-link intent will be caught
        by RunningApp._on_new_intent() when Android redirects back."""
        webbrowser.open(self.auth_url())

    def _exchange(self, code):
        data = urllib.parse.urlencode({
            'client_id': self.client_id, 'client_secret': self.client_secret,
            'code': code, 'grant_type': 'authorization_code',
        }).encode()
        with urllib.request.urlopen(urllib.request.Request(self.TOKEN_URL, data=data), timeout=30) as r:
            t = json.loads(r.read())
        self.access_token = t['access_token']
        self.refresh_token = t['refresh_token']
        self.token_expiry = t.get('expires_at', 0)

    def _do_token_refresh(self):
        """Exchange refresh_token for a new access_token."""
        data = urllib.parse.urlencode({
            'client_id': self.client_id, 'client_secret': self.client_secret,
            'refresh_token': self.refresh_token, 'grant_type': 'refresh_token',
        }).encode()
        with urllib.request.urlopen(urllib.request.Request(self.TOKEN_URL, data=data), timeout=30) as r:
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
        if self.refresh_token and (not self.token_expiry or time.time() >= self.token_expiry - 300):
            self._do_token_refresh()
        req = urllib.request.Request(
            f"{self.API_BASE}{path}",
            headers={'Authorization': f'Bearer {self.access_token}'}
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 401 and self.refresh_token:
                # Access token expired — refresh and retry once
                self._do_token_refresh()
                req = urllib.request.Request(
                    f"{self.API_BASE}{path}",
                    headers={'Authorization': f'Bearer {self.access_token}'}
                )
                with urllib.request.urlopen(req, timeout=30) as r:
                    return json.loads(r.read())
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
        keys = 'time,distance,heartrate,altitude,velocity_smooth'
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
            rgba: 0.07, 0.07, 0.09, 1
        Rectangle:
            pos: self.pos
            size: self.size
    BoxLayout:
        orientation: 'vertical'
        padding: dp(28)
        spacing: dp(22)
        Widget:
            size_hint_y: None
            height: dp(40)
        Label:
            text: 'RUNNING'
            font_size: dp(30)
            bold: True
            color: 0.99, 0.30, 0.01, 1
            size_hint_y: None
            height: dp(50)
        Label:
            text: 'Track. Analyse. Improve.'
            font_size: dp(14)
            color: 0.50, 0.50, 0.55, 1
            size_hint_y: None
            height: dp(26)
        Widget:
            size_hint_y: None
            height: dp(20)
        Button:
            text: 'MY RUNS'
            font_size: dp(20)
            bold: True
            size_hint_y: None
            height: dp(90)
            background_color: 0.99, 0.30, 0.01, 1
            on_press: app.root.current = 'runlist'
        Button:
            text: 'INTERVAL TRAINING'
            font_size: dp(18)
            bold: True
            size_hint_y: None
            height: dp(90)
            background_color: 0.18, 0.28, 0.60, 1
            on_press: app.root.current = 'interval'
        Widget:

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
            height: dp(52)
            padding: dp(8), dp(6)
            spacing: dp(6)
            canvas.before:
                Color:
                    rgba: 0.11, 0.11, 0.14, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            Button:
                text: '< Home'
                font_size: dp(13)
                size_hint_x: None
                width: dp(70)
                background_color: 0, 0, 0, 0
                color: 0.50, 0.50, 0.55, 1
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
        # Status bar
        Label:
            id: status_label
            text: ''
            font_size: dp(12)
            color: 0.50, 0.50, 0.55, 1
            size_hint_y: None
            height: dp(24)
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
            height: dp(52)
            padding: dp(8), dp(6)
            spacing: dp(6)
            canvas.before:
                Color:
                    rgba: 0.11, 0.11, 0.14, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            Button:
                text: '< Runs'
                font_size: dp(13)
                size_hint_x: None
                width: dp(70)
                background_color: 0, 0, 0, 0
                color: 0.50, 0.50, 0.55, 1
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

# ── Split analysis ─────────────────────────────────────────────────────────
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
            height: dp(52)
            padding: dp(8), dp(6)
            spacing: dp(6)
            canvas.before:
                Color:
                    rgba: 0.11, 0.11, 0.14, 1
                Rectangle:
                    pos: self.pos
                    size: self.size
            Button:
                text: '< Detail'
                font_size: dp(13)
                size_hint_x: None
                width: dp(70)
                background_color: 0, 0, 0, 0
                color: 0.50, 0.50, 0.55, 1
                on_press: app.root.current = 'rundetail'
            Label:
                text: 'Split Analysis'
                font_size: dp(17)
                bold: True
                color: 0.95, 0.95, 0.95, 1
        # Interval selector
        ScrollView:
            size_hint_y: None
            height: dp(46)
            do_scroll_y: False
            BoxLayout:
                id: interval_btns
                orientation: 'horizontal'
                size_hint_x: None
                width: self.minimum_width
                spacing: dp(6)
                padding: dp(8), dp(6)
        # Table header
        GridLayout:
            id: table_header
            cols: 5
            size_hint_y: None
            height: dp(30)
            padding: dp(8), 0
            spacing: dp(2)
        # Split rows
        ScrollView:
            GridLayout:
                id: splits_table
                cols: 5
                size_hint_y: None
                height: self.minimum_height
                padding: dp(8), 0
                spacing: dp(2), dp(3)
        Label:
            id: splits_status
            text: ''
            font_size: dp(13)
            color: 0.50, 0.50, 0.55, 1
            size_hint_y: None
            height: dp(30)

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
            height: dp(46)
            Button:
                text: '< Home'
                size_hint_x: 0.25
                font_size: dp(14)
                background_color: 0.3, 0.3, 0.3, 1
                on_press: app.go_home()
            Label:
                text: 'INTERVALS'
                font_size: dp(18)
                bold: True
                color: 0.3, 0.6, 1, 1
            Widget:
                size_hint_x: 0.25

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
            padding: dp(8)
            canvas.before:
                Color:
                    rgba: 0.15, 0.15, 0.2, 1
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [dp(10)]

            Label:
                text: 'CONFIGURE'
                font_size: dp(12)
                color: 0.45, 0.45, 0.45, 1
                size_hint_y: None
                height: dp(22)

            BoxLayout:
                size_hint_y: None
                height: dp(42)
                Label:
                    text: 'WARMUP'
                    font_size: dp(12)
                    color: 0.9, 0.7, 0.2, 1
                    size_hint_x: 0.28
                Button:
                    text: '-'
                    font_size: dp(20)
                    bold: True
                    size_hint_x: 0.16
                    background_color: 0.4, 0.2, 0.2, 1
                    on_press: app.interval_screen.adjust_warmup(-60)
                Label:
                    id: warmup_time_label
                    text: '5:00'
                    font_size: dp(19)
                    bold: True
                    color: 0.9, 0.9, 0.9, 1
                Button:
                    text: '+'
                    font_size: dp(20)
                    bold: True
                    size_hint_x: 0.16
                    background_color: 0.2, 0.4, 0.2, 1
                    on_press: app.interval_screen.adjust_warmup(60)

            BoxLayout:
                size_hint_y: None
                height: dp(42)
                Label:
                    text: 'WORK'
                    font_size: dp(12)
                    color: 0.3, 0.8, 0.4, 1
                    size_hint_x: 0.28
                Button:
                    text: '-'
                    font_size: dp(20)
                    bold: True
                    size_hint_x: 0.16
                    background_color: 0.4, 0.2, 0.2, 1
                    on_press: app.interval_screen.adjust_work(-30)
                Label:
                    id: work_time_label
                    text: '3:00'
                    font_size: dp(19)
                    bold: True
                    color: 0.9, 0.9, 0.9, 1
                Button:
                    text: '+'
                    font_size: dp(20)
                    bold: True
                    size_hint_x: 0.16
                    background_color: 0.2, 0.4, 0.2, 1
                    on_press: app.interval_screen.adjust_work(30)

            BoxLayout:
                size_hint_y: None
                height: dp(42)
                Label:
                    text: 'REST'
                    font_size: dp(12)
                    color: 0.8, 0.3, 0.3, 1
                    size_hint_x: 0.28
                Button:
                    text: '-'
                    font_size: dp(20)
                    bold: True
                    size_hint_x: 0.16
                    background_color: 0.4, 0.2, 0.2, 1
                    on_press: app.interval_screen.adjust_rest(-30)
                Label:
                    id: rest_time_label
                    text: '1:00'
                    font_size: dp(19)
                    bold: True
                    color: 0.9, 0.9, 0.9, 1
                Button:
                    text: '+'
                    font_size: dp(20)
                    bold: True
                    size_hint_x: 0.16
                    background_color: 0.2, 0.4, 0.2, 1
                    on_press: app.interval_screen.adjust_rest(30)

            BoxLayout:
                size_hint_y: None
                height: dp(42)
                Label:
                    text: 'COOLDOWN'
                    font_size: dp(12)
                    color: 0.4, 0.7, 1, 1
                    size_hint_x: 0.28
                Button:
                    text: '-'
                    font_size: dp(20)
                    bold: True
                    size_hint_x: 0.16
                    background_color: 0.4, 0.2, 0.2, 1
                    on_press: app.interval_screen.adjust_cooldown(-60)
                Label:
                    id: cooldown_time_label
                    text: '5:00'
                    font_size: dp(19)
                    bold: True
                    color: 0.9, 0.9, 0.9, 1
                Button:
                    text: '+'
                    font_size: dp(20)
                    bold: True
                    size_hint_x: 0.16
                    background_color: 0.2, 0.4, 0.2, 1
                    on_press: app.interval_screen.adjust_cooldown(60)

            BoxLayout:
                size_hint_y: None
                height: dp(42)
                Label:
                    text: 'REPS'
                    font_size: dp(12)
                    color: 0.7, 0.5, 0.9, 1
                    size_hint_x: 0.28
                Button:
                    text: '-'
                    font_size: dp(20)
                    bold: True
                    size_hint_x: 0.16
                    background_color: 0.4, 0.2, 0.2, 1
                    on_press: app.interval_screen.adjust_reps(-1)
                Label:
                    id: reps_label
                    text: '6'
                    font_size: dp(19)
                    bold: True
                    color: 0.9, 0.9, 0.9, 1
                Button:
                    text: '+'
                    font_size: dp(20)
                    bold: True
                    size_hint_x: 0.16
                    background_color: 0.2, 0.4, 0.2, 1
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
                background_color: 0.2, 0.4, 0.8, 1
                on_press: app.interval_screen.toggle_interval()
            Button:
                text: 'RESET'
                font_size: dp(18)
                background_color: 0.6, 0.2, 0.2, 1
                size_hint_x: 0.38
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
        hr_text       = f'♥ {int(run.avg_hr)} bpm' if run.avg_hr else '',
        elev_text     = f'↑ {int(run.elevation_gain_m)} m' if run.elevation_gain_m else '',
        source_badge  = run.source.upper()[:7],
    )
    card.bind(on_press=on_tap)
    card._run = run
    return card


class RunListLogic:
    def __init__(self, screen, store, strava):
        self.screen = screen
        self.store  = store
        self.strava = strava
        try:
            self._refresh()
        except Exception:
            pass

    def _refresh(self):
        grid = self.screen.ids.runs_grid
        grid.clear_widgets()
        if not self.store.runs:
            lbl = Label(
                text='No runs yet.\nTap Strava to connect or CSV to import.',
                font_size=dp(14), color=(0.5, 0.5, 0.55, 1),
                size_hint_y=None, height=dp(80), halign='center',
                text_size=(dp(300), None),
            )
            grid.add_widget(lbl)
            return
        for run in self.store.runs:
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

    def _render_splits(self):
        table = self.screen.ids.splits_table
        table.clear_widgets()
        status = self.screen.ids.splits_status

        if self.run is None or not self.run.streams:
            status.text = 'No stream data available'
            return

        splits = compute_splits(self.run.streams, self.active_interval_m)
        if not splits:
            status.text = 'Not enough data for this interval size'
            return

        status.text = f'{len(splits)} splits at {self.active_interval_m/1000:.2f} km intervals'
        avg_pace = self.run.avg_pace_s_per_km

        for s in splits:
            color = pace_color(s['pace'], avg_pace)
            dist_label = (f"{s['dist_m']/1000:.2f} km"
                          if s['dist_m'] < self.active_interval_m * 0.99
                          else f"{self.active_interval_m/1000:.2f} km")
            row_data = [
                (str(s['num']),                0.08, (0.50, 0.50, 0.55, 1)),
                (dist_label,                   0.18, (0.85, 0.85, 0.85, 1)),
                (fmt_time(s['time_s']),        0.18, (0.95, 0.95, 0.95, 1)),
                (fmt_pace(s['pace']),          0.30, color),
                (f"{int(s['avg_hr'])}" if s['avg_hr'] else '--', 0.20, (0.90, 0.35, 0.35, 1)),
            ]
            for text, w, c in row_data:
                lbl = Label(text=text, font_size=dp(13), color=c,
                            size_hint_x=w, size_hint_y=None, height=dp(32))
                table.add_widget(lbl)


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
