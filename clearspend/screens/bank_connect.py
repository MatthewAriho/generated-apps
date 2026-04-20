"""Bank connect tab - connect accounts, mock OAuth flow, sync transactions."""
from __future__ import annotations

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.textfield import MDTextField

KV = """
<BankConnectTab>:
    orientation: 'vertical'
    md_bg_color: app.theme_cls.bg_normal

    MDTopAppBar:
        title: "Bank Accounts"
        elevation: 2
        right_action_items:
            [ \
              ["test-tube", lambda x: root.sandbox_test_connect(), "Sandbox test"], \
              ["plus", lambda x: root.show_bank_selector(), "Add bank"] \
            ]

    ScrollView:
        do_scroll_x: False

        MDBoxLayout:
            id: content_box
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            padding: [dp(12), dp(12)]
            spacing: dp(12)

            # ── No accounts placeholder ───────────────────────────────
            MDBoxLayout:
                id: empty_box
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(12)
                padding: [0, dp(40), 0, 0]

                MDIcon:
                    icon: "bank-off-outline"
                    halign: "center"
                    theme_text_color: "Secondary"
                    font_size: "52sp"
                    adaptive_height: True

                MDLabel:
                    text: "No bank accounts connected"
                    halign: "center"
                    theme_text_color: "Secondary"
                    adaptive_height: True

                MDLabel:
                    text: "Tap + above to connect Scotiabank\\nor another institution."
                    halign: "center"
                    theme_text_color: "Hint"
                    font_style: "Caption"
                    adaptive_height: True

            # ── Connected accounts list ───────────────────────────────
            MDBoxLayout:
                id: accounts_list
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)
"""

Builder.load_string(KV)


