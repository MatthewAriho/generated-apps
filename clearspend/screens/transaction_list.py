"""Transaction list tab - scrollable history with search, filter, and sort."""
from __future__ import annotations
import threading
from datetime import date, datetime

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, ObjectProperty
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDIconButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.snackbar import Snackbar

KV = """
<TxnRow>:
    orientation: 'horizontal'
    padding: [dp(8), dp(4)]
    spacing: dp(4)
    size_hint_y: None
    height: dp(66)
    md_bg_color: app.theme_cls.bg_dark
    radius: [dp(10)]
    elevation: 0

    MDBoxLayout:
        orientation: 'vertical'
        adaptive_height: True
        size_hint_x: 1
        spacing: dp(2)

        MDLabel:
            id: desc_label
            text: root.desc
            font_style: "Body1"
            adaptive_height: True
            shorten: True
            shorten_from: "right"

        MDLabel:
            id: meta_label
            text: root.meta
            font_style: "Caption"
            theme_text_color: "Secondary"
            adaptive_height: True
            shorten: True
            shorten_from: "right"

    MDLabel:
        id: amt_label
        text: root.amt
        halign: "right"
        theme_text_color: "Custom"
        text_color: root.amt_color
        font_style: "Subtitle1"
        size_hint_x: None
        width: dp(90)
        size_hint_y: None
        height: dp(66)

    MDIconButton:
        icon: "pencil-outline"
        size_hint: None, None
        size: dp(36), dp(36)
        pos_hint: {"center_y": 0.5}
        theme_text_color: "Custom"
        text_color: 0.5, 0.8, 1, 1
        on_release: root.on_edit()

    MDIconButton:
        icon: "delete-outline"
        size_hint: None, None
        size: dp(36), dp(36)
        pos_hint: {"center_y": 0.5}
        theme_text_color: "Custom"
        text_color: 1, 0.45, 0.45, 1
        on_release: root.on_delete()

<TransactionListTab>:
    orientation: 'vertical'
    md_bg_color: app.theme_cls.bg_normal

    MDTopAppBar:
        title: "Transaction History"
        elevation: 2

    MDBoxLayout:
        size_hint_y: None
        height: dp(50)
        padding: [dp(12), dp(6)]
        md_bg_color: app.theme_cls.bg_dark

        MDTextField:
            id: search_field
            hint_text: "Search transactions..."
            mode: "rectangle"
            size_hint_y: None
            height: dp(40)
            icon_right: "magnify"
            on_text: root.on_search_text(self.text)

    MDBoxLayout:
        size_hint_y: None
        height: self.minimum_height
        padding: [dp(12), dp(6)]
        spacing: dp(8)
        md_bg_color: app.theme_cls.bg_dark

        MDRaisedButton:
            id: month_btn
            text: root.filter_month_label
            size_hint_x: 0.38
            height: dp(36)
            size_hint_y: None
            font_size: "12sp"
            on_release: root.open_month_menu(self)
            md_bg_color: app.theme_cls.primary_dark

        MDRaisedButton:
            id: type_btn
            text: root.filter_type_label
            size_hint_x: 0.25
            height: dp(36)
            size_hint_y: None
            font_size: "12sp"
            on_release: root.cycle_type_filter()
            md_bg_color:
                [0.2, 0.65, 0.35, 1] if root.filter_type == 'income' else \
                ([0.75, 0.25, 0.2, 1] if root.filter_type == 'expense' else \
                app.theme_cls.primary_dark)

        MDRaisedButton:
            id: sort_btn
            text: root.sort_label
            size_hint_x: 0.25
            height: dp(36)
            size_hint_y: None
            font_size: "12sp"
            on_release: root.open_sort_menu(self)
            md_bg_color: app.theme_cls.primary_dark

        MDLabel:
            id: count_label
            text: "0 items"
            font_style: "Caption"
            theme_text_color: "Secondary"
            halign: "right"
            adaptive_height: True

    RecycleView:
        id: rv
        viewclass: "TxnRow"
        scroll_type: ['bars', 'content']
        bar_width: dp(4)

        RecycleBoxLayout:
            default_size: None, dp(74)
            default_size_hint: 1, None
            size_hint_y: None
            height: self.minimum_height
            orientation: 'vertical'
            spacing: dp(6)
            padding: [dp(12), dp(8), dp(12), dp(12)]
"""

Builder.load_string(KV)

_SORT_OPTIONS = [
    ("Date (new)",  "date",        True),
    ("Date (old)",  "date",        False),
    ("Amt (high)",  "amount",      True),
    ("Amt (low)",   "amount",      False),
    ("Name (A-Z)",  "description", False),
    ("Name (Z-A)",  "description", True),
]


