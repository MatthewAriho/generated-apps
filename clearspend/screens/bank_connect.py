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
        right_action_items: [["plus", lambda x: root.show_bank_selector(), "Add bank"]]

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
        scotiabank_btn = MDRaisedButton(
            text="Scotiabank",
            on_release=lambda *_: self._close_and(self._show_scotiabank_login),
        )
        other_btn = MDFlatButton(
            text="Other Bank",
            on_release=lambda *_: self._close_and(self._show_generic_login),
        )
        cancel_btn = MDFlatButton(
            text="Cancel",
            on_release=lambda *_: self._dialog.dismiss() if self._dialog else None,
        )
        self._dialog = MDDialog(
            title="Connect Bank Account",
            text="Choose your financial institution:",
            buttons=[cancel_btn, other_btn, scotiabank_btn],
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
                MDFlatButton(text="CANCEL",
                             on_release=lambda *_: self._dialog.dismiss()),
                MDRaisedButton(text="CONNECT", on_release=_do_login),
            ],
        )
        self._dialog.open()

    # ---------------------------------------------------------------- generic login
    def _show_generic_login(self):
        info = MDLabel(
            text="Generic bank integration uses Flinks/Plaid API.\n"
                 "Enter your Flinks API key in Settings to enable this feature.",
            theme_text_color="Secondary",
            adaptive_height=True,
        )
        self._dialog = MDDialog(
            title="Other Bank",
            type="custom",
            content_cls=info,
            buttons=[MDFlatButton(text="OK",
                                  on_release=lambda *_: self._dialog.dismiss())],
        )
        self._dialog.open()

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
        from utils.bank_api import get_bank_api
        from models.database import Database

        db = Database.get()
        accounts = db.get_bank_accounts()
        acc = next((a for a in accounts if a["id"] == account_id), None)
        if not acc:
            return

        Snackbar(text="Fetching transactions...").open()

        def _do(*_):
            api = get_bank_api(acc["bank_name"])
            api.connect()  # re-auth mock
            txns = api.get_transactions(from_date=acc.get("last_sync", "")[:10])
            added = 0
            for t in txns:
                existing = db.get_transactions(
                    year_month=t["date"][:7],
                )
                # Basic dedup: skip if description+date+amount already exists
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

        Clock.schedule_once(_do, 0.5)

    @staticmethod
    def _get_app():
        from kivy.app import App
        return App.get_running_app()
