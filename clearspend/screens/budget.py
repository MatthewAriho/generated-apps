"""Budget screen - set monthly limits, track over/under, forecast spend.

V1.5 feature: populated in V1.5 milestone.
"""
from __future__ import annotations
from datetime import datetime, date

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.screenmanager import Screen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.textfield import MDTextField

KV = """
<BudgetScreen>:
    name: 'budget'

    MDBoxLayout:
        orientation: 'vertical'
        md_bg_color: app.theme_cls.bg_normal

        MDTopAppBar:
            title: "Monthly Budget"
            elevation: 2
            left_action_items: [["arrow-left", lambda x: app.go_back()]]
            right_action_items: [["plus", lambda x: root.show_add_budget(), "Add budget"]]

        ScrollView:
            do_scroll_x: False

            MDBoxLayout:
                orientation: 'vertical'
                adaptive_height: True
                padding: [dp(12), dp(10)]
                spacing: dp(10)

                MDLabel:
                    id: period_label
                    text: root.period_label
                    font_style: 'H6'
                    halign: 'center'
                    adaptive_height: True

                # Forecast card
                MDCard:
                    orientation: 'vertical'
                    padding: [dp(16), dp(12)]
                    adaptive_height: True
                    radius: [dp(12)]
                    md_bg_color: app.theme_cls.primary_dark

                    MDLabel:
                        id: forecast_label
                        text: root.forecast_text
                        font_style: "Body1"
                        theme_text_color: "Custom"
                        text_color: 1, 1, 1, 0.9
                        adaptive_height: True

                # Budget items
                MDLabel:
                    text: "BUDGET LIMITS"
                    font_style: "Overline"
                    theme_text_color: "Secondary"
                    adaptive_height: True
                    padding: [dp(4), dp(8), 0, dp(2)]

                MDBoxLayout:
                    id: budget_list
                    orientation: 'vertical'
                    adaptive_height: True
                    spacing: dp(8)

                # Saving tips
                MDLabel:
                    text: "SAVING TIPS"
                    font_style: "Overline"
                    theme_text_color: "Secondary"
                    adaptive_height: True
                    padding: [dp(4), dp(12), 0, dp(2)]

                MDBoxLayout:
                    id: tips_box
                    orientation: 'vertical'
                    adaptive_height: True
                    spacing: dp(6)
"""

Builder.load_string(KV)

_SAVING_TIPS = {
    "Restaurants":        "Consider cooking at home 2 extra days a week to cut this by ~30%.",
    "Rides (Uber/Lyft)":  "Try transit or biking for shorter trips - could save $50+/month.",
    "Nightlife / Bars":   "Pre-gaming or limiting outings to 1/week can save significantly.",
    "ATM / Cash":         "Avoid ATM fees by planning cash withdrawals at your own bank.",
    "Subscriptions":      "Audit your subscriptions - cancel any you haven't used in 30 days.",
    "Shopping":           "Try a 24-hour rule before non-essential purchases.",
    "Food & Dining":      "Meal prepping on Sundays can reduce food spending by 20-40%.",
}


