"""Events tab — track spending for trips, weddings, and other occasions."""
from __future__ import annotations
import threading
from datetime import date, datetime

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, NumericProperty, ObjectProperty
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDIconButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.textfield import MDTextField

KV = """
<EventCard>:
    orientation: 'vertical'
    size_hint_y: None
    height: dp(90)
    padding: [dp(14), dp(10)]
    radius: [dp(12)]
    md_bg_color: root.card_color
    ripple_behavior: True
    on_release: root.on_tap()

    MDBoxLayout:
        adaptive_height: True
        MDLabel:
            text: root.name
            font_style: "Subtitle1"
            adaptive_height: True
            bold: True
            shorten: True
            shorten_from: "right"
            size_hint_x: 1
        MDLabel:
            text: root.total_str
            halign: "right"
            font_style: "Subtitle1"
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 1
            adaptive_height: True
            size_hint_x: None
            width: dp(90)

    MDBoxLayout:
        adaptive_height: True
        MDLabel:
            text: root.dates
            font_style: "Caption"
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 0.75
            adaptive_height: True
        MDLabel:
            text: root.txn_count
            halign: "right"
            font_style: "Caption"
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 0.75
            adaptive_height: True

<EventsTab>:
    orientation: 'vertical'
    md_bg_color: app.theme_cls.bg_normal

    MDTopAppBar:
        title: "Events"
        elevation: 2
        right_action_items: [["plus", lambda x: root.new_event_dialog()]]

    MDBoxLayout:
        size_hint_y: None
        height: dp(44)
        padding: [dp(12), dp(6)]
        md_bg_color: app.theme_cls.bg_dark

        MDLabel:
            text: root.subtitle
            font_style: "Caption"
            theme_text_color: "Secondary"
            adaptive_height: True

    RecycleView:
        id: rv
        viewclass: "EventCard"
        scroll_type: ['bars', 'content']
        bar_width: dp(4)
        RecycleBoxLayout:
            default_size: None, dp(98)
            default_size_hint: 1, None
            size_hint_y: None
            height: self.minimum_height
            orientation: 'vertical'
            spacing: dp(8)
            padding: [dp(12), dp(8), dp(12), dp(80)]

<EventDetailTab>:
    orientation: 'vertical'
    md_bg_color: app.theme_cls.bg_normal

    MDTopAppBar:
        id: detail_bar
        title: root.event_name
        elevation: 2
        left_action_items: [["arrow-left", lambda x: root.go_back()]]
        right_action_items: [["delete-outline", lambda x: root.delete_event()]]

    MDBoxLayout:
        size_hint_y: None
        height: dp(60)
        padding: [dp(16), dp(10)]
        spacing: dp(16)
        md_bg_color: app.theme_cls.bg_dark

        MDLabel:
            id: summary_label
            text: root.summary_text
            font_style: "Body2"
            theme_text_color: "Secondary"
            adaptive_height: True

    MDBoxLayout:
        size_hint_y: None
        height: dp(44)
        padding: [dp(12), dp(6)]
        spacing: dp(8)
        md_bg_color: app.theme_cls.bg_dark

        MDRaisedButton:
            text: "Add Transaction"
            size_hint_x: 1
            height: dp(32)
            size_hint_y: None
            font_size: "12sp"
            on_release: root.add_transaction_dialog()
            md_bg_color: app.theme_cls.primary_dark

        MDRaisedButton:
            text: "Auto-match"
            size_hint_x: None
            width: dp(110)
            height: dp(32)
            size_hint_y: None
            font_size: "12sp"
            on_release: root.auto_match()
            md_bg_color: app.theme_cls.accent_color

    RecycleView:
        id: rv_txns
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

# Import TxnRow from transaction_list so it's registered as a viewclass
from screens.transaction_list import TxnRow  # noqa: F401 — needed for RecycleView

_COLORS = [
    (0.18, 0.52, 0.90, 1),
    (0.18, 0.72, 0.42, 1),
    (0.90, 0.48, 0.10, 1),
    (0.80, 0.18, 0.48, 1),
    (0.50, 0.25, 0.85, 1),
    (0.08, 0.68, 0.68, 1),
]


class EventCard(RecycleDataViewBehavior, MDCard):
    name       = StringProperty("")
    total_str  = StringProperty("")
    dates      = StringProperty("")
    txn_count  = StringProperty("")
    card_color = ObjectProperty((0.18, 0.52, 0.90, 1))
    _event_id  = 0
    _tab       = None

    def refresh_view_attrs(self, rv, index, data):
        self.name       = data.get("name", "")
        self.total_str  = data.get("total_str", "")
        self.dates      = data.get("dates", "")
        self.txn_count  = data.get("txn_count", "")
        self.card_color = data.get("card_color", _COLORS[0])
        self._event_id  = data.get("event_id", 0)
        self._tab       = data.get("tab")
        return super().refresh_view_attrs(rv, index, data)

    def on_tap(self):
        if self._tab:
            self._tab.open_detail(self._event_id)


class EventsTab(MDBoxLayout):
    subtitle = StringProperty("Tap + to create a new event or trip")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Clock.schedule_once(self.refresh, 0.5)

    def refresh(self, *_):
        def _fetch():
            from models.database import Database
            db = Database.get()
            events = db.get_events()
            data = []
            for e in events:
                summary = db.get_event_summary(e["id"])
                color = _COLORS[e.get("color_index", 0) % len(_COLORS)]
                data.append({
                    "name":       e["name"],
                    "total_str":  f"${summary['total']:,.2f}",
                    "dates":      f"{e['start_date']} – {e['end_date']}",
                    "txn_count":  f"{summary['count']} transactions",
                    "card_color": color,
                    "event_id":   e["id"],
                    "tab":        self,
                })
            Clock.schedule_once(lambda *_: self._apply(data, len(events)), 0)
        threading.Thread(target=_fetch, daemon=True).start()

    def _apply(self, data, count):
        self.ids.rv.data = data
        if count == 0:
            self.subtitle = "Tap + to create a new event or trip"
        else:
            self.subtitle = f"{count} event{'s' if count != 1 else ''}"

    def open_detail(self, event_id: int):
        from kivy.app import App
        App.get_running_app().go_to_event(event_id)

    # ---------------------------------------------------------------- create dialog
    def new_event_dialog(self):
        self._name_field = MDTextField(hint_text="Event name (e.g. Tokyo Trip)",
                                       mode="rectangle", size_hint_y=None, height=dp(48))
        self._loc_field  = MDTextField(hint_text="Location keyword for auto-match (optional)",
                                       mode="rectangle", size_hint_y=None, height=dp(48))
        self._start_field = MDTextField(hint_text="Start date YYYY-MM-DD",
                                        mode="rectangle", size_hint_y=None, height=dp(48),
                                        text=date.today().isoformat())
        self._end_field  = MDTextField(hint_text="End date YYYY-MM-DD",
                                       mode="rectangle", size_hint_y=None, height=dp(48),
                                       text=date.today().isoformat())

        box = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(8),
                          padding=[0, dp(8)])
        for f in (self._name_field, self._start_field, self._end_field, self._loc_field):
            box.add_widget(f)

        # color picker row
        self._color_index = 0
        color_row = MDBoxLayout(size_hint_y=None, height=dp(36), spacing=dp(8))
        for i, c in enumerate(_COLORS):
            btn = MDRaisedButton(
                text="  ", md_bg_color=c,
                size_hint=(None, None), size=(dp(36), dp(28)),
            )
            idx = i
            btn.bind(on_release=lambda *_, ci=idx: setattr(self, '_color_index', ci))
            color_row.add_widget(btn)
        box.add_widget(color_row)

        self._create_dialog = MDDialog(
            title="New Event",
            type="custom",
            content_cls=box,
            buttons=[
                MDFlatButton(text="CANCEL",
                             on_release=lambda *_: self._create_dialog.dismiss()),
                MDRaisedButton(text="CREATE", on_release=self._do_create),
            ],
        )
        self._create_dialog.open()

    def _do_create(self, *_):
        name  = self._name_field.text.strip()
        start = self._start_field.text.strip()
        end   = self._end_field.text.strip()
        loc   = self._loc_field.text.strip()
        if not name or not start or not end:
            Snackbar(text="Name and dates are required.").open()
            return
        self._create_dialog.dismiss()
        from models.database import Database
        Database.get().create_event(name=name, description="",
                                    start_date=start, end_date=end,
                                    location_keyword=loc,
                                    color_index=self._color_index)
        self.refresh()
        Snackbar(text=f"Event '{name}' created.").open()


class EventDetailTab(MDBoxLayout):
    event_name   = StringProperty("")
    summary_text = StringProperty("")
    _event_id    = 0

    def load(self, event_id: int):
        self._event_id = event_id
        self.refresh()

    def refresh(self, *_):
        def _fetch():
            from models.database import Database
            db = Database.get()
            ev = db.get_event(self._event_id)
            if not ev:
                return
            txns   = db.get_event_transactions(self._event_id)
            summary = db.get_event_summary(self._event_id)
            Clock.schedule_once(lambda *_: self._apply(ev, txns, summary), 0)
        threading.Thread(target=_fetch, daemon=True).start()

    def _apply(self, ev, txns, summary):
        self.event_name   = ev["name"]
        self.summary_text = (
            f"${summary['total']:,.2f} spent  |  "
            f"{summary['count']} transactions  |  "
            f"{ev['start_date']} to {ev['end_date']}"
        )
        data = []
        for t in txns:
            sign  = "+" if t["type"] == "income" else "-"
            color = (0.4, 1, 0.55, 1) if t["type"] == "income" else (1, 0.45, 0.45, 1)
            source_tag = f" [{t.get('source','')}]" if t.get("source") != "manual" else ""
            data.append({
                "desc":      (t.get("description") or t.get("category") or "-")[:40],
                "meta":      f"{t.get('category','')[:22]}{source_tag} | {t.get('date','')}",
                "amt":       f"{sign}${t['amount']:,.2f}",
                "amt_color": color,
                "txn_id":    t["id"],
                "tab":       self,    # TxnRow expects a "tab" ref — won't call _on_delete here
            })
        self.ids.rv_txns.data = data

    def go_back(self):
        from kivy.app import App
        App.get_running_app().go_back()

    def delete_event(self):
        def _confirm(*_):
            dlg.dismiss()
            from models.database import Database
            Database.get().delete_event(self._event_id)
            self.go_back()

        dlg = MDDialog(
            title="Delete this event?",
            text="Transactions will not be deleted, only the event grouping.",
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda *_: dlg.dismiss()),
                MDRaisedButton(text="DELETE", md_bg_color=(0.85, 0.2, 0.2, 1),
                               on_release=_confirm),
            ],
        )
        dlg.open()

    def auto_match(self):
        """Re-run auto-matching for this event's location keyword."""
        def _do():
            from models.database import Database
            db = Database.get()
            ev = db.get_event(self._event_id)
            if not ev or not ev.get("location_keyword"):
                Clock.schedule_once(lambda *_: Snackbar(
                    text="No location keyword set for this event.").open(), 0)
                return
            db._auto_assign_event(self._event_id, ev["start_date"],
                                  ev["end_date"], ev["location_keyword"])
            Clock.schedule_once(lambda *_: (
                self.refresh(),
                Snackbar(text="Auto-match complete.").open(),
            ), 0)
        threading.Thread(target=_do, daemon=True).start()

    def add_transaction_dialog(self):
        """Show a picker of recent transactions to add to this event."""
        def _fetch():
            from models.database import Database
            db = Database.get()
            ev = db.get_event(self._event_id)
            if not ev:
                return
            txns = db.get_transactions(year_month=None, limit=60)
            already = {t["id"] for t in db.get_event_transactions(self._event_id)}
            candidates = [t for t in txns if t["id"] not in already][:30]
            Clock.schedule_once(lambda *_: self._show_add_dialog(candidates), 0)
        threading.Thread(target=_fetch, daemon=True).start()

    def _show_add_dialog(self, candidates):
        if not candidates:
            Snackbar(text="No transactions to add.").open()
            return

        items = []
        for t in candidates:
            label = f"{t.get('description','')[:28]} | ${t['amount']:,.2f} | {t['date']}"
            tid   = t["id"]
            items.append({
                "text": label,
                "viewclass": "OneLineListItem",
                "on_release": lambda t_id=tid: self._add_txn(t_id),
            })

        self._add_menu = MDDropdownMenu(
            caller=self.ids.rv_txns,
            items=items,
            width_mult=5,
            max_height=dp(320),
        )
        self._add_menu.open()

    def _add_txn(self, txn_id: int):
        if hasattr(self, "_add_menu"):
            self._add_menu.dismiss()
        from models.database import Database
        Database.get().add_transaction_to_event(self._event_id, txn_id)
        self.refresh()
        Snackbar(text="Transaction added to event.").open()
