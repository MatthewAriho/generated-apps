"""Dashboard tab - monthly summary card + recent transactions list + FAB."""
from __future__ import annotations
from datetime import date, datetime

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

KV = """
<DashboardTab>:
    orientation: 'vertical'
    md_bg_color: app.theme_cls.bg_normal

    MDTopAppBar:
        id: top_bar
        title: "ClearSpend"
        elevation: 2
        right_action_items:
            [ \
              ["cloud-sync-outline", lambda x: app.sync_cloud(), "Sync to cloud"], \
              ["wifi" if app.is_online else "wifi-off", lambda x: None, \
               "Online" if app.is_online else "Offline"] \
            ]

    FloatLayout:

        ScrollView:
            size_hint: (1, 1)
            pos_hint: {"x": 0, "y": 0}
            do_scroll_x: False

            MDBoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: [dp(12), dp(8), dp(12), dp(80)]
                spacing: dp(10)

                # ── Month navigator ──────────────────────────────────────
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(48)
                    spacing: dp(4)

                    MDIconButton:
                        icon: 'chevron-left'
                        size_hint: (None, None)
                        size: (dp(48), dp(48))
                        on_release: root.prev_month()

                    MDLabel:
                        id: month_label
                        text: root.current_month_label
                        halign: 'center'
                        font_style: 'H6'
                        size_hint_y: None
                        height: dp(48)
                        valign: 'center'

                    MDIconButton:
                        icon: 'chevron-right'
                        size_hint: (None, None)
                        size: (dp(48), dp(48))
                        on_release: root.next_month()

                # ── Balance card ──────────────────────────────────────────
                MDCard:
                    orientation: 'vertical'
                    padding: [dp(20), dp(16)]
                    size_hint_y: None
                    height: dp(140)
                    md_bg_color: app.theme_cls.primary_dark
                    radius: [dp(16)]
                    elevation: 4

                    MDLabel:
                        text: "Net Balance"
                        theme_text_color: "Custom"
                        text_color: 1, 1, 1, 0.65
                        font_style: "Caption"
                        adaptive_height: True

                    MDLabel:
                        id: balance_label
                        text: "$0.00"
                        theme_text_color: "Custom"
                        text_color: 1, 1, 1, 1
                        font_style: "H4"
                        adaptive_height: True

                    MDBoxLayout:
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: dp(24)
                        padding: [0, dp(6), 0, 0]

                        MDBoxLayout:
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            MDLabel:
                                text: "(+) Income"
                                theme_text_color: "Custom"
                                text_color: 0.4, 1, 0.55, 1
                                font_style: "Caption"
                                adaptive_height: True
                            MDLabel:
                                id: income_label
                                text: "$0.00"
                                theme_text_color: "Custom"
                                text_color: 0.4, 1, 0.55, 1
                                font_style: "Subtitle1"
                                adaptive_height: True

                        MDBoxLayout:
                            orientation: 'vertical'
                            size_hint_y: None
                            height: self.minimum_height
                            MDLabel:
                                text: "(-) Expenses"
                                theme_text_color: "Custom"
                                text_color: 1, 0.45, 0.45, 1
                                font_style: "Caption"
                                adaptive_height: True
                            MDLabel:
                                id: expense_label
                                text: "$0.00"
                                theme_text_color: "Custom"
                                text_color: 1, 0.45, 0.45, 1
                                font_style: "Subtitle1"
                                adaptive_height: True

                # ── Income vs Expense chart ───────────────────────────
                MDCard:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: dp(150)
                    radius: [dp(12)]
                    padding: [dp(8), dp(8)]

                    MDLabel:
                        text: "Income vs Expense"
                        font_style: "Caption"
                        theme_text_color: "Secondary"
                        adaptive_height: True
                        padding: [dp(8), 0]

                    BoxLayout:
                        id: income_expense_chart
                        size_hint_y: None
                        height: dp(120)

                # ── 6-Month Trend ────────────────────────────────────
                MDCard:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: dp(180)
                    radius: [dp(12)]
                    padding: [dp(8), dp(8)]

                    MDLabel:
                        text: "Spending Trend"
                        font_style: "Caption"
                        theme_text_color: "Secondary"
                        adaptive_height: True
                        padding: [dp(8), 0]

                    BoxLayout:
                        id: trend_chart
                        size_hint_y: None
                        height: dp(150)

                # ── Quick actions ─────────────────────────────────────
                MDBoxLayout:
                    size_hint_y: None
                    height: dp(42)
                    spacing: dp(8)

                    MDRaisedButton:
                        text: "TRENDS"
                        size_hint_x: 1
                        size_hint_y: None
                        height: dp(42)
                        on_release: app.go_to_trends()
                        md_bg_color: app.theme_cls.primary_color
                        elevation: 0

                    MDRaisedButton:
                        text: "BUDGET"
                        size_hint_x: 1
                        size_hint_y: None
                        height: dp(42)
                        on_release: app.go_to_budget()
                        md_bg_color: app.theme_cls.primary_dark
                        elevation: 0

                # ── Recent transactions header ─────────────────────────
                MDBoxLayout:
                    size_hint_y: None
                    height: self.minimum_height
                    padding: [dp(4), dp(4), 0, 0]

                    MDLabel:
                        text: "Recent Transactions"
                        font_style: "Subtitle1"
                        adaptive_height: True

                    MDLabel:
                        text: "See all"
                        halign: "right"
                        theme_text_color: "Primary"
                        font_style: "Caption"
                        adaptive_height: True
                        on_touch_down: if self.collide_point(*args[1].pos): app.go_to_history()

                # ── Transactions list ──────────────────────────────────
                MDBoxLayout:
                    id: txn_list
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(6)

        MDFloatingActionButton:
            icon: 'plus'
            pos_hint: {'right': 0.95, 'y': 0.02}
            on_release: app.go_to_add()
            md_bg_color: app.theme_cls.primary_color
            elevation: 6
"""