class BudgetScreen(Screen):
    period_label  = StringProperty("")
    forecast_text = StringProperty("Set budgets to see your forecast.")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        now = datetime.now()
        self._year  = now.year
        self._month = now.month
        self.period_label = date(now.year, now.month, 1).strftime("%B %Y")
        self._dialog: MDDialog | None = None

    def on_enter(self):
        Clock.schedule_once(self.refresh, 0.1)

    def refresh(self, *_):
        from models.database import Database
        db  = Database.get()
        ym  = f"{self._year:04d}-{self._month:02d}"

        statuses = db.get_budget_status(ym)
        self.ids.budget_list.clear_widgets()

        if statuses:
            for s in statuses:
                self.ids.budget_list.add_widget(self._make_budget_card(s))
            self._update_forecast(db, ym)
            self._generate_tips(statuses)
        else:
            self.ids.budget_list.add_widget(MDLabel(
                text="No budgets set. Tap + to add one.",
                halign="center", theme_text_color="Secondary", adaptive_height=True,
            ))
            self.forecast_text = "Set category budgets to see forecasting."

    def _make_budget_card(self, s: dict) -> MDCard:
        pct_int = int(s["pct"] * 100)
        over = s["spent"] > s["budget"]
        card = MDCard(
            orientation="vertical",
            padding=[dp(12), dp(10)],
            size_hint_y=None,
            height=dp(85),
            radius=[dp(10)],
        )
        row = MDBoxLayout(adaptive_height=True)
        row.add_widget(MDLabel(text=s["category"][:24], font_style="Body1", adaptive_height=True))
        status_txt = f"OVER by ${abs(s['remaining']):.2f}" if over else f"${s['remaining']:.2f} left"
        row.add_widget(MDLabel(
            text=status_txt, halign="right", font_style="Caption",
            theme_text_color="Custom",
            text_color=(1, 0.3, 0.3, 1) if over else (0.4, 1, 0.55, 1),
            adaptive_height=True,
        ))
        card.add_widget(row)

        sub = MDBoxLayout(adaptive_height=True)
        sub.add_widget(MDLabel(
            text=f"${s['spent']:,.2f} of ${s['budget']:,.2f}",
            font_style="Caption", theme_text_color="Secondary", adaptive_height=True,
        ))
        sub.add_widget(MDLabel(
            text=f"{pct_int}%", halign="right",
            font_style="Caption", theme_text_color="Secondary", adaptive_height=True,
        ))
        card.add_widget(sub)

        bar = MDProgressBar(
            value=min(pct_int, 100),
            size_hint_y=None, height=dp(6),
            color=(1, 0.35, 0.35, 1) if over else None,
        )
        card.add_widget(bar)
        return card

    def _update_forecast(self, db, ym: str):
        from models.database import Database
        import calendar
        year, month = map(int, ym.split("-"))
        today = datetime.now()
        days_elapsed = today.day
        total_days   = calendar.monthrange(year, month)[1]

        summary = db.get_monthly_summary(ym)
        spent   = summary["expense"]
        if days_elapsed > 0:
            pace          = spent / days_elapsed
            projected_end = pace * total_days
            days_left     = total_days - days_elapsed
            self.forecast_text = (
                f"Day {days_elapsed}/{total_days} | "
                f"Spent ${spent:,.2f} | "
                f"Projected total: ${projected_end:,.2f} | "
                f"{days_left} days remaining"
            )

    def _generate_tips(self, statuses: list[dict]):
        self.ids.tips_box.clear_widgets()
        tips_shown = 0
        for s in sorted(statuses, key=lambda x: x["spent"], reverse=True)[:3]:
            tip = _SAVING_TIPS.get(s["category"])
            if tip:
                card = MDCard(
                    orientation="horizontal",
                    padding=[dp(12), dp(10)],
                    size_hint_y=None,
                    height=dp(72),
                    radius=[dp(10)],
                )
                box = MDBoxLayout(orientation="vertical", adaptive_height=True)
                box.add_widget(MDLabel(
                    text=f"💡 {s['category']}", font_style="Caption",
                    theme_text_color="Primary", adaptive_height=True,
                ))
                box.add_widget(MDLabel(
                    text=tip, font_style="Body2",
                    theme_text_color="Secondary", adaptive_height=True,
                ))
                card.add_widget(box)
                self.ids.tips_box.add_widget(card)
                tips_shown += 1

        if tips_shown == 0:
            self.ids.tips_box.add_widget(MDLabel(
                text="Spend more to get personalised tips!",
                halign="center", theme_text_color="Secondary", adaptive_height=True,
            ))

    # ---------------------------------------------------------------- add budget
    def show_add_budget(self):
        cat_field = MDTextField(hint_text="Category (e.g. Restaurants)", mode="rectangle")
        amt_field = MDTextField(
            hint_text="Monthly limit (CAD)", mode="rectangle", input_filter="float"
        )
        box = MDBoxLayout(
            orientation="vertical", spacing=dp(12),
            size_hint_y=None, height=dp(130),
        )
        box.add_widget(cat_field)
        box.add_widget(amt_field)

        def _save(*_):
            cat = cat_field.text.strip()
            amt_txt = amt_field.text.strip()
            if not cat or not amt_txt:
                Snackbar(text="Fill in both fields.").open()
                return
            try:
                amt = float(amt_txt)
            except ValueError:
                Snackbar(text="Invalid amount.").open()
                return
            from models.database import Database
            ym = f"{self._year:04d}-{self._month:02d}"
            Database.get().set_budget(ym, cat, amt)
            self._dialog.dismiss()
            self.refresh()

        self._dialog = MDDialog(
            title="Set Budget Limit",
            type="custom",
            content_cls=box,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda *_: self._dialog.dismiss()),
                MDRaisedButton(text="SAVE", on_release=_save),
            ],
        )
        self._dialog.open()
