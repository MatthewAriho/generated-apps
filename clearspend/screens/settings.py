"""Settings tab - connectivity toggle, cloud sync config, app info."""
from __future__ import annotations
import csv
import os

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.utils import platform
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.snackbar import Snackbar

KV = """
<SettingsTab>:
    orientation: 'vertical'
    md_bg_color: app.theme_cls.bg_normal

    MDTopAppBar:
        title: "Settings"
        elevation: 2

    ScrollView:
        do_scroll_x: False

        MDBoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            padding: [dp(16), dp(12)]
            spacing: dp(4)

            # ── Connectivity ─────────────────────────────────────────
            MDLabel:
                text: "CONNECTIVITY"
                font_style: "Overline"
                theme_text_color: "Secondary"
                adaptive_height: True
                padding: [dp(4), dp(8), 0, dp(4)]

            MDCard:
                orientation: 'vertical'
                padding: [dp(16), dp(12)]
                size_hint_y: None
                height: self.minimum_height
                radius: [dp(10)]

                MDBoxLayout:
                    size_hint_y: None
                    height: self.minimum_height

                    MDLabel:
                        text: "Mode"
                        font_style: "Body1"
                        adaptive_height: True

                    MDLabel:
                        id: online_status_label
                        text: root.connectivity_text
                        halign: "right"
                        theme_text_color: "Custom"
                        text_color:
                            (0.3, 0.9, 0.4, 1) if app.is_online else (0.9, 0.4, 0.3, 1)
                        font_style: "Body1"
                        adaptive_height: True

                MDLabel:
                    text: "ClearSpend works offline. Transactions are saved locally."
                    font_style: "Caption"
                    theme_text_color: "Secondary"
                    adaptive_height: True

                MDRaisedButton:
                    text: "RECHECK CONNECTION"
                    size_hint_y: None
                    height: dp(40)
                    on_release: root.recheck_connectivity()
                    md_bg_color: app.theme_cls.primary_dark
                    elevation: 0

            # ── Cloud Backup ──────────────────────────────────────────
            MDLabel:
                text: "CLOUD BACKUP (JSONBIN.IO)"
                font_style: "Overline"
                theme_text_color: "Secondary"
                adaptive_height: True
                padding: [dp(4), dp(16), 0, dp(4)]

            MDCard:
                orientation: 'vertical'
                padding: [dp(16), dp(12)]
                size_hint_y: None
                height: self.minimum_height
                radius: [dp(10)]
                spacing: dp(10)

                MDLabel:
                    text: "Get a free API key at jsonbin.io. Your data is encrypted before upload."
                    font_style: "Caption"
                    theme_text_color: "Secondary"
                    adaptive_height: True

                MDTextField:
                    id: api_key_field
                    hint_text: "JSONBin API Key ($2b$...)"
                    mode: "rectangle"
                    password: True
                    size_hint_y: None
                    height: dp(56)
                    text: root.saved_api_key

                MDTextField:
                    id: bin_id_field
                    hint_text: "Bin ID (auto-filled on first backup)"
                    mode: "rectangle"
                    size_hint_y: None
                    height: dp(56)
                    text: root.saved_bin_id

                MDBoxLayout:
                    size_hint_y: None
                    height: dp(42)
                    spacing: dp(8)

                    MDRaisedButton:
                        text: "BACKUP NOW"
                        size_hint_x: 1
                        size_hint_y: None
                        height: dp(42)
                        on_release: root.do_backup()
                        md_bg_color: app.theme_cls.primary_color
                        elevation: 0

                    MDRaisedButton:
                        text: "RESTORE"
                        size_hint_x: 1
                        size_hint_y: None
                        height: dp(42)
                        on_release: root.do_restore()
                        md_bg_color: app.theme_cls.primary_dark
                        elevation: 0

                MDLabel:
                    id: sync_status_label
                    text: root.sync_status_text
                    font_style: "Caption"
                    theme_text_color: "Secondary"
                    adaptive_height: True
                    halign: "center"

            # ── Plaid Integration ────────────────────────────────────
            MDLabel:
                text: "PLAID INTEGRATION"
                font_style: "Overline"
                theme_text_color: "Secondary"
                adaptive_height: True
                padding: [dp(4), dp(16), 0, dp(4)]

            MDCard:
                orientation: 'vertical'
                padding: [dp(16), dp(12)]
                size_hint_y: None
                height: self.minimum_height
                radius: [dp(10)]
                spacing: dp(10)

                MDLabel:
                    text: "Connect real bank accounts via Plaid. Get sandbox keys at dashboard.plaid.com."
                    font_style: "Caption"
                    theme_text_color: "Secondary"
                    adaptive_height: True

                MDTextField:
                    id: plaid_client_id_field
                    hint_text: "Client ID"
                    mode: "rectangle"
                    size_hint_y: None
                    height: dp(56)
                    text: root.saved_plaid_client_id

                MDTextField:
                    id: plaid_secret_field
                    hint_text: "Secret"
                    mode: "rectangle"
                    password: True
                    size_hint_y: None
                    height: dp(56)
                    text: root.saved_plaid_secret

                MDBoxLayout:
                    size_hint_y: None
                    height: dp(36)
                    spacing: dp(4)

                    MDLabel:
                        text: "Environment:"
                        font_style: "Caption"
                        adaptive_height: True

                    MDRaisedButton:
                        id: plaid_env_btn
                        text: root.saved_plaid_env.upper()
                        size_hint_x: None
                        width: dp(120)
                        size_hint_y: None
                        height: dp(36)
                        font_size: "11sp"
                        on_release: root.cycle_plaid_env()
                        md_bg_color: app.theme_cls.primary_dark
                        elevation: 0

                MDRaisedButton:
                    text: "SAVE PLAID CREDENTIALS"
                    size_hint_y: None
                    height: dp(42)
                    on_release: root.save_plaid_credentials()
                    md_bg_color: app.theme_cls.primary_color
                    elevation: 0

                MDLabel:
                    id: plaid_status_label
                    text: root.plaid_status_text
                    font_style: "Caption"
                    theme_text_color: "Secondary"
                    adaptive_height: True
                    halign: "center"

            # ── Security ─────────────────────────────────────────────
            MDLabel:
                text: "SECURITY"
                font_style: "Overline"
                theme_text_color: "Secondary"
                adaptive_height: True
                padding: [dp(4), dp(16), 0, dp(4)]

            MDCard:
                orientation: 'vertical'
                padding: [dp(16), dp(12)]
                size_hint_y: None
                height: self.minimum_height
                radius: [dp(10)]
                spacing: dp(8)

                MDLabel:
                    text: "PIN lock protects your financial data on app launch."
                    font_style: "Caption"
                    theme_text_color: "Secondary"
                    adaptive_height: True

                MDRaisedButton:
                    text: "CHANGE PIN"
                    size_hint_y: None
                    height: dp(42)
                    on_release: root.change_pin()
                    md_bg_color: app.theme_cls.primary_dark
                    elevation: 0

            # ── Analytics ─────────────────────────────────────────────
            MDLabel:
                text: "ANALYTICS"
                font_style: "Overline"
                theme_text_color: "Secondary"
                adaptive_height: True
                padding: [dp(4), dp(16), 0, dp(4)]

            MDCard:
                orientation: 'vertical'
                padding: [dp(16), dp(12)]
                size_hint_y: None
                height: self.minimum_height
                radius: [dp(10)]
                spacing: dp(8)

                MDRaisedButton:
                    text: "VIEW SPENDING TRENDS"
                    size_hint_y: None
                    height: dp(42)
                    on_release: app.go_to_trends()
                    md_bg_color: app.theme_cls.primary_color
                    elevation: 0

                MDRaisedButton:
                    text: "SET MONTHLY BUDGET"
                    size_hint_y: None
                    height: dp(42)
                    on_release: app.go_to_budget()
                    md_bg_color: app.theme_cls.primary_dark
                    elevation: 0

                MDRaisedButton:
                    text: "EXPORT CSV"
                    size_hint_y: None
                    height: dp(42)
                    on_release: root.do_export_csv()
                    md_bg_color: app.theme_cls.primary_dark
                    elevation: 0

            # ── Demo Mode ─────────────────────────────────────────────
            MDLabel:
                text: "DEMO MODE"
                font_style: "Overline"
                theme_text_color: "Secondary"
                adaptive_height: True
                padding: [dp(4), dp(16), 0, dp(4)]

            MDCard:
                orientation: 'vertical'
                padding: [dp(16), dp(12)]
                size_hint_y: None
                height: self.minimum_height
                radius: [dp(10)]
                spacing: dp(8)

                MDLabel:
                    text: "Load 3 months of realistic demo transactions and budgets to test all features."
                    font_style: "Caption"
                    theme_text_color: "Secondary"
                    adaptive_height: True

                MDRaisedButton:
                    text: "LOAD DEMO DATA"
                    size_hint_y: None
                    height: dp(42)
                    on_release: root.load_demo()
                    md_bg_color: [0.8, 0.5, 0.1, 1]
                    elevation: 0

                MDRaisedButton:
                    text: "CLEAR ALL DATA"
                    size_hint_y: None
                    height: dp(42)
                    on_release: root.clear_all_data()
                    md_bg_color: [0.7, 0.2, 0.2, 1]
                    elevation: 0

            # ── About ─────────────────────────────────────────────────
            MDLabel:
                text: "ABOUT"
                font_style: "Overline"
                theme_text_color: "Secondary"
                adaptive_height: True
                padding: [dp(4), dp(16), 0, dp(4)]

            MDCard:
                orientation: 'vertical'
                padding: [dp(16), dp(12)]
                size_hint_y: None
                height: self.minimum_height
                radius: [dp(10)]
                spacing: dp(4)

                MDLabel:
                    text: "ClearSpend"
                    font_style: "H6"
                    adaptive_height: True

                MDLabel:
                    text: "Version 0.3 | Built with KivyMD"
                    font_style: "Caption"
                    theme_text_color: "Secondary"
                    adaptive_height: True

                MDLabel:
                    text: "Track expenses, connect your bank, and take control\\nof your finances."
                    font_style: "Body2"
                    theme_text_color: "Secondary"
                    adaptive_height: True
"""

