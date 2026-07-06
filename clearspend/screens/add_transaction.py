"""Add Transaction screen - full-screen form for manual expense/income entry."""
from __future__ import annotations
from datetime import date

from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, BooleanProperty
from kivy.uix.screenmanager import Screen
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.snackbar import Snackbar

KV = """
#:import ScrollEffect kivy.effects.scroll.ScrollEffect
<AddTransactionScreen>:
    name: 'add_transaction'

    MDBoxLayout:
        orientation: 'vertical'
        md_bg_color: app.theme_cls.bg_normal

        MDTopAppBar:
            title: "Add Transaction"
            elevation: 2
            left_action_items: [["arrow-left", lambda x: app.go_back()]]

        ScrollView:
            do_scroll_x: False
            effect_cls: ScrollEffect

            MDBoxLayout:
                orientation: 'vertical'
                size_hint_y: None
                height: self.minimum_height
                padding: [dp(20), dp(16)]
                spacing: dp(14)
                canvas.before:
                    Color:
                        rgba: app.theme_cls.bg_normal
                    Rectangle:
                        pos: self.pos
                        size: self.size

                # ── Type toggle ──────────────────────────────────────────
                MDBoxLayout:
                    size_hint_y: None
                    height: self.minimum_height
                    spacing: dp(12)

                    MDRaisedButton:
                        id: btn_expense
                        text: "EXPENSE"
                        size_hint_x: 1
                        on_release: root.set_type('expense')
                        md_bg_color:
                            app.theme_cls.primary_color if root.tx_type == 'expense' \
                            else app.theme_cls.bg_darkest

                    MDRaisedButton:
                        id: btn_income
                        text: "INCOME"
                        size_hint_x: 1
                        on_release: root.set_type('income')
                        md_bg_color:
                            [0.2, 0.75, 0.35, 1] if root.tx_type == 'income' \
                            else app.theme_cls.bg_darkest

                # ── Amount ───────────────────────────────────────────────
                MDTextField:
                    id: amount_field
                    hint_text: "Amount (CAD)"
                    mode: "rectangle"
                    input_filter: "float"
                    input_type: "number"
                    size_hint_y: None
                    height: dp(56)
                    icon_right: "currency-usd"

                # ── Category ─────────────────────────────────────────────
                MDTextField:
                    id: category_field
                    hint_text: "Category"
                    mode: "rectangle"
                    size_hint_y: None
                    height: dp(56)
                    icon_right: "chevron-down"
                    text: root.selected_category
                    on_focus: if self.focus: root.open_category_menu(self)

                # ── Description ───────────────────────────────────────────
                MDTextField:
                    id: desc_field
                    hint_text: "Description (optional)"
                    mode: "rectangle"
                    size_hint_y: None
                    height: dp(56)
                    on_text_validate: root.auto_classify_description()
                    on_focus: if not self.focus and self.text: root.auto_classify_description()

                # ── Date ──────────────────────────────────────────────────
                MDTextField:
                    id: date_field
                    hint_text: "Date (YYYY-MM-DD)"
                    mode: "rectangle"
                    size_hint_y: None
                    height: dp(56)
                    text: root.selected_date
                    icon_right: "calendar"
                    on_focus: if self.focus: root.open_date_picker()

                # ── Save button ───────────────────────────────────────────
                MDRaisedButton:
                    text: "SAVE TRANSACTION"
                    size_hint_x: 1
                    height: dp(52)
                    size_hint_y: None
                    on_release: root.save()
                    md_bg_color: app.theme_cls.primary_color

                MDFlatButton:
                    text: "CANCEL"
                    size_hint_x: 1
                    on_release: app.go_back()
                    theme_text_color: "Secondary"
"""

Builder.load_string(KV)


class AddTransactionScreen(Screen):
    tx_type = StringProperty("expense")
    selected_category = StringProperty("")
    selected_date = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_date = date.today().isoformat()
        self._menu: MDDropdownMenu | None = None

    def on_enter(self):
        """Reset form when entering the screen."""
        self.ids.amount_field.text = ""
        self.ids.desc_field.text = ""
        self.selected_date = date.today().isoformat()
        self.selected_category = ""
        self.tx_type = "expense"

    def set_type(self, type_: str):
        self.tx_type = type_

    # ---------------------------------------------------------------- category
    def open_category_menu(self, caller):
        from models.database import Database
        cats = Database.get().get_categories()
        items = [
            {
                "text": c["name"],
                "viewclass": "OneLineListItem",
                "on_release": lambda x=c["name"]: self._pick_category(x),
            }
            for c in cats
        ]
        self._menu = MDDropdownMenu(
            caller=caller,
            items=items,
            width_mult=4,
            max_height=dp(300),
        )
        self._menu.open()

    def _pick_category(self, name: str):
        self.selected_category = name
        self.ids.category_field.text = name
        if self._menu:
            self._menu.dismiss()

    def auto_classify_description(self):
        """Auto-fill category from description using keyword + Claude API."""
        desc = self.ids.desc_field.text.strip()
        if not desc:
            return
        # Don't override a manually chosen category
        if self.selected_category:
            return
        from utils.classifier import classify_keyword
        result = classify_keyword(desc)
        if result:
            self.selected_category = result
            self.ids.category_field.text = result
            return
        # Try Claude API async - don't block UI
        from kivy.clock import Clock
        Clock.schedule_once(lambda *_: self._classify_via_api(desc), 0)

    def _classify_via_api(self, desc: str):
        """Background classification via Gemini API (non-blocking)."""
        try:
            from utils.classifier import classify_gemini, _get_gemini_api_key
            api_key = _get_gemini_api_key()
            if not api_key:
                return
            result = classify_gemini(desc, api_key)
            if result and not self.selected_category:
                from kivy.clock import Clock
                Clock.schedule_once(lambda *_: self._set_auto_category(result), 0)
        except Exception:
            pass

    def _set_auto_category(self, category: str):
        if not self.selected_category:
            self.selected_category = category
            self.ids.category_field.text = category

    # ---------------------------------------------------------------- date
    def open_date_picker(self):
        try:
            from kivymd.uix.picker import MDDatePicker
            picker = MDDatePicker()
            picker.bind(on_save=self._on_date_save, on_cancel=lambda *_: None)
            picker.open()
        except Exception:
            pass  # date picker unavailable - user types manually

    def _on_date_save(self, instance, value, *_):
        self.selected_date = value.strftime("%Y-%m-%d")
        self.ids.date_field.text = self.selected_date

    # ---------------------------------------------------------------- save
    def save(self):
        amount_txt = self.ids.amount_field.text.strip()
        if not amount_txt:
            Snackbar(text="Please enter an amount.").open()
            return
        try:
            amount = float(amount_txt)
            if amount <= 0:
                raise ValueError
        except ValueError:
            Snackbar(text="Enter a valid positive amount.").open()
            return

        category = self.selected_category or "Other"
        desc = self.ids.desc_field.text.strip()
        tx_date = self.ids.date_field.text.strip() or date.today().isoformat()

        from models.database import Database
        Database.get().add_transaction(
            amount=amount,
            type_=self.tx_type,
            category=category,
            description=desc,
            trans_date=tx_date,
        )

        Snackbar(text=f"{'Expense' if self.tx_type == 'expense' else 'Income'} saved!").open()
        # Refresh dashboard before going back
        app = self._get_app()
        if app:
            app.refresh_dashboard()
        app.go_back()

    @staticmethod
    def _get_app():
        from kivy.app import App
        return App.get_running_app()
