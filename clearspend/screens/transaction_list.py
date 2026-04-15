"""Transaction list tab - scrollable history with month/type filter."""
from __future__ import annotations
from datetime import date, datetime

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.snackbar import Snackbar

KV = """
<TransactionListTab>:
    orientation: 'vertical'
    md_bg_color: app.theme_cls.bg_normal

    MDTopAppBar:
        title: "Transaction History"
        elevation: 2

    # ── Filter bar ────────────────────────────────────────────────────
    MDBoxLayout:
        size_hint_y: None
        height: self.minimum_height
        padding: [dp(12), dp(6)]
        spacing: dp(8)
        md_bg_color: app.theme_cls.bg_dark

        MDRaisedButton:
            id: month_btn
            text: root.filter_month_label
            size_hint_x: 0.45
            height: dp(36)
            size_hint_y: None
            font_size: "12sp"
            on_release: root.open_month_menu(self)
            md_bg_color: app.theme_cls.primary_dark

        MDRaisedButton:
            id: type_btn
            text: root.filter_type_label
            size_hint_x: 0.3
            height: dp(36)
            size_hint_y: None
            font_size: "12sp"
            on_release: root.cycle_type_filter()
            md_bg_color:
                [0.2, 0.65, 0.35, 1] if root.filter_type == 'income' else \
                ([0.75, 0.25, 0.2, 1] if root.filter_type == 'expense' else \
                app.theme_cls.primary_dark)

        MDLabel:
            id: count_label
            text: "0 items"
            font_style: "Caption"
            theme_text_color: "Secondary"
            halign: "right"
            adaptive_height: True

    # ── List ──────────────────────────────────────────────────────────
    ScrollView:
        do_scroll_x: False

        MDBoxLayout:
            id: txn_list
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            padding: [dp(12), dp(8), dp(12), dp(12)]
            spacing: dp(6)
"""

Builder.load_string(KV)


class TransactionListTab(MDBoxLayout):
    filter_month_label = StringProperty("")
    filter_type_label  = StringProperty("All")
    filter_type        = StringProperty("all")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        now = datetime.now()
        self._year  = now.year
        self._month = now.month
        self._update_month_label()
        Clock.schedule_once(self.refresh, 0.5)

    # ----------------------------------------------------------------
    def _ym(self) -> str:
        return f"{self._year:04d}-{self._month:02d}"

    def _update_month_label(self):
        self.filter_month_label = date(self._year, self._month, 1).strftime("%b %Y")

    def refresh(self, *_):
        from models.database import Database
        type_ = None if self.filter_type == "all" else self.filter_type
        txns = Database.get().get_transactions(year_month=self._ym(), type_=type_, limit=200)

        self.ids.count_label.text = f"{len(txns)} items"
        self.ids.txn_list.clear_widgets()

        if not txns:
            self.ids.txn_list.add_widget(MDLabel(
                text="No transactions found.",
                halign="center",
                theme_text_color="Secondary",
                adaptive_height=True,
                padding=[0, dp(30)],
            ))
            return

        for t in txns:
            self.ids.txn_list.add_widget(self._make_row(t))

    def _make_row(self, t: dict) -> MDCard:
        from kivymd.uix.button import MDIconButton
        card = MDCard(
            orientation="horizontal",
            padding=[dp(8), dp(8)],
            size_hint_y=None,
            height=dp(66),
            radius=[dp(10)],
            ripple_behavior=False,
        )
        left = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(2), size_hint_x=1)
        desc = (t.get("description") or t.get("category") or "-")[:32]
        left.add_widget(MDLabel(text=desc, font_style="Body1", adaptive_height=True))
        source_tag = f"  [{t.get('source','')}]" if t.get("source") != "manual" else ""
        left.add_widget(MDLabel(
            text=f"{t.get('category','')[:22]}{source_tag} | {t.get('date','')}",
            font_style="Caption", theme_text_color="Secondary", adaptive_height=True,
        ))

        sign  = "+" if t["type"] == "income" else "-"
        color = (0.4, 1, 0.55, 1) if t["type"] == "income" else (1, 0.45, 0.45, 1)
        amt = MDLabel(
            text=f"{sign}${t['amount']:,.2f}",
            halign="right",
            theme_text_color="Custom",
            text_color=color,
            font_style="Subtitle1",
            size_hint_x=0.38,
            size_hint_y=None,
            height=dp(66),
        )

        txn_id = t["id"]
        edit_btn = MDIconButton(
            icon="pencil-outline",
            size_hint=(None, None),
            size=(dp(36), dp(36)),
            pos_hint={"center_y": 0.5},
            theme_text_color="Custom",
            text_color=(0.5, 0.8, 1, 1),
        )
        edit_btn.bind(on_release=lambda *_, tid=txn_id: self._on_edit(tid))

        del_btn = MDIconButton(
            icon="delete-outline",
            size_hint=(None, None),
            size=(dp(36), dp(36)),
            pos_hint={"center_y": 0.5},
            theme_text_color="Custom",
            text_color=(1, 0.45, 0.45, 1),
        )
        del_btn.bind(on_release=lambda *_, tid=txn_id: self._on_delete(tid))

        card.add_widget(left)
        card.add_widget(amt)
        card.add_widget(edit_btn)
        card.add_widget(del_btn)
        return card

    # ---------------------------------------------------------------- edit / delete
    def _on_edit(self, txn_id: int):
        from kivy.app import App
        App.get_running_app().go_to_edit(txn_id)

    def _on_delete(self, txn_id: int):
        self._pending_delete_id = txn_id
        self._delete_dialog = MDDialog(
            title="Delete this transaction?",
            text="This action cannot be undone.",
            buttons=[
                MDFlatButton(
                    text="CANCEL",
                    on_release=lambda *_: self._delete_dialog.dismiss(),
                ),
                MDRaisedButton(
                    text="DELETE",
                    md_bg_color=(0.85, 0.2, 0.2, 1),
                    on_release=self._confirm_delete,
                ),
            ],
        )
        self._delete_dialog.open()

    def _confirm_delete(self, *_):
        self._delete_dialog.dismiss()
        from models.database import Database
        Database.get().delete_transaction(self._pending_delete_id)
        self.refresh()
        Snackbar(text="Transaction deleted").open()

    # ---------------------------------------------------------------- filters
    def cycle_type_filter(self):
        cycle = {"all": "expense", "expense": "income", "income": "all"}
        labels = {"all": "All", "expense": "Expense", "income": "Income"}
        self.filter_type = cycle[self.filter_type]
        self.filter_type_label = labels[self.filter_type]
        self.refresh()

    def open_month_menu(self, caller):
        now = datetime.now()
        items = []
        for delta in range(12):
            m = now.month - delta
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            label = date(y, m, 1).strftime("%B %Y")
            ym = f"{y:04d}-{m:02d}"
            items.append({
                "text": label,
                "viewclass": "OneLineListItem",
                "on_release": lambda _y=y, _m=m, _l=label: self._pick_month(_y, _m, _l),
            })

        menu = MDDropdownMenu(caller=caller, items=items, width_mult=3, max_height=dp(320))
        menu.open()

    def _pick_month(self, year: int, month: int, label: str):
        self._year  = year
        self._month = month
        self.filter_month_label = label
        self.refresh()
