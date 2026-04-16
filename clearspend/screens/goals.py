"""Goals tab - savings goals with progress tracking and milestone celebrations."""
from __future__ import annotations
from datetime import datetime, date

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.progressbar import MDProgressBar
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.textfield import MDTextField

KV = """
<GoalsTab>:
    orientation: 'vertical'
    md_bg_color: app.theme_cls.bg_normal

    MDTopAppBar:
        title: "Savings Goals"
        elevation: 2
        right_action_items: [["plus", lambda x: root.show_add_goal(), "Add goal"]]

    ScrollView:
        do_scroll_x: False

        MDBoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            padding: [dp(12), dp(10), dp(12), dp(80)]
            spacing: dp(10)

            # Summary card
            MDCard:
                orientation: 'vertical'
                padding: [dp(16), dp(14)]
                size_hint_y: None
                height: self.minimum_height
                radius: [dp(16)]
                md_bg_color: app.theme_cls.primary_dark
                elevation: 4

                MDLabel:
                    text: "Goals Overview"
                    theme_text_color: "Custom"
                    text_color: 1, 1, 1, 0.65
                    font_style: "Caption"
                    adaptive_height: True

                MDBoxLayout:
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(24)
                    padding: [0, dp(4), 0, 0]

                    MDBoxLayout:
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height
                        MDLabel:
                            text: "Active Goals"
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 0.65
                            font_style: "Caption"
                            adaptive_height: True
                        MDLabel:
                            id: active_count
                            text: "0"
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                            font_style: "H5"
                            adaptive_height: True

                    MDBoxLayout:
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height
                        MDLabel:
                            text: "Total Saved"
                            theme_text_color: "Custom"
                            text_color: 0.4, 1, 0.55, 0.9
                            font_style: "Caption"
                            adaptive_height: True
                        MDLabel:
                            id: total_saved
                            text: "$0"
                            theme_text_color: "Custom"
                            text_color: 0.4, 1, 0.55, 1
                            font_style: "H5"
                            adaptive_height: True

                    MDBoxLayout:
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height
                        MDLabel:
                            text: "Total Target"
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 0.65
                            font_style: "Caption"
                            adaptive_height: True
                        MDLabel:
                            id: total_target
                            text: "$0"
                            theme_text_color: "Custom"
                            text_color: 1, 1, 1, 1
                            font_style: "H5"
                            adaptive_height: True

            MDLabel:
                text: "MY GOALS"
                font_style: "Overline"
                theme_text_color: "Secondary"
                adaptive_height: True
                padding: [dp(4), dp(8), 0, dp(2)]

            MDBoxLayout:
                id: goals_list
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(10)

            MDLabel:
                text: "COMPLETED"
                font_style: "Overline"
                theme_text_color: "Secondary"
                adaptive_height: True
                padding: [dp(4), dp(12), 0, dp(2)]

            MDBoxLayout:
                id: completed_list
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(8)
"""

Builder.load_string(KV)

_GOAL_ICONS = {
    "Travel": "airplane",
    "Emergency Fund": "shield-check",
    "Car": "car",
    "Home": "home",
    "Education": "school",
    "Electronics": "laptop",
    "Vacation": "beach",
    "Wedding": "ring",
    "Other": "flag",
}

_GOAL_SUGGESTIONS = [
    ("Emergency Fund", 5000, "3-6 months of expenses for unexpected events"),
    ("Vacation", 2000, "Annual travel fund"),
    ("New Phone / Laptop", 1200, "Electronics upgrade"),
    ("Car Down Payment", 5000, "Saving for a vehicle"),
    ("Investment Starter", 1000, "First step to investing"),
]


