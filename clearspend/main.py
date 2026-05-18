"""ClearSpend - main entry point.

Kivy/KivyMD Android budget tracker.  All KV layout strings are defined via
Builder.load_string() - no external .kv files.
"""
from __future__ import annotations

# Force portrait on desktop during dev
from kivy.config import Config
Config.set("graphics", "width",  "360")
Config.set("graphics", "height", "800")

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivymd.app import MDApp

# Import screens - each module calls Builder.load_string() at import time
from screens.dashboard         import DashboardTab          # noqa: F401
from screens.add_transaction   import AddTransactionScreen  # noqa: F401
from screens.edit_transaction  import EditTransactionScreen # noqa: F401
from screens.transaction_list  import TransactionListTab    # noqa: F401
from screens.bank_connect      import BankConnectTab        # noqa: F401
from screens.settings          import SettingsTab           # noqa: F401
from screens.trends            import TrendsContent           # noqa: F401
from screens.budget            import BudgetContent           # noqa: F401
from screens.goals             import GoalsTab              # noqa: F401
from screens.pin_auth          import PinAuthScreen         # noqa: F401

from utils.connectivity import is_online
from utils.cloud_sync   import CloudSync

KV = """
#:import SlideTransition kivy.uix.screenmanager.SlideTransition
ScreenManager:
    id: root_sm
    transition: SlideTransition()

    Screen:
        name: 'home'

        MDBoxLayout:
            orientation: 'vertical'

            MDBottomNavigation:
                id: nav
                transition_duration: 0.1
                text_color_active: 1, 1, 1, 1
                text_color_normal: 1, 1, 1, 0.5
                panel_color: app.theme_cls.bg_darkest

                MDBottomNavigationItem:
                    name: 'dashboard'
                    text: ' '
                    icon: 'home'
                    on_tab_press: app.refresh_dashboard()

                    DashboardTab:
                        id: dashboard_tab

                MDBottomNavigationItem:
                    name: 'history'
                    text: ' '
                    icon: 'history'
                    on_tab_press: app.refresh_history()

                    TransactionListTab:
                        id: history_tab

                MDBottomNavigationItem:
                    name: 'bank'
                    text: ' '
                    icon: 'bank'
                    on_tab_press: app.refresh_bank()

                    BankConnectTab:
                        id: bank_tab

                MDBottomNavigationItem:
                    name: 'trends'
                    text: ' '
                    icon: 'chart-line'
                    on_tab_press: app.refresh_trends()

                    TrendsContent:
                        id: trends_tab

                MDBottomNavigationItem:
                    name: 'budget'
                    text: ' '
                    icon: 'wallet'
                    on_tab_press: app.refresh_budget()

                    BudgetContent:
                        id: budget_tab

                MDBottomNavigationItem:
                    name: 'goals'
                    text: ' '
                    icon: 'flag-checkered'
                    on_tab_press: app.refresh_goals()

                    GoalsTab:
                        id: goals_tab

                MDBottomNavigationItem:
                    name: 'settings'
                    text: ' '
                    icon: 'cog'

                    SettingsTab:
                        id: settings_tab

    AddTransactionScreen:
        name: 'add_transaction'

    EditTransactionScreen:
        name: 'edit_transaction'

    PinAuthScreen:
        name: 'pin_auth'
"""


