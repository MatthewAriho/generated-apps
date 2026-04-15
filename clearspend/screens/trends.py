"""Trends screen - category breakdown + recurring transaction detection.

V1 feature: populated in V1 milestone.
"""
from __future__ import annotations
from datetime import datetime, date

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.boxlayout import MDBoxLayout

KV = """
<TrendsScreen>:
    name: 'trends'

    MDBoxLayout:
        orientation: 'vertical'
        md_bg_color: app.theme_cls.bg_normal

        MDTopAppBar:
            title: "Spending Trends"
            elevation: 2
            left_action_items: [["arrow-left", lambda x: app.go_back()]]

        ScrollView:
            do_scroll_x: False

            MDBoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: [dp(12), dp(10)]
                spacing: dp(10)

                # Month label
                MDLabel:
                    id: period_label
                    text: root.period_label
                    font_style: 'H6'
                    halign: 'center'
                    adaptive_height: True

                # Donut chart
                MDCard:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: dp(220)
                    radius: [dp(12)]
                    padding: [dp(8), dp(8)]

                    MDLabel:
                        text: "Category Breakdown"
                        font_style: "Caption"
                        theme_text_color: "Secondary"
                        adaptive_height: True
                        padding: [dp(8), 0]

                    BoxLayout:
                        id: donut_chart
                        size_hint_y: None
                        height: dp(190)

                # Category breakdown
                MDLabel:
                    text: "SPENDING BY CATEGORY"
                    font_style: "Overline"
                    theme_text_color: "Secondary"
                    adaptive_height: True
                    padding: [dp(4), dp(8), 0, dp(2)]

                MDBoxLayout:
                    id: categories_box
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(8)

                # Recurring
                MDLabel:
                    text: "RECURRING TRANSACTIONS"
                    font_style: "Overline"
                    theme_text_color: "Secondary"
                    adaptive_height: True
                    padding: [dp(4), dp(16), 0, dp(2)]

                MDBoxLayout:
                    id: recurring_box
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(6)
"""

Builder.load_string(KV)


class TrendsScreen(Screen):
    period_label = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        now = datetime.now()
        self.period_label = date(now.year, now.month, 1).strftime("%B %Y")

    def on_enter(self):
        Clock.schedule_once(self.refresh, 0.1)

    def refresh(self, *_):
        from models.database import Database
        db = Database.get()
        ym = datetime.now().strftime("%Y-%m")

        # --- Donut chart ---
        breakdown = db.get_category_breakdown(ym)
        self._update_donut(breakdown)

        # --- Category breakdown bars ---
        self.ids.categories_box.clear_widgets()

        max_amt = max((r["total"] for r in breakdown), default=1)
        for row in breakdown:
            pct = row["total"] / max_amt if max_amt > 0 else 0
            card = self._make_bar_card(row["category"], row["total"], pct)
            self.ids.categories_box.add_widget(card)

        if not breakdown:
            self.ids.categories_box.add_widget(MDLabel(
                text="No expense data for this month.",
                halign="center", theme_text_color="Secondary", adaptive_height=True,
            ))

        # --- Recurring ---
        recurring = db.get_recurring_transactions()
        self.ids.recurring_box.clear_widgets()

        for r in recurring:
            card = MDCard(
                orientation="horizontal",
                padding=[dp(14), dp(10)],
                size_hint_y=None,
                height=dp(60),
                radius=[dp(10)],
            )
            left = MDBoxLayout(orientation="vertical", adaptive_height=True)
            left.add_widget(MDLabel(
                text=r["description"][:30], font_style="Body1", adaptive_height=True,
            ))
            left.add_widget(MDLabel(
                text=f"Seen {r['month_count']} months | {r['category']}",
                font_style="Caption", theme_text_color="Secondary", adaptive_height=True,
            ))
            card.add_widget(left)
            card.add_widget(MDLabel(
                text=f"~${r['avg_amount']:,.2f}/mo",
                halign="right", font_style="Subtitle2",
                theme_text_color="Secondary",
            ))
            self.ids.recurring_box.add_widget(card)

        if not recurring:
            self.ids.recurring_box.add_widget(MDLabel(
                text="No recurring transactions detected yet.\nAdd a few months of data to see patterns.",
                halign="center", theme_text_color="Secondary", adaptive_height=True,
            ))

    def _update_donut(self, breakdown: list[dict]):
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

    @staticmethod
    def _make_bar_card(category: str, amount: float, pct: float) -> MDCard:
        card = MDCard(
            orientation="vertical",
            padding=[dp(12), dp(10)],
            size_hint_y=None,
            height=dp(72),
            radius=[dp(10)],
        )
        row = MDBoxLayout(adaptive_height=True)
        row.add_widget(MDLabel(text=category[:24], font_style="Body2", adaptive_height=True))
        row.add_widget(MDLabel(
            text=f"${amount:,.2f}", halign="right",
            font_style="Body2", theme_text_color="Primary", adaptive_height=True,
        ))
        card.add_widget(row)
        bar = MDProgressBar(value=pct * 100, size_hint_y=None, height=dp(6))
        card.add_widget(bar)
        return card
