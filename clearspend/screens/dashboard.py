"""Dashboard tab - monthly summary card + recent transactions list + FAB."""
from __future__ import annotations
from datetime import date, datetime

import threading

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel

KV = """
#:import ScrollEffect kivy.effects.scroll.ScrollEffect
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
            effect_cls: ScrollEffect

            MDBoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: [dp(12), dp(8), dp(12), dp(80)]
                spacing: dp(10)
                canvas.before:
                    Color:
                        rgba: app.theme_cls.bg_normal
                    Rectangle:
                        pos: self.pos
                        size: self.size

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

                # ── Monthly comparison ────────────────────────────────
                MDCard:
                    id: comparison_card
                    orientation: 'horizontal'
                    padding: [dp(16), dp(10)]
                    size_hint_y: None
                    height: dp(50)
                    radius: [dp(10)]
                    md_bg_color: app.theme_cls.bg_dark

                    MDIcon:
                        id: comparison_icon
                        icon: "trending-neutral"
                        theme_text_color: "Custom"
                        text_color: 0.6, 0.6, 0.6, 1
                        size_hint: (None, None)
                        size: (dp(24), dp(24))
                        pos_hint: {"center_y": 0.5}

                    MDLabel:
                        id: comparison_label
                        text: ""
                        font_style: "Caption"
                        theme_text_color: "Secondary"
                        adaptive_height: True
                        padding: [dp(8), 0]

                # ── Income vs Expense chart ───────────────────────────
                MDCard:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: dp(160)
                    radius: [dp(12)]
                    padding: [dp(12), dp(10), dp(12), dp(12)]

                    MDLabel:
                        text: "Income vs Expense"
                        font_style: "Caption"
                        theme_text_color: "Secondary"
                        size_hint_y: None
                        height: dp(20)
                        padding: [0, 0]

                    BoxLayout:
                        id: income_expense_chart
                        size_hint_y: None
                        height: dp(118)

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

                # ── Financial tips ────────────────────────────────────
                MDBoxLayout:
                    size_hint_y: None
                    height: self.minimum_height
                    padding: [dp(4), dp(12), 0, 0]

                    MDLabel:
                        text: "Financial Tips"
                        font_style: "Subtitle1"
                        adaptive_height: True

                MDBoxLayout:
                    id: tips_list
                    orientation: 'vertical'
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(8)

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
        def _fetch():
            from models.database import Database
            from utils.tips import generate_tips
            db = Database.get()
            ym = self._ym()
            s = db.get_monthly_summary(ym)

            pm = self._month - 1
            py = self._year
            if pm <= 0:
                pm = 12
                py -= 1
            prev = db.get_monthly_summary(f"{py:04d}-{pm:02d}")
            summaries = db.get_monthly_summaries(6)
            txns = db.get_transactions(year_month=ym, limit=10)
            tips = generate_tips(db)
            Clock.schedule_once(lambda *_: self._apply(s, prev, py, pm, summaries, txns, tips), 0)

        threading.Thread(target=_fetch, daemon=True).start()

    def _apply(self, s, prev, prev_year, prev_month, summaries, txns, tips):
        balance = s["balance"]
        self.ids.balance_label.text = f"${balance:,.2f}"
        self.ids.balance_label.text_color = (
            (0.4, 1, 0.55, 1) if balance >= 0 else (1, 0.45, 0.45, 1)
        )
        self.ids.income_label.text  = f"${s['income']:,.2f}"
        self.ids.expense_label.text = f"${s['expense']:,.2f}"

        self._apply_comparison(s, prev, prev_year, prev_month)
        self._update_income_expense_chart(s["income"], s["expense"])
        self._apply_trend_chart(summaries)

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

        self._apply_tips(tips)

    def _apply_tips(self, tips):
        from kivymd.uix.button import MDIconButton
        _SEVERITY_COLORS = {
            "warn":  (0.85, 0.35, 0.15, 1),
            "good":  (0.18, 0.65, 0.35, 1),
            "info":  (0.20, 0.45, 0.75, 1),
        }
        box = self.ids.tips_list
        box.clear_widgets()
        for icon, title, body, severity in tips:
            color = _SEVERITY_COLORS.get(severity, _SEVERITY_COLORS["info"])

            title_lbl = MDLabel(
                text=title, font_style="Body2", bold=True,
                size_hint_y=None, height=dp(22),
                shorten=True, shorten_from="right",
                theme_text_color="Custom", text_color=(*color[:3], 1),
            )
            body_lbl = MDLabel(
                text=body, font_style="Caption",
                size_hint_y=None, height=dp(16),
                theme_text_color="Secondary",
            )
            # Enable wrapping: bind width→text_size, then texture height→label height
            def _bind(lbl):
                def _on_w(inst, w):
                    inst.text_size = (w, None)
                def _on_tex(inst, ts):
                    inst.height = ts[1]
                lbl.bind(width=_on_w, texture_size=_on_tex)
            _bind(body_lbl)
            _bind(title_lbl)

            text_box = MDBoxLayout(
                orientation="vertical", size_hint_x=1, spacing=dp(2),
                size_hint_y=None,
            )
            text_box.bind(minimum_height=text_box.setter("height"))
            text_box.add_widget(title_lbl)
            text_box.add_widget(body_lbl)

            ico = MDIconButton(
                icon=icon,
                size_hint=(None, None),
                size=(dp(36), dp(36)),
                pos_hint={"center_y": 0.5},
                theme_text_color="Custom",
                text_color=color,
            )

            card = MDCard(
                orientation="horizontal",
                padding=[dp(8), dp(10)],
                size_hint_y=None,
                height=dp(72),
                radius=[dp(10)],
                md_bg_color=(*color[:3], 0.18),
            )
            # Grow card to fit text (text_box height + top+bottom padding)
            text_box.bind(
                height=lambda inst, h, c=card: setattr(c, "height", max(dp(56), h + dp(20)))
            )
            card.add_widget(ico)
            card.add_widget(text_box)
            box.add_widget(card)

    def _apply_comparison(self, curr, prev, prev_year, prev_month):
        curr_exp = curr["expense"]
        prev_exp = prev["expense"]
        diff = curr_exp - prev_exp
        try:
            if prev_exp > 0 and abs(diff) > 0.01:
                pct = abs(diff) / prev_exp * 100
                prev_label = date(prev_year, prev_month, 1).strftime("%b")
                if diff > 0:
                    self.ids.comparison_icon.icon = "trending-up"
                    self.ids.comparison_icon.text_color = (1, 0.45, 0.45, 1)
                    self.ids.comparison_label.text = (
                        f"Spending ${abs(diff):,.0f} ({pct:.0f}%) more than {prev_label}"
                    )
                else:
                    self.ids.comparison_icon.icon = "trending-down"
                    self.ids.comparison_icon.text_color = (0.4, 1, 0.55, 1)
                    self.ids.comparison_label.text = (
                        f"Spending ${abs(diff):,.0f} ({pct:.0f}%) less than {prev_label}"
                    )
            else:
                self.ids.comparison_icon.icon = "trending-neutral"
                self.ids.comparison_icon.text_color = (0.6, 0.6, 0.6, 1)
                self.ids.comparison_label.text = "No previous month data to compare"
        except Exception:
            self.ids.comparison_label.text = ""

    def _update_income_expense_chart(self, income: float, expense: float):
        from utils.charts import IncomeExpenseBar
        container = self.ids.income_expense_chart
        container.clear_widgets()
        chart = IncomeExpenseBar(income=income, expense=expense)
        chart.size_hint = (1, 1)
        container.add_widget(chart)

    def _apply_trend_chart(self, summaries):
        from utils.charts import MonthlyTrendLine
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
        left = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(2), size_hint_x=1)
        desc_lbl = MDLabel(font_style="Body1", adaptive_height=True,
                           shorten=True, shorten_from="right", size_hint_x=1)
        desc_lbl.text = (t.get("description") or t.get("category") or "-")
        left.add_widget(desc_lbl)
        left.add_widget(MDLabel(
            text=f"{t.get('category','')[:20]} | {t.get('date','')}",
            font_style="Caption", theme_text_color="Secondary", adaptive_height=True,
            shorten=True, shorten_from="right",
        ))
        sign = "+" if t["type"] == "income" else "-"
        color = (0.4, 1, 0.55, 1) if t["type"] == "income" else (1, 0.45, 0.45, 1)
        amt = MDLabel(
            text=f"{sign}${t['amount']:,.2f}",
            halign="right",
            theme_text_color="Custom",
            text_color=color,
            font_style="Subtitle1",
            size_hint_x=None,
            width=dp(90),
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