class BankConnectTab(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dialog: MDDialog | None = None
        Clock.schedule_once(self.refresh, 0.4)

    # ---------------------------------------------------------------- refresh
    def refresh(self, *_):
        from models.database import Database
        accounts = Database.get().get_bank_accounts()
        self.ids.accounts_list.clear_widgets()

        if accounts:
            self.ids.empty_box.opacity = 0
            self.ids.empty_box.size_hint_y = None
            self.ids.empty_box.height = 0
            for acc in accounts:
                self.ids.accounts_list.add_widget(self._make_account_card(acc))
        else:
            self.ids.empty_box.opacity = 1
            self.ids.empty_box.size_hint_y = None
            self.ids.empty_box.height = dp(200)

    def _make_account_card(self, acc: dict) -> MDCard:
        card = MDCard(
            orientation="vertical",
            padding=[dp(14), dp(12)],
            size_hint_y=None,
            height=dp(100),
            radius=[dp(12)],
            elevation=2,
        )
        row1 = MDBoxLayout(adaptive_height=True)
        row1.add_widget(MDLabel(
            text=f"{acc['bank_name']} - {acc['account_name']}",
            font_style="Subtitle1", adaptive_height=True,
        ))

        sync_btn = MDFlatButton(
            text="SYNC",
            theme_text_color="Custom",
            text_color=(0.3, 0.7, 1, 1),
            size_hint=(None, None),
            height=dp(32),
        )
        acc_id = acc["id"]
        sync_btn.bind(on_release=lambda *_: self.sync_account(acc_id))
        row1.add_widget(sync_btn)

        card.add_widget(row1)
        card.add_widget(MDLabel(
            text=f"Account: {acc.get('account_number_masked','****')}",
            font_style="Caption", theme_text_color="Secondary", adaptive_height=True,
        ))
        last = acc.get("last_sync","")
        if last:
            last = last[:10]
        card.add_widget(MDLabel(
            text=f"Last synced: {last or 'never'}",
            font_style="Caption", theme_text_color="Hint", adaptive_height=True,
        ))
        return card

    # ---------------------------------------------------------------- bank selector
    def show_bank_selector(self):
        plaid_btn = MDRaisedButton(
            text="Plaid",
            size_hint_x=None,
            width=dp(100),
            on_release=lambda *_: self._close_and(self._start_plaid_link),
        )
        scotiabank_btn = MDFlatButton(
            text="Scotiabank",
            size_hint_x=None,
            width=dp(100),
            on_release=lambda *_: self._close_and(self._show_scotiabank_login),
        )
        self._dialog = MDDialog(
            title="Connect Bank Account",
            text="Use Plaid for real banks.\nScotiabank uses mock data.",
            buttons=[scotiabank_btn, plaid_btn],
        )
        self._dialog.open()

    def _close_and(self, fn):
        if self._dialog:
            self._dialog.dismiss()
        Clock.schedule_once(lambda *_: fn(), 0.3)

    # ---------------------------------------------------------------- scotiabank login
    def _show_scotiabank_login(self):
        username_field = MDTextField(hint_text="Username / Card Number", mode="rectangle")
        password_field = MDTextField(hint_text="Password", mode="rectangle", password=True)
        box = MDBoxLayout(
            orientation="vertical", spacing=dp(12),
            size_hint_y=None, height=dp(130),
        )
        box.add_widget(username_field)
        box.add_widget(password_field)

        def _do_login(*_):
            self._dialog.dismiss()
            self._mock_oauth_connect(
                bank_name="Scotiabank",
                username=username_field.text,
                password=password_field.text,
            )

        self._dialog = MDDialog(
            title="Sign in to Scotiabank",
            type="custom",
            content_cls=box,
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    size_hint_x=None,
                    width=dp(100),
                    on_release=lambda *_: self._dialog.dismiss(),
                ),
                MDRaisedButton(
                    text="CONNECT",
                    size_hint_x=None,
                    width=dp(100),
                    on_release=_do_login,
                ),
            ],
        )
        self._dialog.open()

    # ---------------------------------------------------------------- plaid link
    def _get_plaid_credentials(self) -> dict | None:
        """Load Plaid credentials from JsonStore. Returns None if not configured."""
        from kivy.storage.jsonstore import JsonStore
        import os
        from kivy.utils import platform as kp
        if kp == "android":
            try:
                from android.storage import app_storage_path
                base = app_storage_path()
            except Exception:
                base = os.path.expanduser("~")
        else:
            base = os.path.join(os.path.expanduser("~"), ".clearspend")
        os.makedirs(base, exist_ok=True)
        store = JsonStore(os.path.join(base, "settings.json"))
        if store.exists("plaid"):
            data = store.get("plaid")
            cid = data.get("client_id", "")
            sec = data.get("secret", "")
            if cid and sec:
                return {
                    "client_id": cid,
                    "secret": sec,
                    "environment": data.get("environment", "sandbox"),
                }
        return None

    def _start_plaid_link(self):
        """Create a Link token then open Plaid Link in an in-app WebView (Android)
        or browser (desktop)."""
        creds = self._get_plaid_credentials()
        if not creds:
            Snackbar(text="Configure Plaid credentials in Settings first.").open()
            return

        Snackbar(text="Preparing bank login...").open()

        import threading

        def _bg():
            self._plaid_log("background thread started")
            try:
                from utils.bank_api import PlaidAPI
                api = PlaidAPI(**creds)
                self._plaid_log("calling create_link_token")
                resp = api.create_link_token()
                link_token = resp.get("link_token", "")
                self._plaid_log(f"link_token received, length={len(link_token)}")
                if not link_token:
                    Clock.schedule_once(
                        lambda *_: Snackbar(text="Plaid error: empty link_token.").open(), 0
                    )
                    return
                url = api.get_link_url(link_token)
                self._plaid_log(f"launching UI with url length={len(url)}")
                Clock.schedule_once(lambda *_, u=url: self._launch_plaid_ui(u), 0)
            except Exception as e:
                import traceback
                msg = traceback.format_exc()
                self._plaid_log(f"_bg EXCEPTION: {msg}")
                err = str(e)
                Clock.schedule_once(
                    lambda *_, m=err: self._show_error_dialog("Plaid Link Failed", m), 0
                )

        threading.Thread(target=_bg, daemon=True).start()

    def _launch_plaid_ui(self, url: str):
        """Main-thread: open in-app WebView on Android, browser on desktop."""
        from kivy.utils import platform as kp
        if kp == "android":
            self._open_plaid_webview(url)
        else:
            import webbrowser
            webbrowser.open(url)
            Snackbar(text="Complete bank login in the browser.").open()

    def _open_plaid_webview(self, url: str):
        """Android: reset static state then start PlaidWebViewActivity.

        Result is picked up in on_resume via check_plaid_webview_result()
        because singleTask launchMode breaks startActivityForResult.
        """
        self._plaid_log(f"_open_plaid_webview called, url length={len(url)}")
        try:
            from jnius import autoclass
            self._plaid_log("jnius imported")

            Intent = autoclass("android.content.Intent")
            self._plaid_log("Intent loaded")

            PlaidWebViewActivity = autoclass(
                "com.clearspend.clearspend.PlaidWebViewActivity"
            )
            self._plaid_log("PlaidWebViewActivity class loaded")

            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            activity = PythonActivity.mActivity
            self._plaid_log(f"PythonActivity loaded: {activity}")

            PlaidWebViewActivity.completed = False
            PlaidWebViewActivity.lastPublicToken = None
            self._plaid_log("static fields reset")

            intent = Intent(activity, PlaidWebViewActivity)
            intent.putExtra("plaid_url", url)
            self._plaid_log("intent created, calling startActivity")

            activity.startActivity(intent)
            self._plaid_log("startActivity called successfully")

        except Exception as e:
            import traceback
            msg = traceback.format_exc()
            self._plaid_log(f"EXCEPTION: {msg}")
            self._show_error_dialog("Plaid WebView Error", str(e))

    @staticmethod
    def _plaid_log(msg: str):
        """Write a timestamped line to plaid_debug.txt for on-device diagnosis."""
        try:
            import os, time
            from kivy.utils import platform as kp
            if kp == "android":
                try:
                    from android.storage import app_storage_path
                    base = app_storage_path()
                except Exception:
                    base = os.path.expanduser("~")
            else:
                base = os.path.join(os.path.expanduser("~"), ".clearspend")
            os.makedirs(base, exist_ok=True)
            path = os.path.join(base, "plaid_debug.txt")
            with open(path, "a") as f:
                f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
        except Exception:
            pass

    def check_plaid_webview_result(self):
        """Called from app on_resume. Picks up result left by PlaidWebViewActivity."""
        try:
            from jnius import autoclass
            PlaidWebViewActivity = autoclass(
                "com.clearspend.clearspend.PlaidWebViewActivity"
            )
            if not PlaidWebViewActivity.completed:
                return
            token = PlaidWebViewActivity.lastPublicToken
            # Reset so we don't process it twice
            PlaidWebViewActivity.completed = False
            PlaidWebViewActivity.lastPublicToken = None

            if token:
                self._handle_plaid_callback(token)
            else:
                Snackbar(text="Bank login cancelled.").open()
        except Exception:
            pass

    def _show_error_dialog(self, title: str, message: str):
        """Show a scrollable error dialog (main thread only)."""
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton
        d = MDDialog(
            title=title,
            text=message,
            buttons=[MDFlatButton(text="OK", on_release=lambda *_: d.dismiss())],
        )
        d.open()

    def _handle_plaid_callback(self, public_token: str):
        """Called when the app receives a Plaid redirect with a public_token."""
        creds = self._get_plaid_credentials()
        if not creds:
            Snackbar(text="Plaid credentials missing.").open()
            return

        Snackbar(text="Connecting bank account...").open()

        import threading

        def _bg():
            try:
                from utils.bank_api import PlaidAPI
                from models.database import Database
                api = PlaidAPI(**creds)
                result = api.connect(public_token=public_token)

                if result.get("success"):
                    db = Database.get()
                    access_token = result.get("access_token", "")
                    item_id = result.get("item_id", "")
                    for acc in result.get("accounts", []):
                        db.add_bank_account(
                            bank_name="Plaid",
                            account_name=acc.get("name", "Account"),
                            account_number_masked=acc.get("number", "****"),
                            access_token=access_token,
                            item_id=item_id,
                            environment=creds.get("environment", "sandbox"),
                        )

                    def _done(*_):
                        Snackbar(text="Bank connected via Plaid!").open()
                        self.refresh()

                    Clock.schedule_once(_done, 0)
                else:
                    err = result.get("error", "")
                    Clock.schedule_once(
                        lambda *_, e=err: Snackbar(text=f"Connection failed: {e}").open(), 0
                    )
            except Exception as e:
                err = str(e)
                Clock.schedule_once(
                    lambda *_, m=err: Snackbar(text=f"Plaid error: {m}").open(), 0
                )

        threading.Thread(target=_bg, daemon=True).start()

    def sandbox_test_connect(self):
        """Sandbox shortcut: skip browser, create test token directly."""
        creds = self._get_plaid_credentials()
        if not creds:
            Snackbar(text="Configure Plaid credentials in Settings first.").open()
            return
        if creds.get("environment") != "sandbox":
            Snackbar(text="Sandbox test only works in sandbox environment.").open()
            return

        Snackbar(text="Creating sandbox connection...").open()

        import threading

        def _bg():
            try:
                from utils.bank_api import PlaidAPI
                api = PlaidAPI(**creds)
                public_token = api.create_sandbox_token()
                if public_token:
                    Clock.schedule_once(
                        lambda *_: self._handle_plaid_callback(public_token), 0
                    )
                else:
                    Clock.schedule_once(
                        lambda *_: Snackbar(text="Failed to create sandbox token.").open(), 0
                    )
            except Exception as e:
                err = str(e)
                Clock.schedule_once(
                    lambda *_, m=err: Snackbar(text=f"Sandbox error: {m}").open(), 0
                )

        threading.Thread(target=_bg, daemon=True).start()

    # ---------------------------------------------------------------- mock OAuth
    def _mock_oauth_connect(self, bank_name: str, username: str, password: str):
        from utils.bank_api import get_bank_api
        from models.database import Database

        Snackbar(text=f"Connecting to {bank_name}...").open()

        def _do(*_):
            api = get_bank_api(bank_name)
            result = api.connect(username=username, password=password)
            if result.get("success"):
                db = Database.get()
                for acc in result.get("accounts", []):
                    db.add_bank_account(
                        bank_name=bank_name,
                        account_name=acc.get("name", "Account"),
                        account_number_masked=acc.get("number", "****"),
                        access_token="mock_token",
                    )
                Snackbar(text=f"{bank_name} connected!").open()
                self.refresh()
            else:
                Snackbar(text="Connection failed.").open()

        Clock.schedule_once(_do, 0.5)

    # ---------------------------------------------------------------- sync
    def sync_account(self, account_id: int):
        from models.database import Database

        db = Database.get()
        accounts = db.get_bank_accounts()
        acc = next((a for a in accounts if a["id"] == account_id), None)
        if not acc:
            return

        Snackbar(text="Fetching transactions...").open()

        if acc.get("bank_name") == "Plaid":
            Clock.schedule_once(lambda *_: self._sync_plaid(acc, account_id), 0.3)
        else:
            Clock.schedule_once(lambda *_: self._sync_mock(acc, account_id), 0.5)

    def _sync_plaid(self, acc: dict, account_id: int):
        """Sync transactions for a Plaid-connected account using /transactions/sync."""
        try:
            from utils.bank_api import PlaidAPI
            from models.database import Database

            creds = self._get_plaid_credentials()
            if not creds:
                Snackbar(text="Plaid credentials missing. Check Settings.").open()
                return

            db = Database.get()
            api = PlaidAPI(**creds)
            cursor = db.get_plaid_cursor(account_id)
            access_token = acc.get("access_token", "")

            result = api.get_transactions(
                access_token=access_token,
                cursor=cursor,
            )

            added = 0
            for t in result.get("added", []):
                ptid = t.get("plaid_transaction_id", "")
                if ptid:
                    existing = db.conn.execute(
                        "SELECT id FROM transactions WHERE plaid_transaction_id = ?",
                        (ptid,),
                    ).fetchone()
                    if existing:
                        continue

                db.add_transaction(
                    amount=t["amount"],
                    type_=t["type"],
                    category=t.get("category", "Other"),
                    description=t.get("description", ""),
                    trans_date=t["date"],
                    source="plaid",
                    bank_account_id=account_id,
                    plaid_transaction_id=t.get("plaid_transaction_id", ""),
                )
                added += 1

            removed_ids = result.get("removed", [])
            if removed_ids:
                db.delete_transactions_by_plaid_id(removed_ids)

            new_cursor = result.get("cursor", cursor)
            if new_cursor:
                db.set_plaid_cursor(account_id, new_cursor)

            db.update_bank_sync_time(account_id)
            self.refresh()

            app = self._get_app()
            if app:
                app.refresh_dashboard()

            removed_count = len(removed_ids)
            msg = f"Synced {added} new"
            if removed_count:
                msg += f", {removed_count} removed"
            Snackbar(text=msg + ".").open()

        except Exception as e:
            Snackbar(text=f"Sync error: {e}").open()

    def _sync_mock(self, acc: dict, account_id: int):
        """Sync transactions for a mock (Scotiabank) account."""
        from utils.bank_api import get_bank_api
        from models.database import Database

        db = Database.get()
        api = get_bank_api(acc["bank_name"])
        api.connect()
        txns = api.get_transactions(from_date=acc.get("last_sync", "")[:10])
        added = 0
        for t in txns:
            existing = db.get_transactions(year_month=t["date"][:7])
            dup = any(
                e.get("description") == t["description"]
                and e.get("date") == t["date"]
                and abs(e.get("amount", 0) - t["amount"]) < 0.01
                for e in existing
            )
            if not dup:
                db.add_transaction(
                    amount=t["amount"],
                    type_=t["type"],
                    category=t.get("category", "Other"),
                    description=t.get("description", ""),
                    trans_date=t["date"],
                    source=t.get("source", acc["bank_name"].lower()),
                    bank_account_id=account_id,
                )
                added += 1

        db.update_bank_sync_time(account_id)
        self.refresh()

        app = self._get_app()
        if app:
            app.refresh_dashboard()

        Snackbar(text=f"Synced {added} new transaction(s).").open()

    @staticmethod
    def _get_app():
        from kivy.app import App
        return App.get_running_app()
