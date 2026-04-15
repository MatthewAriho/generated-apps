"""Settings tab - connectivity toggle, cloud sync config, app info."""
from __future__ import annotations

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
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
            adaptive_height: True
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
                adaptive_height: True
                radius: [dp(10)]

                MDBoxLayout:
                    adaptive_height: True

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
                adaptive_height: True
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
                    adaptive_height: True
                    spacing: dp(8)

                    MDRaisedButton:
                        text: "BACKUP NOW"
                        size_hint_x: 1
                        size_hint_y: None
                        height: dp(42)
                        on_release: root.do_backup()
                        md_bg_color: app.theme_cls.primary_color

                    MDRaisedButton:
                        text: "RESTORE"
                        size_hint_x: 1
                        size_hint_y: None
                        height: dp(42)
                        on_release: root.do_restore()
                        md_bg_color: app.theme_cls.primary_dark

                MDLabel:
                    id: sync_status_label
                    text: root.sync_status_text
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
                adaptive_height: True
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
                adaptive_height: True
                radius: [dp(10)]
                spacing: dp(8)

                MDRaisedButton:
                    text: "VIEW SPENDING TRENDS"
                    size_hint_y: None
                    height: dp(42)
                    on_release: app.go_to_trends()
                    md_bg_color: app.theme_cls.primary_color

                MDRaisedButton:
                    text: "SET MONTHLY BUDGET"
                    size_hint_y: None
                    height: dp(42)
                    on_release: app.go_to_budget()
                    md_bg_color: app.theme_cls.primary_dark

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
                adaptive_height: True
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