class TxnRow(RecycleDataViewBehavior, MDCard):
    """Single recycled transaction row."""
    desc      = StringProperty("")
    meta      = StringProperty("")
    amt       = StringProperty("")
    amt_color = ObjectProperty((1, 0.45, 0.45, 1))
    _txn_id   = 0
    _tab      = None   # set by TransactionListTab

    def refresh_view_attrs(self, rv, index, data):
        self.desc      = data.get("desc", "")
        self.meta      = data.get("meta", "")
        self.amt       = data.get("amt", "")
        self.amt_color = data.get("amt_color", (1, 0.45, 0.45, 1))
        self._txn_id   = data.get("txn_id", 0)
        self._tab      = data.get("tab")
        return super().refresh_view_attrs(rv, index, data)

    def on_edit(self):
        from kivy.app import App
        App.get_running_app().go_to_edit(self._txn_id)

    def on_delete(self):
        if self._tab:
            self._tab._on_delete(self._txn_id)


class TransactionListTab(MDBoxLayout):
    filter_month_label = StringProperty("")
    filter_type_label  = StringProperty("All")
    filter_type        = StringProperty("all")
    sort_label         = StringProperty("Date (new)")
    _search_text       = ""
    _sort_key          = "date"
    _sort_desc         = True
    _refresh_event     = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        now = datetime.now()
        self._year  = now.year
        self._month = now.month
        self._update_month_label()
        Clock.schedule_once(self.refresh, 0.5)

    def _ym(self):
        return f"{self._year:04d}-{self._month:02d}"

    def _update_month_label(self):
        self.filter_month_label = date(self._year, self._month, 1).strftime("%b %Y")

    def on_search_text(self, text: str):
        self._search_text = text.strip().lower()
        if self._refresh_event:
            self._refresh_event.cancel()
        self._refresh_event = Clock.schedule_once(lambda *_: self.refresh(), 0.35)

    def refresh(self, *_):
        self._refresh_event = None
        type_ = None if self.filter_type == "all" else self.filter_type
        ym    = self._ym()
        search  = self._search_text
        key     = self._sort_key
        reverse = self._sort_desc

        def _fetch():
            try:
                from models.database import Database
                txns = Database.get().get_transactions(year_month=ym, type_=type_, limit=500)
                if search:
                    txns = [
                        t for t in txns
                        if search in (t.get("description") or "").lower()
                        or search in (t.get("category") or "").lower()
                    ]
                try:
                    txns = sorted(txns, key=lambda t: (t.get(key) or ""), reverse=reverse)
                except Exception:
                    pass
                Clock.schedule_once(lambda *_: self._apply(txns), 0)
            except Exception:
                pass

        threading.Thread(target=_fetch, daemon=True).start()

    def _apply(self, txns):
        self.ids.count_label.text = f"{len(txns)} items"
        data = []
        for t in txns:
            sign      = "+" if t["type"] == "income" else "-"
            color     = (0.4, 1, 0.55, 1) if t["type"] == "income" else (1, 0.45, 0.45, 1)
            source_tag = f" [{t.get('source','')}]" if t.get("source") != "manual" else ""
            data.append({
                "desc":      (t.get("description") or t.get("category") or "-")[:40],
                "meta":      f"{t.get('category','')[:22]}{source_tag} | {t.get('date','')}",
                "amt":       f"{sign}${t['amount']:,.2f}",
                "amt_color": color,
                "txn_id":    t["id"],
                "tab":       self,
            })
        self.ids.rv.data = data

    # ---------------------------------------------------------------- edit / delete
    def _on_delete(self, txn_id: int):
        self._pending_delete_id = txn_id
        self._delete_dialog = MDDialog(
            title="Delete this transaction?",
            text="This action cannot be undone.",
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda *_: self._delete_dialog.dismiss()),
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
        cycle  = {"all": "expense", "expense": "income", "income": "all"}
        labels = {"all": "All", "expense": "Expense", "income": "Income"}
        self.filter_type       = cycle[self.filter_type]
        self.filter_type_label = labels[self.filter_type]
        self.refresh()

    def open_month_menu(self, caller):
        now   = datetime.now()
        items = []
        for delta in range(12):
            m = now.month - delta
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            label = date(y, m, 1).strftime("%B %Y")
            items.append({
                "text": label,
                "viewclass": "OneLineListItem",
                "on_release": lambda _y=y, _m=m, _l=label: self._pick_month(_y, _m, _l),
            })
        MDDropdownMenu(caller=caller, items=items, width_mult=3, max_height=dp(320)).open()

    def _pick_month(self, year, month, label):
        self._year  = year
        self._month = month
        self.filter_month_label = label
        self.refresh()

    # ---------------------------------------------------------------- sort
    def open_sort_menu(self, caller):
        items = [
            {
                "text": label,
                "viewclass": "OneLineListItem",
                "on_release": lambda l=label, k=key, d=desc: self._pick_sort(l, k, d),
            }
            for label, key, desc in _SORT_OPTIONS
        ]
        MDDropdownMenu(caller=caller, items=items, width_mult=3, max_height=dp(280)).open()

    def _pick_sort(self, label, key, desc):
        self._sort_key  = key
        self._sort_desc = desc
        self.sort_label = label
        self.refresh()
