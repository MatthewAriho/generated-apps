"""PIN authentication screen - shown on app launch if PIN is set.

V2 feature: 4-digit PIN with SHA-256 hash stored in JsonStore.
Supports first-time PIN setup + unlock flow.
"""
from __future__ import annotations
import hashlib

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, StringProperty
from kivy.uix.screenmanager import Screen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton
from kivymd.uix.label import MDLabel

KV = """
<PinAuthScreen>:
    name: 'pin_auth'

    MDBoxLayout:
        orientation: 'vertical'
        md_bg_color: app.theme_cls.bg_normal

        MDBoxLayout:
            orientation: 'vertical'
            padding: [dp(40), dp(60), dp(40), dp(20)]
            spacing: dp(24)

            MDLabel:
                id: title_label
                text: root.title_text
                font_style: 'H5'
                halign: 'center'
                adaptive_height: True

            MDLabel:
                id: subtitle_label
                text: root.subtitle_text
                font_style: 'Body1'
                halign: 'center'
                theme_text_color: 'Secondary'
                adaptive_height: True

            # PIN dots
            MDBoxLayout:
                adaptive_height: True
                size_hint_x: 0.5
                pos_hint: {'center_x': 0.5}
                spacing: dp(16)

                MDLabel:
                    id: dot0
                    text: "_"
                    halign: 'center'
                    font_style: 'H4'
                    adaptive_height: True
                MDLabel:
                    id: dot1
                    text: "_"
                    halign: 'center'
                    font_style: 'H4'
                    adaptive_height: True
                MDLabel:
                    id: dot2
                    text: "_"
                    halign: 'center'
                    font_style: 'H4'
                    adaptive_height: True
                MDLabel:
                    id: dot3
                    text: "_"
                    halign: 'center'
                    font_style: 'H4'
                    adaptive_height: True

            MDLabel:
                id: error_label
                text: root.error_text
                halign: 'center'
                theme_text_color: 'Custom'
                text_color: 1, 0.3, 0.3, 1
                font_style: 'Caption'
                adaptive_height: True

        # Number pad
        MDBoxLayout:
            orientation: 'vertical'
            padding: [dp(40), dp(0), dp(40), dp(40)]
            spacing: dp(8)
            size_hint_y: None
            height: dp(280)

            MDBoxLayout:
                spacing: dp(8)
                MDRaisedButton:
                    text: "1"
                    size_hint_x: 1
                    size_hint_y: None
                    height: dp(56)
                    on_release: root.press_digit("1")
                MDRaisedButton:
                    text: "2"
                    size_hint_x: 1
                    size_hint_y: None
                    height: dp(56)
                    on_release: root.press_digit("2")
                MDRaisedButton:
                    text: "3"
                    size_hint_x: 1
                    size_hint_y: None
                    height: dp(56)
                    on_release: root.press_digit("3")

            MDBoxLayout:
                spacing: dp(8)
                MDRaisedButton:
                    text: "4"
                    size_hint_x: 1
                    size_hint_y: None
                    height: dp(56)
                    on_release: root.press_digit("4")
                MDRaisedButton:
                    text: "5"
                    size_hint_x: 1
                    size_hint_y: None
                    height: dp(56)
                    on_release: root.press_digit("5")
                MDRaisedButton:
                    text: "6"
                    size_hint_x: 1
                    size_hint_y: None
                    height: dp(56)
                    on_release: root.press_digit("6")

            MDBoxLayout:
                spacing: dp(8)
                MDRaisedButton:
                    text: "7"
                    size_hint_x: 1
                    size_hint_y: None
                    height: dp(56)
                    on_release: root.press_digit("7")
                MDRaisedButton:
                    text: "8"
                    size_hint_x: 1
                    size_hint_y: None
                    height: dp(56)
                    on_release: root.press_digit("8")
                MDRaisedButton:
                    text: "9"
                    size_hint_x: 1
                    size_hint_y: None
                    height: dp(56)
                    on_release: root.press_digit("9")

            MDBoxLayout:
                spacing: dp(8)
                MDFlatButton:
                    text: ""
                    size_hint_x: 1
                    size_hint_y: None
                    height: dp(56)
                MDRaisedButton:
                    text: "0"
                    size_hint_x: 1
                    size_hint_y: None
                    height: dp(56)
                    on_release: root.press_digit("0")
                MDRaisedButton:
                    text: "DEL"
                    size_hint_x: 1
                    size_hint_y: None
                    height: dp(56)
                    md_bg_color: app.theme_cls.primary_dark
                    on_release: root.backspace()

            MDRaisedButton:
                id: biometric_btn
                text: "USE FINGERPRINT"
                size_hint_x: 1
                size_hint_y: None
                height: dp(48) if root.show_biometric else 0
                opacity: 1 if root.show_biometric else 0
                disabled: not root.show_biometric
                md_bg_color: app.theme_cls.primary_dark
                on_release: root.try_biometric()
"""