Builder.load_string(KV)


class DashboardTab(MDBoxLayout):
    current_month_label = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        now = datetime.now()
        self._year = now.year
        self._month = now.month
        self._update_label()
        Clock.schedule_once(self.refresh, 0.3)

    # ---------------------------------------------------------------- helpers
    def _ym(self) -> str:
        return f"{self._year:04d}-{self._month:02d}"

    def _update_label(self):
        self.current_month_label = date(self._year, self._month, 1).strftime("%B %Y")

    # ---------------------------------------------------------------- public
    def refresh(self, *_):
        from models.database import Database
        db = Database.get()
        s = db.get_monthly_summary(self._ym())

        balance = s["balance"]
        self.ids.balance_label.text = f"${balance:,.2f}"
        self.ids.balance_label.text_color = (
            (0.4, 1, 0.55, 1) if balance >= 0 else (1, 0.45, 0.45, 1)
        )
        self.ids.income_label.text  = f"${s['income']:,.2f}"
        self.ids.expense_label.text = f"${s['expense']:,.2f}"

        # Income vs Expense chart
        self._update_income_expense_chart(s["income"], s["expense"])

        # 6-month trend line
        self._update_trend_chart(db)

        # Recent transactions
        txns = db.get_transactions(year_month=self._ym(), limit=10)
        self.ids.txn_list.clear_widgets()
        if txns:
            for t in txns:
                self.ids.txn_list.add_widget(self._make_row(t))
        else:
            self.ids.txn_list.add_widget(MDLabel(
                text="No transactions yet. Tap + to add one.",
                halign="center",
                theme_text_color="Secondary",
                adaptive_height=True,
                padding=[0, dp(20)],
            ))

    def _update_income_expense_chart(self, income: float, expense: float):
        from utils.charts import IncomeExpenseBar
        container = self.ids.income_expense_chart
        container.clear_widgets()
        chart = IncomeExpenseBar(income=income, expense=expense)
        chart.size_hint = (1, 1)
        container.add_widget(chart)

    def _update_trend_chart(self, db):
        from utils.charts import MonthlyTrendLine
        summaries = db.get_monthly_summaries(6)
        data_points = [(s["label"], s["expense"]) for s in summaries]
        container = self.ids.trend_chart
        container.clear_widgets()
        chart = MonthlyTrendLine(data_points=data_points)
        chart.size_hint = (1, 1)
        container.add_widget(chart)

    def _make_row(self, t: dict) -> MDCard:
        card = MDCard(
            orientation="horizontal",
            padding=[dp(12), dp(10)],
            size_hint_y=None,
            height=dp(64),
            radius=[dp(10)],
            ripple_behavior=True,
        )
        left = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(2))
        desc = (t.get("description") or t.get("category") or "-")[:30]
        left.add_widget(MDLabel(
            text=desc, font_style="Body1", adaptive_height=True,
        ))
        left.add_widget(MDLabel(
            text=f"{t.get('category','')[:20]} | {t.get('date','')}",
            font_style="Caption", theme_text_color="Secondary", adaptive_height=True,
        ))
        sign = "+" if t["type"] == "income" else "-"
        color = (0.4, 1, 0.55, 1) if t["type"] == "income" else (1, 0.45, 0.45, 1)
        amt = MDLabel(
            text=f"{sign}${t['amount']:,.2f}",
            halign="right",
            theme_text_color="Custom",
            text_color=color,
            font_style="Subtitle1",
            size_hint_x=0.38,
        )
        card.add_widget(left)
        card.add_widget(amt)
        return card

    # ---------------------------------------------------------------- nav
    def prev_month(self):
        if self._month == 1:
            self._year -= 1
            self._month = 12
        else:
            self._month -= 1
        self._update_label()
        self.refresh()

    def next_month(self):
        if self._month == 12:
            self._year += 1
            self._month = 1
        else:
            self._month += 1
        self._update_label()
        self.refresh()
