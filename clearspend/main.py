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
from screens.dashboard        import DashboardTab        # noqa: F401
from screens.add_transaction  import AddTransactionScreen # noqa: F401
from screens.transaction_list import TransactionListTab   # noqa: F401
from screens.bank_connect     import BankConnectTab       # noqa: F401
from screens.settings         import SettingsTab          # noqa: F401
from screens.trends           import TrendsScreen         # noqa: F401
from screens.budget           import BudgetScreen         # noqa: F401
from screens.pin_auth         import PinAuthScreen        # noqa: F401

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
                selected_color_background: app.theme_cls.primary_color

                MDBottomNavigationItem:
                    name: 'dashboard'
                    text: 'Home'
                    icon: 'home'
                    on_tab_press: app.refresh_dashboard()

                    DashboardTab:
                        id: dashboard_tab

                MDBottomNavigationItem:
                    name: 'history'
                    text: 'History'
                    icon: 'history'
                    on_tab_press: app.refresh_history()

                    TransactionListTab:
                        id: history_tab

                MDBottomNavigationItem:
                    name: 'bank'
                    text: 'Bank'
                    icon: 'bank'
                    on_tab_press: app.refresh_bank()

                    BankConnectTab:
                        id: bank_tab

                MDBottomNavigationItem:
                    name: 'settings'
                    text: 'Settings'
                    icon: 'cog'

                    SettingsTab:
                        id: settings_tab

    AddTransactionScreen:
        name: 'add_transaction'

    TrendsScreen:
        name: 'trends'

    BudgetScreen:
        name: 'budget'

    PinAuthScreen:
        name: 'pin_auth'
"""


class ClearSpendApp(MDApp):
    is_online   = BooleanProperty(True)
    sync_status = StringProperty("idle")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cloud_sync = CloudSync()
        self._load_cloud_credentials()

    # ---------------------------------------------------------------- kivy
    def build(self):
        self.theme_cls.theme_style   = "Dark"
        self.theme_cls.primary_palette = "Teal"
        self.title = "ClearSpend"
        root = Builder.load_string(KV)
        # Start on PIN screen
        root.current = "pin_auth"
        # Init DB in background
        Clock.schedule_once(self._init_db, 0)
        # Check connectivity
        Clock.schedule_once(self._check_connectivity, 0.5)
        # Start spend alert checker (every 30 min)
        Clock.schedule_interval(self._check_spend_alert, 1800)
        return root

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

    # ---------------------------------------------------------------- navigation
    def go_to_add(self):
        self.root.transition.direction = "left"
        self.root.current = "add_transaction"

    def go_back(self):
        self.root.transition.direction = "right"
        self.root.current = "home"

    def go_to_history(self):
        try:
            self.root.ids.nav.switch_tab("history")
        except Exception:
            pass

    def go_to_trends(self):
        self.root.transition.direction = "left"
        self.root.current = "trends"

    def go_to_budget(self):
        self.root.transition.direction = "left"
        self.root.current = "budget"

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


if __name__ == "__main__":
    ClearSpendApp().run()