Builder.load_string(KV)


def _hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


class PinAuthScreen(Screen):
    title_text     = StringProperty("ClearSpend")
    subtitle_text  = StringProperty("Enter your 4-digit PIN")
    error_text     = StringProperty("")
    is_setup_mode  = BooleanProperty(False)
    show_biometric = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._digits = ""
        self._confirm_digits = ""

    def on_enter(self):
        self._digits = ""
        self._confirm_digits = ""
        self.error_text = ""
        stored = self._get_stored_pin()
        if stored is None:
            self.is_setup_mode  = True
            self.show_biometric = False
            self.title_text     = "Set a PIN"
            self.subtitle_text  = "Choose a 4-digit PIN to secure your data"
        else:
            self.is_setup_mode = False
            self.title_text    = "ClearSpend"
            self.subtitle_text = "Enter your PIN"
            # Offer biometric only in unlock mode
            from utils.biometric import biometric_available
            self.show_biometric = biometric_available()
        self._update_dots()

    # ---------------------------------------------------------------- pad
    def press_digit(self, d: str):
        if len(self._digits) >= 4:
            return
        self._digits += d
        self._update_dots()
        if len(self._digits) == 4:
            Clock.schedule_once(self._evaluate, 0.15)

    def backspace(self):
        self._digits = self._digits[:-1]
        self._update_dots()
        self.error_text = ""

    # ---------------------------------------------------------------- logic
    def _evaluate(self, *_):
        if self.is_setup_mode:
            self._handle_setup()
        else:
            self._handle_unlock()

    def _handle_setup(self):
        if not self._confirm_digits:
            # First entry - ask to confirm
            self._confirm_digits = self._digits
            self._digits = ""
            self.subtitle_text = "Confirm your PIN"
            self.error_text = ""
            self._update_dots()
        else:
            # Second entry - compare
            if self._digits == self._confirm_digits:
                self._save_pin(self._digits)
                self._proceed_to_app()
            else:
                self._confirm_digits = ""
                self._digits = ""
                self.subtitle_text = "Pins didn't match. Choose again."
                self.error_text = "PIN mismatch - try again"
                self._update_dots()

    def _handle_unlock(self):
        stored = self._get_stored_pin()
        if stored and _hash_pin(self._digits) == stored:
            self._proceed_to_app()
        else:
            self._digits = ""
            self.error_text = "Incorrect PIN"
            self._update_dots()

    # ---------------------------------------------------------------- biometric
    def try_biometric(self):
        from utils.biometric import prompt_biometric
        self.error_text = ""
        prompt_biometric(
            on_success=self._proceed_to_app,
            on_failure=self._on_biometric_failure,
        )

    def _on_biometric_failure(self, msg: str):
        # User cancelled or error - stay on PIN screen so they can type PIN
        self.error_text = "Biometric cancelled - enter PIN"

    # ---------------------------------------------------------------- helpers
    def _update_dots(self):
        filled = len(self._digits)
        for i in range(4):
            lbl = self.ids[f"dot{i}"]
            lbl.text = "*" if i < filled else "_"
            lbl.theme_text_color = "Custom"
            lbl.text_color = (0.2, 0.8, 0.5, 1) if i < filled else (0.5, 0.5, 0.5, 1)

    def _proceed_to_app(self):
        from kivy.app import App
        app = App.get_running_app()
        if app:
            app.root.transition.direction = "left"
            app.root.current = "home"

    # ---------------------------------------------------------------- storage
    @staticmethod
    def _get_store():
        from kivy.storage.jsonstore import JsonStore
        import os
        from kivy.utils import platform
        if platform == "android":
            try:
                from android.storage import app_storage_path  # type: ignore
                base = app_storage_path()
            except Exception:
                base = os.path.expanduser("~")
        else:
            base = os.path.join(os.path.expanduser("~"), ".clearspend")
        os.makedirs(base, exist_ok=True)
        return JsonStore(os.path.join(base, "settings.json"))

    @classmethod
    def _get_stored_pin(cls) -> str | None:
        store = cls._get_store()
        if store.exists("pin"):
            return store.get("pin").get("hash")
        return None

    @classmethod
    def _save_pin(cls, pin: str):
        cls._get_store().put("pin", hash=_hash_pin(pin))