class GoalsTab(MDBoxLayout):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._dialog = None
        self._deposit_dialog = None
        Clock.schedule_once(self.refresh, 0.5)

    def refresh(self, *_):
        from models.database import Database
        db = Database.get()
        goals = db.get_goals()

        active = [g for g in goals if not g["completed"]]
        done   = [g for g in goals if g["completed"]]

        self.ids.active_count.text = str(len(active))
        total_saved  = sum(g["saved"] for g in active)
        total_target = sum(g["target"] for g in active)
        self.ids.total_saved.text  = f"${total_saved:,.0f}"
        self.ids.total_target.text = f"${total_target:,.0f}"

        self.ids.goals_list.clear_widgets()
        if active:
            for g in active:
                self.ids.goals_list.add_widget(self._make_goal_card(g))
        else:
            self.ids.goals_list.add_widget(MDLabel(
                text="No active goals. Tap + to create one!",
                halign="center", theme_text_color="Secondary", adaptive_height=True,
                padding=[0, dp(12)],
            ))
            self._show_suggestions()

        self.ids.completed_list.clear_widgets()
        if done:
            for g in done:
                self.ids.completed_list.add_widget(self._make_completed_card(g))
        else:
            self.ids.completed_list.add_widget(MDLabel(
                text="No completed goals yet - keep going!",
                halign="center", theme_text_color="Secondary", adaptive_height=True,
            ))

    def _show_suggestions(self):
        """Show goal suggestions when user has no active goals."""
        self.ids.goals_list.add_widget(MDLabel(
            text="IDEAS TO GET STARTED",
            font_style="Overline", theme_text_color="Secondary",
            adaptive_height=True, padding=[dp(4), dp(8), 0, dp(2)],
        ))
        for name, target, desc in _GOAL_SUGGESTIONS[:3]:
            card = MDCard(
                orientation="horizontal",
                padding=[dp(14), dp(10)],
                size_hint_y=None,
                height=dp(72),
                radius=[dp(10)],
                md_bg_color=(0.15, 0.15, 0.18, 1),
                ripple_behavior=True,
            )
            box = MDBoxLayout(orientation="vertical", adaptive_height=True)
            box.add_widget(MDLabel(
                text=name, font_style="Body1", adaptive_height=True,
            ))
            box.add_widget(MDLabel(
                text=desc, font_style="Caption",
                theme_text_color="Secondary", adaptive_height=True,
            ))
            card.add_widget(box)
            amt_label = MDLabel(
                text=f"${target:,}", halign="right",
                font_style="Subtitle2", theme_text_color="Primary",
            )
            card.add_widget(amt_label)
            # Capture for lambda closure
            _n, _t = name, target
            card.bind(on_release=lambda x, n=_n, t=_t: self.show_add_goal(prefill_name=n, prefill_target=t))
            self.ids.goals_list.add_widget(card)

    def _make_goal_card(self, g):
        pct = min(g["saved"] / g["target"] * 100, 100) if g["target"] > 0 else 0
        remaining = max(g["target"] - g["saved"], 0)

        card = MDCard(
            orientation="vertical",
            padding=[dp(14), dp(12)],
            size_hint_y=None,
            height=dp(120),
            radius=[dp(12)],
            ripple_behavior=True,
        )

        header = MDBoxLayout(size_hint_y=None, height=self._line_h(), spacing=dp(8))
        # Icon text as short category prefix instead of MDIcon (avoids import complexity)
        cat = g.get("category", "Other")
        icon_prefix = {"Travel": "[T]", "Emergency Fund": "[!]", "Car": "[C]",
                       "Home": "[H]", "Education": "[E]"}.get(cat, "")
        goal_display = f"{icon_prefix} {g['name'][:26]}".strip() if icon_prefix else g["name"][:28]
        header.add_widget(MDLabel(
            text=goal_display, font_style="Body1", adaptive_height=True,
        ))
        pct_txt = f"{pct:.0f}%"
        header.add_widget(MDLabel(
            text=pct_txt, halign="right", font_style="Body2",
            theme_text_color="Custom",
            text_color=(0.4, 1, 0.55, 1) if pct >= 100 else (1, 1, 1, 0.8),
            adaptive_height=True,
        ))
        card.add_widget(header)

        bar = MDProgressBar(value=pct, size_hint_y=None, height=dp(6))
        card.add_widget(bar)

        sub = MDBoxLayout(size_hint_y=None, height=self._line_h(), padding=[0, dp(4), 0, 0])
        sub.add_widget(MDLabel(
            text=f"${g['saved']:,.0f} saved of ${g['target']:,.0f}",
            font_style="Caption", theme_text_color="Secondary", adaptive_height=True,
        ))
        deadline_txt = f"By {g['deadline']}" if g.get("deadline") else f"${remaining:,.0f} to go"
        sub.add_widget(MDLabel(
            text=deadline_txt, halign="right", font_style="Caption",
            theme_text_color="Secondary", adaptive_height=True,
        ))
        card.add_widget(sub)

        btn_row = MDBoxLayout(size_hint_y=None, height=dp(30), spacing=dp(8), padding=[0, dp(4), 0, 0])
        dep_btn = MDFlatButton(text="DEPOSIT", size_hint_x=None, height=dp(28))
        dep_btn.bind(on_release=lambda x, gid=g["id"]: self.show_deposit(gid))
        btn_row.add_widget(dep_btn)
        card.add_widget(btn_row)

        return card

    @staticmethod
    def _line_h():
        return dp(28)

    def _make_completed_card(self, g):
        card = MDCard(
            orientation="horizontal",
            padding=[dp(14), dp(10)],
            size_hint_y=None,
            height=dp(56),
            radius=[dp(10)],
            md_bg_color=(0.12, 0.25, 0.15, 1),
        )
        card.add_widget(MDLabel(
            text=g["name"][:28], font_style="Body1", adaptive_height=True,
        ))
        card.add_widget(MDLabel(
            text=f"${g['saved']:,.0f} saved", halign="right",
            font_style="Caption", theme_text_color="Custom",
            text_color=(0.4, 1, 0.55, 1), adaptive_height=True,
        ))
        return card

    # -------------------------------------------------------- add goal dialog
    def show_add_goal(self, *_, prefill_name="", prefill_target=0):
        name_field = MDTextField(
            hint_text="Goal name (e.g. Emergency Fund)", mode="rectangle",
            text=prefill_name, size_hint_y=None, height=dp(56),
        )
        target_field = MDTextField(
            hint_text="Target amount (CAD)", mode="rectangle",
            input_filter="float",
            text=str(prefill_target) if prefill_target else "",
            size_hint_y=None, height=dp(56),
        )
        deadline_field = MDTextField(
            hint_text="Deadline (YYYY-MM, optional)", mode="rectangle",
            size_hint_y=None, height=dp(56),
        )
        initial_field = MDTextField(
            hint_text="Initial deposit (optional)", mode="rectangle",
            input_filter="float", size_hint_y=None, height=dp(56),
        )
        box = MDBoxLayout(
            orientation="vertical", spacing=dp(10),
            size_hint_y=None, height=dp(244),
        )
        for f in (name_field, target_field, deadline_field, initial_field):
            box.add_widget(f)

        def _save(*_):
            name = name_field.text.strip()
            target_txt = target_field.text.strip()
            if not name or not target_txt:
                Snackbar(text="Name and target amount required.").open()
                return
            try:
                target = float(target_txt)
                if target <= 0:
                    raise ValueError
            except ValueError:
                Snackbar(text="Enter a valid positive target amount.").open()
                return
            initial = 0.0
            try:
                initial = float(initial_field.text.strip() or "0")
            except ValueError:
                pass
            deadline = deadline_field.text.strip() or None
            from models.database import Database
            Database.get().add_goal(name=name, target=target, saved=initial, deadline=deadline)
            self._dialog.dismiss()
            self.refresh()
            Snackbar(text=f"Goal '{name}' created!").open()

        self._dialog = MDDialog(
            title="Create Savings Goal",
            type="custom",
            content_cls=box,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda *_: self._dialog.dismiss()),
                MDRaisedButton(text="CREATE", on_release=_save),
            ],
        )
        self._dialog.open()

    # -------------------------------------------------------- deposit dialog
    def show_deposit(self, goal_id):
        amt_field = MDTextField(
            hint_text="Amount to deposit (CAD)", mode="rectangle",
            input_filter="float", size_hint_y=None, height=dp(56),
        )
        box = MDBoxLayout(
            orientation="vertical", size_hint_y=None, height=dp(56),
        )
        box.add_widget(amt_field)

        def _save(*_):
            try:
                amt = float(amt_field.text.strip())
                if amt <= 0:
                    raise ValueError
            except ValueError:
                Snackbar(text="Enter a valid amount.").open()
                return
            from models.database import Database
            db = Database.get()
            g = db.deposit_goal(goal_id, amt)
            self._deposit_dialog.dismiss()
            self.refresh()
            if g and g["saved"] >= g["target"]:
                Snackbar(text=f"Goal '{g['name']}' complete! Well done!").open()
            else:
                Snackbar(text=f"${amt:,.2f} added to goal.").open()

        self._deposit_dialog = MDDialog(
            title="Add to Goal",
            type="custom",
            content_cls=box,
            buttons=[
                MDFlatButton(text="CANCEL", on_release=lambda *_: self._deposit_dialog.dismiss()),
                MDRaisedButton(text="DEPOSIT", on_release=_save),
            ],
        )
        self._deposit_dialog.open()
