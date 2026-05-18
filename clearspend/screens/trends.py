"""Trends screen + tab - category breakdown + recurring transaction detection."""
from __future__ import annotations
from datetime import datetime, date

import threading

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, BooleanProperty, ListProperty, NumericProperty
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.screenmanager import Screen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.boxlayout import MDBoxLayout

KV = """
<CategoryBarRow>:
    orientation: 'vertical'
    size_hint_y: None
    height: dp(68)
    padding: [dp(12), dp(8)]
    md_bg_color: app.theme_cls.bg_dark
    radius: [dp(10)]

    MDBoxLayout:
        adaptive_height: True
        MDLabel:
            text: root.category
            font_style: "Body2"
            adaptive_height: True
            shorten: True
            shorten_from: "right"
        MDLabel:
            text: root.amount_str
            halign: "right"
            font_style: "Body2"
            theme_text_color: "Primary"
            adaptive_height: True
            size_hint_x: None
            width: dp(80)
    MDProgressBar:
        value: root.bar_pct
        size_hint_y: None
        height: dp(6)

<RecurringRow>:
    orientation: 'horizontal'
    size_hint_y: None
    height: dp(64)
    padding: [dp(14), dp(10)]
    md_bg_color: app.theme_cls.bg_dark
    radius: [dp(10)]

    MDBoxLayout:
        orientation: 'vertical'
        adaptive_height: True
        size_hint_x: 1
        MDLabel:
            text: root.desc
            font_style: "Body1"
            adaptive_height: True
            shorten: True
            shorten_from: "right"
        MDLabel:
            text: root.meta
            font_style: "Caption"
            theme_text_color: "Secondary"
            adaptive_height: True
            shorten: True
            shorten_from: "right"
    MDLabel:
        text: root.avg_amt
        halign: "right"
        font_style: "Subtitle2"
        theme_text_color: "Secondary"
        size_hint_x: None
        width: dp(100)

<TrendsContent>:
    orientation: 'vertical'
    md_bg_color: app.theme_cls.bg_normal

    MDTopAppBar:
        id: top_bar
        title: "Spending Trends"
        elevation: 2
        left_action_items: root.back_items

    MDBoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: dp(36)
        padding: [dp(12), dp(6)]
        MDLabel:
            id: period_label
            text: root.period_label
            font_style: 'H6'
            halign: 'center'
            adaptive_height: True

    MDCard:
        orientation: 'vertical'
        size_hint_y: None
        height: dp(224)
        radius: [dp(12)]
        padding: [dp(12), dp(10), dp(12), dp(12)]
        margin: [dp(12), 0]

        MDLabel:
            text: "Category Breakdown"
            font_style: "Caption"
            theme_text_color: "Secondary"
            size_hint_y: None
            height: dp(20)

        BoxLayout:
            id: donut_chart
            size_hint_y: None
            height: dp(190)

    RecycleView:
        id: rv_cats
        viewclass: "CategoryBarRow"
        size_hint_y: 0.42
        scroll_type: ['bars', 'content']
        bar_width: dp(3)
        RecycleBoxLayout:
            default_size: None, dp(76)
            default_size_hint: 1, None
            size_hint_y: None
            height: self.minimum_height
            orientation: 'vertical'
            spacing: dp(6)
            padding: [dp(12), dp(6), dp(12), dp(4)]

    MDLabel:
        text: "RECURRING TRANSACTIONS"
        font_style: "Overline"
        theme_text_color: "Secondary"
        size_hint_y: None
        height: dp(28)
        padding: [dp(16), 0]

    RecycleView:
        id: rv_recurring
        viewclass: "RecurringRow"
        size_hint_y: 0.32
        scroll_type: ['bars', 'content']
        bar_width: dp(3)
        RecycleBoxLayout:
            default_size: None, dp(72)
            default_size_hint: 1, None
            size_hint_y: None
            height: self.minimum_height
            orientation: 'vertical'
            spacing: dp(6)
            padding: [dp(12), dp(4), dp(12), dp(8)]

<TrendsScreen>:
    name: 'trends'
    TrendsContent:
        show_back: True
"""

Builder.load_string(KV)


def _get_app():
    from kivy.app import App
    return App.get_running_app()


class CategoryBarRow(RecycleDataViewBehavior, MDCard):
    category   = StringProperty("")
    amount_str = StringProperty("")
    bar_pct    = NumericProperty(0)

    def refresh_view_attrs(self, rv, index, data):
        self.category   = data.get("category", "")
        self.amount_str = data.get("amount_str", "")
        self.bar_pct    = data.get("bar_pct", 0)
        return super().refresh_view_attrs(rv, index, data)


class RecurringRow(RecycleDataViewBehavior, MDCard):
    desc    = StringProperty("")
    meta    = StringProperty("")
    avg_amt = StringProperty("")

    def refresh_view_attrs(self, rv, index, data):
        self.desc    = data.get("desc", "")
        self.meta    = data.get("meta", "")
        self.avg_amt = data.get("avg_amt", "")
        return super().refresh_view_attrs(rv, index, data)


class TrendsContent(MDBoxLayout):
    period_label = StringProperty("")
    show_back = BooleanProperty(False)
    back_items = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        now = datetime.now()
        self.period_label = date(now.year, now.month, 1).strftime("%B %Y")
        Clock.schedule_once(self.refresh, 0.4)

    def on_show_back(self, instance, value):
        self.back_items = [["arrow-left", lambda x: _get_app().go_back()]] if value else []

    def refresh(self, *_):
        def _fetch():
            try:
                from models.database import Database
                db = Database.get()
                ym = datetime.now().strftime("%Y-%m")
                breakdown = db.get_category_breakdown(ym)
                recurring = db.get_recurring_transactions()
                Clock.schedule_once(lambda *_: self._apply(breakdown, recurring), 0)
            except Exception:
                pass
        threading.Thread(target=_fetch, daemon=True).start()

    def _apply(self, breakdown, recurring):
        self._update_donut(breakdown)

        max_amt = max((r["total"] for r in breakdown), default=1)
        self.ids.rv_cats.data = [
            {
                "category":   r["category"],
                "amount_str": f"${r['total']:,.2f}",
                "bar_pct":    (r["total"] / max_amt * 100) if max_amt > 0 else 0,
            }
            for r in breakdown
        ]

        self.ids.rv_recurring.data = [
            {
                "desc":    (r.get("description") or "")[:40],
                "meta":    f"Seen {r['month_count']} months | {r['category'][:18]}",
                "avg_amt": f"~${r['avg_amount']:,.2f}/mo",
            }
            for r in recurring
        ]

    def _update_donut(self, breakdown):
        from utils.charts import DonutChart, CHART_COLORS
        container = self.ids.donut_chart
        container.clear_widgets()
        slices = []
        for i, row in enumerate(breakdown[:10]):
            color = CHART_COLORS[i % len(CHART_COLORS)]
            slices.append((row["category"], row["total"], color))
        chart = DonutChart(slices=slices)
        chart.size_hint = (1, 1)
        container.add_widget(chart)



class TrendsScreen(Screen):
    def on_enter(self):
        try:
            self.children[0].refresh()
        except Exception:
            pass


# Alias for use as bottom nav tab content (show_back=False by default)
TrendsTab = TrendsContent