class ClearSpendApp(MDApp):
    is_online   = BooleanProperty(True)
    sync_status = StringProperty("idle")

    AUTO_LOCK_SECONDS = 300  # 5 minutes

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cloud_sync = CloudSync()
        self._load_cloud_credentials()
        self._last_activity = 0
        self._screen_history = []
        self._last_plaid_token = None

    # ---------------------------------------------------------------- kivy
    def build(self):
        self.theme_cls.theme_style   = "Dark"
        self.theme_cls.primary_palette = "Teal"
        self.title = "ClearSpend"
        try:
            root = Builder.load_string(KV)
        except Exception as exc:
            return self._crash_screen("KV build failed", exc)
        try:
            root.current = "pin_auth"
        except Exception as exc:
            return self._crash_screen("Screen switch failed", exc)
        # Init DB in background
        Clock.schedule_once(self._init_db, 0)
        # Check connectivity
        Clock.schedule_once(self._check_connectivity, 0.5)
        # Start spend alert checker (every 30 min)
        Clock.schedule_interval(self._check_spend_alert, 1800)
        # Check for deep link intent on cold start
        Clock.schedule_once(lambda *_: self._check_plaid_intent(), 1.0)
        # Bind on_new_intent for warm-start deep links (app already running)
        try:
            from android.activity import bind as android_bind
            app_ref = self
            def _plaid_intent_handler(intent):
                app_ref._handle_plaid_intent(intent)
            android_bind(on_new_intent=_plaid_intent_handler)
        except Exception:
            pass
        return root

    def _crash_screen(self, phase, exc):
        """Show exception on screen so it's readable without logcat."""
        import traceback
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.label import Label
        from kivy.uix.scrollview import ScrollView
        err = f"CRASH in {phase}:\n\n{traceback.format_exc()}"
        self._write_crash_log(err)
        sv = ScrollView()
        lbl = Label(
            text=err, halign="left", valign="top",
            size_hint_y=None, font_size="11sp",
            text_size=(340, None),
        )
        lbl.bind(texture_size=lbl.setter("size"))
        sv.add_widget(lbl)
        return sv

    def _write_crash_log(self, text):
        try:
            import os
            from kivy.utils import platform
            if platform == "android":
                try:
                    from android.storage import app_storage_path
                    base = app_storage_path()
                except Exception:
                    base = os.path.expanduser("~")
            else:
                base = os.path.join(os.path.expanduser("~"), ".clearspend")
            os.makedirs(base, exist_ok=True)
            with open(os.path.join(base, "crash_log.txt"), "w") as f:
                f.write(text)
        except Exception:
            pass

    def on_start(self):
        from kivy.core.window import Window
        Window.bind(on_keyboard=self._on_keyboard)
        # Android: also bind directly via the activity so back is never missed
        self._bind_android_back()

    def _bind_android_back(self):
        """Bind Android's native back button via the activity if on Android."""
        try:
            from kivy.utils import platform
            if platform != "android":
                return
            from jnius import autoclass
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            # Store ref so GC doesn't collect it
            self._python_activity = PythonActivity
        except Exception:
            pass

    def on_resume(self):
        """Check for Plaid deep link + WebView result + auto-lock on resume."""
        import time
        Clock.schedule_once(lambda *_: self._check_plaid_intent(), 0.5)
        # Pick up result from PlaidWebViewActivity (singleTask workaround)
        Clock.schedule_once(lambda *_: self._check_plaid_webview_result(), 0.3)
        # Auto-lock if idle too long
        if self._last_activity > 0:
            elapsed = time.time() - self._last_activity
            if elapsed > self.AUTO_LOCK_SECONDS:
                self.root.current = "pin_auth"

    def _check_plaid_webview_result(self):
        try:
            self.root.ids.bank_tab.check_plaid_webview_result()
        except Exception:
            pass

    def on_pause(self):
        """Record pause time for auto-lock calculation."""
        import time
        self._last_activity = time.time()
        return True

    def _init_db(self, *_):
        from models.database import Database
        Database.get()  # initialise singleton + create tables

    def _check_connectivity(self, *_):
        self.check_connectivity()
        # Schedule periodic recheck every 60s
        Clock.schedule_interval(lambda *_: self.check_connectivity(), 60)

    # ---------------------------------------------------------------- spend alerts (V2)
    def _check_spend_alert(self, *_):
        """Alert if >$50 or >$100 spent since last check-in."""
        try:
            from models.database import Database
            from kivymd.uix.snackbar import Snackbar
            from datetime import datetime, timedelta

            db = Database.get()
            ym = datetime.now().strftime("%Y-%m")
            s = db.get_monthly_summary(ym)
            spent = s.get("expense", 0)

            if spent >= 100:
                Snackbar(text=f"Heads up: you've spent ${spent:,.0f} this month!").open()
            elif spent >= 50:
                Snackbar(text=f"Spending check-in: ${spent:,.0f} spent this month.").open()
        except Exception:
            pass

    # ---------------------------------------------------------------- connectivity
    def check_connectivity(self):
        """Non-blocking connectivity probe."""
        from kivy.network.urlrequest import UrlRequest  # noqa
        def _probe(*_):
            self.is_online = is_online()
        Clock.schedule_once(_probe, 0)

    # ---------------------------------------------------------------- cloud
    def _load_cloud_credentials(self):
        try:
            from kivy.storage.jsonstore import JsonStore
            import os
            from kivy.utils import platform
            if platform == "android":
                try:
                    from android.storage import app_storage_path  # type: ignore
                    base = app_storage_path()
                except Exception:
                    base = os.path.expanduser("~")
            else:
                base = os.path.join(os.path.expanduser("~"), ".clearspend")
            os.makedirs(base, exist_ok=True)
            store = JsonStore(os.path.join(base, "settings.json"))
            if store.exists("cloud"):
                d = store.get("cloud")
                self.cloud_sync.set_credentials(
                    d.get("api_key", ""), d.get("bin_id", "")
                )
        except Exception:
            pass

    def sync_cloud(self):
        if not self.is_online:
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text="Cannot sync - offline.").open()
            return
        if not self.cloud_sync.api_key:
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text="Add a JSONBin API key in Settings to enable sync.").open()
            return

        self.sync_status = "syncing"

        def _do(*_):
            from models.database import Database
            from kivymd.uix.snackbar import Snackbar
            result = self.cloud_sync.backup(Database.get().export_to_dict())
            self.sync_status = "done" if result["success"] else "error"
            msg = "Backup complete!" if result["success"] else f"Sync failed: {result['error']}"
            Snackbar(text=msg).open()

        Clock.schedule_once(_do, 0.2)

    # ---------------------------------------------------------------- back button
    def on_back_pressed(self):
        """Called by Android native back button (KivyMD hook - most reliable)."""
        return self._handle_back()

    def _on_keyboard(self, window, key, *args):
        """Intercept Android hardware back button (key 27 / 1001) - desktop fallback."""
        if key in (27, 1001):
            return self._handle_back()
        return False

    def _handle_back(self):
        if self.root is None:
            return False
        current = self.root.current
        # On PIN screen, let system handle (exit app)
        if current == "pin_auth":
            return False
        # On home screen with bottom nav: handle tab switching or exit
        if current == "home":
            try:
                nav = self.root.ids.nav
                active = nav.current
                if active != "dashboard":
                    # Switch back to dashboard tab first
                    nav.switch_tab("dashboard")
                    return True
            except Exception:
                pass
            return False  # Let system minimise/exit from dashboard
        # On any other screen: pop history or go home
        if self._screen_history:
            prev = self._screen_history.pop()
            self.root.transition.direction = "right"
            self.root.current = prev
            return True
        self.root.transition.direction = "right"
        self.root.current = "home"
        return True

    def _push_history(self):
        current = self.root.current
        if current not in ("pin_auth",):
            self._screen_history.append(current)

    # ---------------------------------------------------------------- navigation
    def go_to_add(self):
        self._push_history()
        self.root.transition.direction = "left"
        self.root.current = "add_transaction"

    def go_to_edit(self, txn_id: int):
        from models.database import Database
        txns = Database.get().get_transactions(limit=100000)
        txn = next((t for t in txns if t["id"] == txn_id), None)
        if txn is None:
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text="Transaction not found.").open()
            return
        edit_screen = self.root.get_screen("edit_transaction")
        edit_screen.load_transaction(txn)
        self._push_history()
        self.root.transition.direction = "left"
        self.root.current = "edit_transaction"

    def go_back(self):
        if self._screen_history:
            prev = self._screen_history.pop()
            self.root.transition.direction = "right"
            self.root.current = prev
        else:
            self.root.transition.direction = "right"
            self.root.current = "home"

    def go_to_history(self):
        try:
            self.root.ids.nav.switch_tab("history")
        except Exception:
            pass

    def go_to_trends(self):
        try:
            self.root.ids.nav.switch_tab("trends")
        except Exception:
            self._push_history()
            self.root.transition.direction = "left"
            self.root.current = "trends"

    def go_to_budget(self):
        try:
            self.root.ids.nav.switch_tab("budget")
        except Exception:
            self._push_history()
            self.root.transition.direction = "left"
            self.root.current = "budget"

    def go_to_goals(self):
        try:
            self.root.ids.nav.switch_tab("goals")
        except Exception:
            pass

    # ---------------------------------------------------------------- plaid deep link
    def _plaid_log(self, msg):
        try:
            import os, datetime
            from android.storage import app_storage_path
            base = app_storage_path()
            with open(os.path.join(base, "plaid_debug.txt"), "a") as f:
                f.write(f"[{datetime.datetime.now()}] {msg}\n")
        except Exception:
            pass

    def _check_plaid_intent(self):
        """Cold-start / resume wrapper: read getIntent() and forward."""
        from kivy.utils import platform
        if platform != "android":
            return
        try:
            from jnius import autoclass
            intent = autoclass("org.kivy.android.PythonActivity").mActivity.getIntent()
            self._handle_plaid_intent(intent)
        except Exception:
            pass

    def _handle_plaid_intent(self, intent):
        """Shared handler for both cold-start and on_new_intent paths."""
        code = None
        try:
            self._plaid_log(f"_handle_plaid_intent called, intent={'None' if intent is None else 'present'}")
            if intent is None:
                return
            uri = intent.getData()
            self._plaid_log(f"uri={uri} scheme={str(uri.getScheme() or '') if uri else 'N/A'} host={str(uri.getHost() or '') if uri else 'N/A'}")
            if uri is None or str(uri.getScheme() or "") != "clearspend":
                return
            if str(uri.getHost() or "") != "plaid-callback":
                return
            # Log ALL query params so we can see what Plaid actually sends
            try:
                query = str(uri.getQuery() or "")
                self._plaid_log(f"full query string: {query}")
            except Exception as qe:
                self._plaid_log(f"query log error: {qe}")
            code = str(uri.getQueryParameter("public_token") or "")
            if not code:
                # Try alternate param names Plaid Hosted Link may use
                code = str(uri.getQueryParameter("oauth_state_id") or "")
                if code:
                    self._plaid_log(f"found oauth_state_id instead of public_token")
            self._plaid_log(f"token={'present' if code else 'MISSING'}")
        except Exception:
            return

        if not code:
            return

        if code == self._last_plaid_token:
            return
        self._last_plaid_token = code

        try:
            intent.setData(None)
            from jnius import autoclass
            autoclass("org.kivy.android.PythonActivity").mActivity.setIntent(intent)
        except Exception:
            pass

        Clock.schedule_once(lambda *_: self._process_plaid_token(code), 0.3)

    def _process_plaid_token(self, public_token: str):
        """Route the Plaid public_token to BankConnectTab for processing."""
        try:
            bank_tab = self.root.ids.bank_tab
            bank_tab._handle_plaid_callback(public_token)
            self.root.ids.nav.switch_tab("bank")
        except Exception as e:
            from kivymd.uix.snackbar import Snackbar
            Snackbar(text=f"Plaid callback error: {e}").open()

    # ---------------------------------------------------------------- demo mode
    def load_demo_data(self):
        """Seed database with realistic demo transactions and budgets."""
        from models.database import Database
        from kivymd.uix.snackbar import Snackbar
        db = Database.get()
        db.seed_demo_data()
        self.refresh_dashboard()
        Snackbar(text="Demo data loaded!").open()

    # ---------------------------------------------------------------- refresh helpers
    def refresh_dashboard(self, *_):
        try:
            self.root.ids.dashboard_tab.refresh()
        except Exception:
            pass

    def refresh_history(self, *_):
        try:
            self.root.ids.history_tab.refresh()
        except Exception:
            pass

    def refresh_bank(self, *_):
        try:
            self.root.ids.bank_tab.refresh()
        except Exception:
            pass

    def refresh_trends(self, *_):
        try:
            self.root.ids.trends_tab.refresh()
        except Exception:
            pass

    def refresh_budget(self, *_):
        try:
            self.root.ids.budget_tab.refresh()
        except Exception:
            pass

    def refresh_goals(self, *_):
        try:
            self.root.ids.goals_tab.refresh()
        except Exception:
            pass


if __name__ == "__main__":
    ClearSpendApp().run()