Builder.load_string(KV)


class SettingsTab(MDBoxLayout):
    connectivity_text  = StringProperty("Checking...")
    sync_status_text   = StringProperty("No backup yet this session.")
    saved_api_key      = StringProperty("")
    saved_bin_id       = StringProperty("")
    saved_plaid_client_id = StringProperty("")
    saved_plaid_secret    = StringProperty("")
    saved_plaid_env       = StringProperty("sandbox")
    plaid_status_text     = StringProperty("Not configured.")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self._load_stored, 0.5)
        Clock.schedule_once(self._update_connectivity, 0.6)

    # ----------------------------------------------------------------
    def _load_stored(self, *_):
        store = self._get_store()
        if store.exists("cloud"):
            data = store.get("cloud")
            self.saved_api_key = data.get("api_key", "")
            self.saved_bin_id  = data.get("bin_id", "")
        if store.exists("plaid"):
            data = store.get("plaid")
            self.saved_plaid_client_id = data.get("client_id", "")
            self.saved_plaid_secret    = data.get("secret", "")
            self.saved_plaid_env       = data.get("environment", "sandbox")
            if self.saved_plaid_client_id:
                self.plaid_status_text = f"Configured ({self.saved_plaid_env})"

    def _update_connectivity(self, *_):
        app = self._get_app()
        if app:
            self.connectivity_text = "[ON]  Online" if app.is_online else "[OFF] Offline"

    def recheck_connectivity(self):
        app = self._get_app()
        if app:
            app.check_connectivity()
        Clock.schedule_once(self._update_connectivity, 1.5)
        Snackbar(text="Checking connectivity...").open()

    # ---------------------------------------------------------------- cloud backup
    def _save_credentials(self):
        api_key = self.ids.api_key_field.text.strip()
        bin_id  = self.ids.bin_id_field.text.strip()
        store = self._get_store()
        store.put("cloud", api_key=api_key, bin_id=bin_id)
        self.saved_api_key = api_key
        self.saved_bin_id  = bin_id

        app = self._get_app()
        if app:
            app.cloud_sync.set_credentials(api_key, bin_id)

    def do_backup(self):
        self._save_credentials()
        api_key = self.ids.api_key_field.text.strip()
        if not api_key:
            Snackbar(text="Enter a JSONBin API key first.").open()
            return

        self.sync_status_text = "Backing up..."
        Snackbar(text="Starting backup...").open()

        def _do(*_):
            from models.database import Database
            app = self._get_app()
            if app:
                result = app.cloud_sync.backup(Database.get().export_to_dict())
                if result["success"]:
                    # Save the bin_id so future runs update the same bin
                    self.ids.bin_id_field.text = result.get("bin_id", "")
                    self._save_credentials()
                    self.sync_status_text = f"Backup successful. Bin: {result.get('bin_id','')[:12]}..."
                    Snackbar(text="Backup complete!").open()
                else:
                    self.sync_status_text = f"Backup failed: {result['error']}"
                    Snackbar(text=f"Backup failed: {result['error']}").open()

        Clock.schedule_once(_do, 0.3)

    def do_restore(self):
        self._save_credentials()
        if not self.saved_api_key or not self.saved_bin_id:
            Snackbar(text="Both API key and Bin ID are required to restore.").open()
            return

        self.sync_status_text = "Restoring..."

        def _do(*_):
            from models.database import Database
            app = self._get_app()
            if app:
                result = app.cloud_sync.restore()
                if result["success"]:
                    Database.get().import_from_dict(result["data"])
                    self.sync_status_text = "Restore complete."
                    Snackbar(text="Data restored from cloud!").open()
                    if app:
                        app.refresh_dashboard()
                else:
                    self.sync_status_text = f"Restore failed: {result['error']}"
                    Snackbar(text=f"Restore failed: {result['error']}").open()

        Clock.schedule_once(_do, 0.3)

    def change_pin(self):
        """Navigate to PIN screen in setup mode to reset PIN."""
        from kivy.storage.jsonstore import JsonStore
        import os
        from kivy.utils import platform
        # Clear existing PIN so setup mode triggers
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
        if store.exists("pin"):
            store.delete("pin")
        app = self._get_app()
        if app:
            app.root.transition.direction = "left"
            app.root.current = "pin_auth"

    # ---------------------------------------------------------------- plaid credentials
    def save_plaid_credentials(self):
        client_id = self.ids.plaid_client_id_field.text.strip()
        secret = self.ids.plaid_secret_field.text.strip()
        env = self.saved_plaid_env

        if not client_id or not secret:
            Snackbar(text="Enter both Client ID and Secret.").open()
            return

        store = self._get_store()
        store.put("plaid", client_id=client_id, secret=secret, environment=env)
        self.saved_plaid_client_id = client_id
        self.saved_plaid_secret = secret
        self.plaid_status_text = f"Saved ({env})"
        Snackbar(text="Plaid credentials saved.").open()

    def cycle_plaid_env(self):
        envs = ["sandbox", "development", "production"]
        idx = envs.index(self.saved_plaid_env) if self.saved_plaid_env in envs else 0
        self.saved_plaid_env = envs[(idx + 1) % len(envs)]

    # ---------------------------------------------------------------- demo mode
    def load_demo(self):
        app = self._get_app()
        if app:
            app.load_demo_data()

    def clear_all_data(self):
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton, MDRaisedButton

        def _confirm(*_):
            self._clear_dialog.dismiss()
            from models.database import Database
            db = Database.get()
            db.conn.execute("DELETE FROM transactions")
            db.conn.execute("DELETE FROM budgets")
            db.conn.execute("DELETE FROM bank_accounts")
            db.conn.commit()
            Snackbar(text="All data cleared.").open()
            app = self._get_app()
            if app:
                app.refresh_dashboard()

        self._clear_dialog = MDDialog(
            title="Clear all data?",
            text="This will delete all transactions, budgets, and bank accounts. This cannot be undone.",
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=lambda *_: self._clear_dialog.dismiss(),
                ),
                MDRaisedButton(
                    text="DELETE ALL",
                    md_bg_color=(0.85, 0.2, 0.2, 1),
                    on_release=_confirm,
                ),
            ],
        )
        self._clear_dialog.open()

    # ---------------------------------------------------------------- csv export
    def do_export_csv(self):
        """Export all transactions to a CSV file and show the path in a Snackbar."""
        try:
            from models.database import Database
            txns = Database.get().get_transactions(limit=100000)

            if platform == "android":
                try:
                    from kivy.app import App
                    base = App.get_running_app().user_data_dir
                except Exception:
                    base = os.path.expanduser("~")
            else:
                base = os.path.expanduser("~")

            out_path = os.path.join(base, "clearspend_export.csv")
            with open(out_path, "w", newline="", encoding="utf-8") as fh:
                writer = csv.DictWriter(
                    fh,
                    fieldnames=["date", "type", "category", "description", "amount", "source"],
                    extrasaction="ignore",
                )
                writer.writeheader()
                writer.writerows(txns)

            Snackbar(text=f"Exported to: {out_path}").open()
        except Exception as exc:
            Snackbar(text=f"Export failed: {exc}").open()

    # ----------------------------------------------------------------
    @staticmethod
    def _get_app():
        from kivy.app import App
        return App.get_running_app()

    @staticmethod
    def _get_store():
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
        return JsonStore(os.path.join(base, "settings.json"))
