#!/usr/bin/env python3
"""Kindling — KivyMD dating assistant app."""

from __future__ import annotations

from kivy.config import Config
Config.set("graphics", "width", "360")
Config.set("graphics", "height", "800")

import os
import json
import base64
import threading
import urllib.request
import urllib.error
import random
from datetime import datetime

from kivy.clock import Clock
from kivy.core.window import Window
Window.clearcolor = (0.949, 0.949, 0.949, 1)
Window.softinput_mode = "below_target"
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDIconButton, MDRaisedButton
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.textfield import MDTextField

# ─── Constants ────────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a warm, insightful dating assistant with the expertise of a clinical counsellor and relationship therapist.

Your role:
1. Help craft genuine, engaging messages for dating apps
2. Suggest conversation topics, date ideas, and icebreakers
3. Provide in-person approach advice and openers
4. Offer therapeutic insights on patterns and emotional health
5. Track and celebrate wins; reframe setbacks constructively

Tone: Warm, non-judgmental, practical, and encouraging. Balance immediate help with long-term emotional wellbeing.
Format responses clearly. Use numbered lists or bullet points when giving multiple suggestions. Be concise but thorough."""

MOTIVATIONAL_QUOTES = [
    "The best time to put yourself out there is right now.",
    "Every rejection is a redirection toward something better.",
    "Confidence is attractive. Be yourself — boldly.",
    "You miss 100% of the shots you don't take.",
    "Growth always happens just outside your comfort zone.",
    "Someone out there is looking for exactly who you are.",
    "Be the energy you want to attract.",
    "Small steps every day lead to big changes.",
    "Your story is still being written. Make it a good one.",
    "Vulnerability is strength, not weakness.",
    "Every conversation is a new opportunity.",
    "The right person will appreciate you for exactly who you are.",
    "Invest in yourself first — everything else follows.",
    "Courage isn't the absence of fear; it's acting despite it.",
    "Dating is a skill. Skills improve with practice.",
    "Show up. The rest will follow.",
    "You are worthy of love and connection.",
    "Be curious about people. Everyone has a story.",
    "A single genuine conversation can change everything.",
    "Today is a great day to make your move.",
]

THERAPY_TIPS = [
    "Notice if you're seeking external validation. True confidence grows from within.",
    "Rejection activates the same brain regions as physical pain — be gentle with yourself.",
    "Your attachment style shapes how you date. Understanding it can transform your relationships.",
    "Are you showing your authentic self, or performing who you think they want you to be?",
    "Healthy relationships begin with a healthy relationship with yourself.",
    "Boundaries aren't walls — they're the foundation of mutual respect.",
    "Feeling nervous is normal. Vulnerability is the birthplace of real connection.",
    "Notice patterns in who you're drawn to. Do they align with your long-term wellbeing?",
    "Self-compassion after rejection is emotional intelligence, not weakness.",
    "Quality connections take time. Don't rush what needs to unfold naturally.",
    "Are you dating from abundance or scarcity? Your mindset changes everything.",
    "Know your non-negotiables — clear values help you recognize compatible partners.",
    "Your past doesn't define your dating future. Each interaction is a fresh start.",
    "Ask yourself: am I trying to impress, or am I trying to connect?",
]

# ─── Data ─────────────────────────────────────────────────────────────────────

_data_file = "dating_data.json"


def load_data():
    try:
        if os.path.exists(_data_file):
            with open(_data_file, 'r') as f:
                data = json.load(f)
            # Migrate legacy style_profile key
            if 'style_profile' in data and 'profiles' not in data:
                old = data.pop('style_profile', '') or ''
                data['profiles'] = {'Default': old}
                data['active_profile'] = 'Default'
            elif 'profiles' not in data:
                data['profiles'] = {'Default': ''}
                data['active_profile'] = 'Default'
            if 'active_profile' not in data:
                data['active_profile'] = next(iter(data['profiles']), 'Default')
            return data
    except Exception:
        pass
    return {
        "api_key": "",
        "provider": "gemini",
        "active_profile": "Default",
        "profiles": {"Default": ""},
        "conversation_history": [],
        "successes": [],
        "failures": [],
    }


def save_data(data):
    try:
        with open(_data_file, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Save error: {e}")


# ─── AI Providers ─────────────────────────────────────────────────────────────

PROVIDERS = ['gemini', 'claude', 'openai']
PROVIDER_LABELS = {'gemini': 'Gemini', 'claude': 'Claude', 'openai': 'OpenAI'}
PROVIDER_HINTS = {
    'gemini': 'Get free key at aistudio.google.com',
    'claude': 'sk-ant-api03-...',
    'openai': 'sk-...',
}


def _make_ssl_context():
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _http_post(url, headers, payload):
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30, context=_make_ssl_context()) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _call_claude(api_key, messages, system, callback):
    def run():
        try:
            result = _http_post(
                "https://api.anthropic.com/v1/messages",
                {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json.dumps({
                    "model": "claude-sonnet-4-6",
                    "max_tokens": 1500,
                    "system": system,
                    "messages": messages,
                }).encode("utf-8"),
            )
            text = result["content"][0]["text"]
            Clock.schedule_once(lambda dt: callback(text, None), 0)
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}: {e.read().decode()[:200]}"
            Clock.schedule_once(lambda dt: callback(None, err), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: callback(None, str(e)), 0)
    threading.Thread(target=run, daemon=True).start()


def _call_openai(api_key, messages, system, callback):
    def run():
        try:
            oai_msgs = [{"role": "system", "content": system}]
            for m in messages:
                content = m["content"]
                if isinstance(content, list):
                    parts = []
                    for block in content:
                        if block.get("type") == "text":
                            parts.append({"type": "text", "text": block["text"]})
                        elif block.get("type") == "image":
                            src = block["source"]
                            parts.append({"type": "image_url", "image_url": {
                                "url": f"data:{src['media_type']};base64,{src['data']}"
                            }})
                    oai_msgs.append({"role": m["role"], "content": parts})
                else:
                    oai_msgs.append({"role": m["role"], "content": content})
            result = _http_post(
                "https://api.openai.com/v1/chat/completions",
                {"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
                json.dumps({"model": "gpt-4o-mini", "max_tokens": 1500,
                            "messages": oai_msgs}).encode("utf-8"),
            )
            text = result["choices"][0]["message"]["content"]
            Clock.schedule_once(lambda dt: callback(text, None), 0)
        except urllib.error.HTTPError as e:
            err = f"HTTP {e.code}: {e.read().decode()[:200]}"
            Clock.schedule_once(lambda dt: callback(None, err), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: callback(None, str(e)), 0)
    threading.Thread(target=run, daemon=True).start()


GEMINI_MODELS = [
    ("v1",     "gemini-2.0-flash-lite"),
    ("v1",     "gemini-2.0-flash"),
    ("v1",     "gemini-1.5-flash"),
    ("v1beta", "gemini-2.5-flash"),
    ("v1beta", "gemini-2.5-pro"),
]


def _call_gemini(api_key, messages, system, callback):
    def run():
        import time
        contents = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else "user"
            content = m["content"]
            if isinstance(content, list):
                parts = []
                for block in content:
                    if block.get("type") == "text":
                        parts.append({"text": block["text"]})
                    elif block.get("type") == "image":
                        src = block["source"]
                        parts.append({"inline_data": {
                            "mime_type": src["media_type"], "data": src["data"],
                        }})
                contents.append({"role": role, "parts": parts})
            else:
                contents.append({"role": role, "parts": [{"text": content}]})

        body = json.dumps({
            "contents": contents,
            "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": {"maxOutputTokens": 1500},
        }).encode("utf-8")

        last_err = "Unknown error"
        for api_ver, model in GEMINI_MODELS:
            url = (
                f"https://generativelanguage.googleapis.com/{api_ver}/models/"
                f"{model}:generateContent?key={api_key}"
            )
            try:
                result = _http_post(url, {"content-type": "application/json"}, body)
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                Clock.schedule_once(lambda dt: callback(text, None), 0)
                return
            except urllib.error.HTTPError as e:
                code = e.code
                try:
                    body_txt = e.read().decode()[:150]
                except Exception:
                    body_txt = ""
                last_err = f"HTTP {code} ({api_ver}/{model}): {body_txt}"
                if code == 429:
                    time.sleep(3)
                elif code not in (404, 400):
                    break
            except Exception as e:
                last_err = str(e)
                break

        Clock.schedule_once(lambda dt: callback(None, last_err), 0)

    threading.Thread(target=run, daemon=True).start()


def call_ai(provider, api_key, messages, system, callback):
    if provider == 'claude':
        _call_claude(api_key, messages, system, callback)
    elif provider == 'openai':
        _call_openai(api_key, messages, system, callback)
    else:
        _call_gemini(api_key, messages, system, callback)


# ─── KV Layout ────────────────────────────────────────────────────────────────

KV = """
#:import NoTransition kivy.uix.screenmanager.NoTransition
#:import ScrollEffect kivy.effects.scroll.ScrollEffect

<MDRaisedButton>:
    elevation: 0
    _no_ripple_effect: True

<MDIconButton>:
    _no_ripple_effect: True

MDBoxLayout:
    orientation: 'vertical'
    md_bg_color: app.theme_cls.bg_normal
    canvas.before:
        Color:
            rgba: 0.949, 0.949, 0.949, 1
        Rectangle:
            pos: self.pos
            size: self.size

    ScreenManager:
        id: sm
        transition: NoTransition()

        Screen:
            name: 'chat'

            MDBoxLayout:
                orientation: 'vertical'
                md_bg_color: app.theme_cls.bg_normal
                canvas.before:
                    Color:
                        rgba: 0.949, 0.949, 0.949, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size

                MDTopAppBar:
                    title: "Kindling"
                    elevation: 0
                    right_action_items: [["cog-outline", lambda x: app.go_to_settings()]]

                ScrollView:
                    id: chat_scroll
                    do_scroll_x: False
                    effect_cls: ScrollEffect
                    canvas.before:
                        Color:
                            rgba: 0.949, 0.949, 0.949, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size

                    MDBoxLayout:
                        id: chat_box
                        orientation: 'vertical'
                        adaptive_height: True
                        padding: [dp(8), dp(8)]
                        spacing: dp(6)

                # Image attachment bar — hidden until image selected
                MDBoxLayout:
                    id: img_bar
                    size_hint_y: None
                    height: dp(0)
                    opacity: 0
                    padding: [dp(12), dp(4)]
                    spacing: dp(6)
                    md_bg_color: app.theme_cls.bg_dark

                    MDIconButton:
                        icon: 'image-outline'
                        size_hint: None, None
                        size: dp(28), dp(28)
                        theme_text_color: "Custom"
                        text_color: app.theme_cls.primary_color

                    MDLabel:
                        id: img_name_label
                        text: ''
                        font_style: "Caption"
                        adaptive_height: True
                        size_hint_x: 1
                        theme_text_color: "Secondary"

                    MDIconButton:
                        icon: 'close-circle'
                        size_hint: None, None
                        size: dp(28), dp(28)
                        theme_text_color: "Custom"
                        text_color: 0.78, 0.18, 0.18, 1
                        on_release: app.clear_image()

                # Input area
                BoxLayout:
                    size_hint_y: None
                    height: dp(46)
                    padding: [dp(4), dp(5), dp(4), dp(5)]
                    spacing: dp(2)
                    canvas.before:
                        Color:
                            rgba: 0.91, 0.91, 0.91, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size

                    MDIconButton:
                        icon: 'image-plus'
                        size_hint: None, None
                        size: dp(32), dp(36)
                        pos_hint: {"center_y": 0.5}
                        theme_text_color: "Custom"
                        text_color: app.theme_cls.primary_color
                        on_release: app.show_file_picker()

                    TextInput:
                        id: user_input
                        hint_text: 'Type here...'
                        multiline: False
                        write_tab: False
                        size_hint_x: 1
                        size_hint_y: None
                        height: dp(36)
                        pos_hint: {"center_y": 0.5}
                        font_size: '12sp'
                        background_normal: ''
                        background_active: ''
                        background_color: 1, 1, 1, 1
                        foreground_color: 0.12, 0.12, 0.12, 1
                        hint_text_color: 0.6, 0.6, 0.6, 1
                        padding: [dp(8), dp(10), dp(8), dp(8)]
                        cursor_color: 0.98, 0.34, 0.08, 1

                    MDIconButton:
                        icon: 'close-circle-outline'
                        size_hint: None, None
                        size: dp(30), dp(36)
                        pos_hint: {"center_y": 0.5}
                        theme_text_color: "Custom"
                        text_color: 0.55, 0.55, 0.55, 1
                        on_release: app.clear_chat()

                    MDIconButton:
                        id: send_btn
                        icon: 'send-circle'
                        size_hint: None, None
                        size: dp(36), dp(36)
                        pos_hint: {"center_y": 0.5}
                        theme_text_color: "Custom"
                        text_color: app.theme_cls.primary_color
                        on_release: app.send_message()


        Screen:
            name: 'icebreakers'

            MDBoxLayout:
                orientation: 'vertical'
                md_bg_color: app.theme_cls.bg_normal
                canvas.before:
                    Color:
                        rgba: 0.949, 0.949, 0.949, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size

                MDTopAppBar:
                    title: "Icebreakers & Openers"
                    elevation: 0

                MDBoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: dp(130)
                    padding: [dp(12), dp(8)]
                    spacing: dp(8)
                    md_bg_color: app.theme_cls.bg_dark

                    MDTextField:
                        id: ice_context
                        hint_text: 'e.g. "Hinge match, loves hiking & dogs"'
                        mode: 'rectangle'
                        multiline: False
                        size_hint_y: None
                        height: dp(48)
                        font_size: '11sp'

                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(40)
                        spacing: dp(6)

                        MDRaisedButton:
                            text: 'App Opener'
                            size_hint_x: 1
                            size_hint_y: None
                            height: dp(38)
                            font_size: '10sp'
                            on_release: app.generate_opener('app')

                        MDRaisedButton:
                            text: 'In-Person'
                            size_hint_x: 1
                            size_hint_y: None
                            height: dp(38)
                            font_size: '10sp'
                            md_bg_color: 0.85, 0.2, 0.25, 1
                            on_release: app.generate_opener('inperson')

                        MDRaisedButton:
                            text: 'Date Ideas'
                            size_hint_x: 1
                            size_hint_y: None
                            height: dp(38)
                            font_size: '10sp'
                            md_bg_color: 0.18, 0.6, 0.38, 1
                            on_release: app.generate_opener('date')

                ScrollView:
                    do_scroll_x: False
                    effect_cls: ScrollEffect
                    canvas.before:
                        Color:
                            rgba: 0.949, 0.949, 0.949, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size
                    MDBoxLayout:
                        id: ice_box
                        orientation: 'vertical'
                        adaptive_height: True
                        padding: [dp(12), dp(8)]
                        spacing: dp(8)
                        canvas.before:
                            Color:
                                rgba: 0.949, 0.949, 0.949, 1
                            Rectangle:
                                pos: self.pos
                                size: self.size


        Screen:
            name: 'track'

            MDBoxLayout:
                orientation: 'vertical'
                md_bg_color: app.theme_cls.bg_normal
                canvas.before:
                    Color:
                        rgba: 0.949, 0.949, 0.949, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size

                MDTopAppBar:
                    title: "Track Results"
                    elevation: 0

                MDBoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: dp(128)
                    padding: [dp(12), dp(8)]
                    spacing: dp(8)
                    md_bg_color: app.theme_cls.bg_dark

                    MDTextField:
                        id: track_note
                        hint_text: 'What happened? What did you try?'
                        mode: 'rectangle'
                        multiline: True
                        size_hint_y: None
                        height: dp(64)
                        font_size: '11sp'

                    MDBoxLayout:
                        size_hint_y: None
                        height: dp(40)
                        spacing: dp(8)

                        MDRaisedButton:
                            text: 'Log a Win!'
                            size_hint_x: 1
                            size_hint_y: None
                            height: dp(38)
                            font_size: '11sp'
                            md_bg_color: 0.18, 0.68, 0.38, 1
                            on_release: app.log_result('success')

                        MDRaisedButton:
                            text: "Didn't Work"
                            size_hint_x: 1
                            size_hint_y: None
                            height: dp(38)
                            font_size: '11sp'
                            md_bg_color: 0.85, 0.2, 0.25, 1
                            on_release: app.log_result('failure')

                MDBoxLayout:
                    size_hint_y: None
                    height: dp(38)
                    padding: [dp(16), dp(4)]

                    MDLabel:
                        id: wins_label
                        text: 'Wins: 0'
                        theme_text_color: "Custom"
                        text_color: 0.18, 0.68, 0.38, 1
                        font_size: '13sp'
                        bold: True
                        halign: 'center'

                    MDLabel:
                        id: fails_label
                        text: 'Learning: 0'
                        theme_text_color: "Custom"
                        text_color: 0.85, 0.2, 0.25, 1
                        font_size: '13sp'
                        bold: True
                        halign: 'center'

                ScrollView:
                    do_scroll_x: False
                    effect_cls: ScrollEffect
                    canvas.before:
                        Color:
                            rgba: 0.949, 0.949, 0.949, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size
                    MDBoxLayout:
                        id: track_box
                        orientation: 'vertical'
                        adaptive_height: True
                        padding: [dp(12), dp(8)]
                        spacing: dp(6)
                        canvas.before:
                            Color:
                                rgba: 0.949, 0.949, 0.949, 1
                            Rectangle:
                                pos: self.pos
                                size: self.size


        Screen:
            name: 'motivate'

            MDBoxLayout:
                orientation: 'vertical'
                md_bg_color: app.theme_cls.bg_normal
                canvas.before:
                    Color:
                        rgba: 0.949, 0.949, 0.949, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size

                MDTopAppBar:
                    title: "Get Out There!"
                    elevation: 0

                ScrollView:
                    do_scroll_x: False
                    effect_cls: ScrollEffect
                    canvas.before:
                        Color:
                            rgba: 0.949, 0.949, 0.949, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size
                    MDBoxLayout:
                        orientation: 'vertical'
                        adaptive_height: True
                        padding: [dp(14), dp(14)]
                        spacing: dp(14)

                        MDCard:
                            orientation: 'vertical'
                            size_hint_y: None
                            height: dp(140)
                            radius: [dp(12)]
                            padding: [dp(18), dp(14)]
                            md_bg_color: 1, 0.96, 0.92, 1
                            elevation: 0

                            MDLabel:
                                id: quote_label
                                text: ''
                                font_size: '12sp'
                                theme_text_color: "Custom"
                                text_color: 0.18, 0.12, 0.08, 1
                                halign: 'center'
                                valign: 'middle'
                                text_size: self.width, None

                        MDRaisedButton:
                            text: 'Shuffle Inspiration'
                            size_hint_x: 1
                            size_hint_y: None
                            height: dp(46)
                            on_release: app.shuffle_quote()

                        MDLabel:
                            text: "Therapist's Corner"
                            font_size: '15sp'
                            bold: True
                            theme_text_color: "Custom"
                            text_color: 0.78, 0.15, 0.20, 1
                            adaptive_height: True

                        MDCard:
                            orientation: 'vertical'
                            size_hint_y: None
                            height: dp(140)
                            radius: [dp(12)]
                            padding: [dp(18), dp(14)]
                            md_bg_color: 1, 0.93, 0.93, 1
                            elevation: 0

                            MDLabel:
                                id: therapy_label
                                text: ''
                                font_size: '12sp'
                                theme_text_color: "Custom"
                                text_color: 0.30, 0.10, 0.12, 1
                                halign: 'center'
                                valign: 'middle'
                                text_size: self.width, None

                        MDRaisedButton:
                            text: 'New Insight'
                            size_hint_x: 1
                            size_hint_y: None
                            height: dp(46)
                            md_bg_color: 0.78, 0.15, 0.20, 1
                            on_release: app.shuffle_therapy()


        Screen:
            name: 'settings'

            MDBoxLayout:
                orientation: 'vertical'
                md_bg_color: app.theme_cls.bg_normal
                canvas.before:
                    Color:
                        rgba: 0.949, 0.949, 0.949, 1
                    Rectangle:
                        pos: self.pos
                        size: self.size

                MDTopAppBar:
                    title: "Settings"
                    elevation: 0

                ScrollView:
                    do_scroll_x: False
                    effect_cls: ScrollEffect
                    canvas.before:
                        Color:
                            rgba: 0.949, 0.949, 0.949, 1
                        Rectangle:
                            pos: self.pos
                            size: self.size
                    MDBoxLayout:
                        orientation: 'vertical'
                        adaptive_height: True
                        padding: [dp(14), dp(12)]
                        spacing: dp(10)
                        canvas.before:
                            Color:
                                rgba: 0.949, 0.949, 0.949, 1
                            Rectangle:
                                pos: self.pos
                                size: self.size

                        MDLabel:
                            text: 'AI Provider'
                            font_style: "Subtitle2"
                            bold: True
                            adaptive_height: True
                            theme_text_color: "Secondary"

                        MDBoxLayout:
                            size_hint_y: None
                            height: dp(44)
                            spacing: dp(8)

                            MDRaisedButton:
                                id: btn_gemini
                                text: 'Gemini'
                                size_hint_x: 1
                                size_hint_y: None
                                height: dp(40)
                                font_size: '13sp'
                                on_release: app.set_provider('gemini')

                            MDRaisedButton:
                                id: btn_claude
                                text: 'Claude'
                                size_hint_x: 1
                                size_hint_y: None
                                height: dp(40)
                                font_size: '13sp'
                                on_release: app.set_provider('claude')

                            MDRaisedButton:
                                id: btn_openai
                                text: 'OpenAI'
                                size_hint_x: 1
                                size_hint_y: None
                                height: dp(40)
                                font_size: '13sp'
                                on_release: app.set_provider('openai')

                        MDLabel:
                            id: provider_note
                            text: ''
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: 0.18, 0.55, 0.30, 1
                            size_hint_y: None
                            height: dp(20)
                            adaptive_height: True

                        MDTextField:
                            id: api_key_input
                            hint_text: 'API Key'
                            mode: 'rectangle'
                            password: True
                            size_hint_y: None
                            height: dp(52)
                            font_size: '13sp'

                        BoxLayout:
                            size_hint_y: None
                            height: dp(46)
                            spacing: dp(6)

                            MDRaisedButton:
                                text: 'Save & Connect'
                                size_hint_x: 1
                                size_hint_y: None
                                height: dp(46)
                                on_release: app.save_and_connect()

                            MDIconButton:
                                icon: 'content-save-outline'
                                size_hint: None, None
                                size: dp(46), dp(46)
                                theme_text_color: "Custom"
                                text_color: app.theme_cls.primary_color
                                on_release: app.save_local()

                        MDLabel:
                            id: settings_status
                            text: ''
                            font_style: "Caption"
                            theme_text_color: "Custom"
                            text_color: 0.18, 0.60, 0.30, 1
                            size_hint_y: None
                            height: dp(22)

                        BoxLayout:
                            size_hint_y: None
                            height: dp(38)

                            MDLabel:
                                text: 'Style Profiles'
                                font_style: "Subtitle2"
                                bold: True
                                adaptive_height: True
                                theme_text_color: "Custom"
                                text_color: app.theme_cls.primary_color

                            MDIconButton:
                                icon: 'plus-circle-outline'
                                size_hint: None, None
                                size: dp(38), dp(38)
                                theme_text_color: "Custom"
                                text_color: 0.18, 0.68, 0.38, 1
                                on_release: app.create_profile_dialog()

                        MDBoxLayout:
                            id: profile_cards_box
                            orientation: 'vertical'
                            adaptive_height: True
                            spacing: dp(8)
                            canvas.before:
                                Color:
                                    rgba: 0.949, 0.949, 0.949, 1
                                Rectangle:
                                    pos: self.pos
                                    size: self.size

                        # Hidden text field — used by edit dialogs
                        TextInput:
                            id: style_input
                            size_hint_y: None
                            height: dp(0)
                            opacity: 0
    # Custom bottom nav bar
    BoxLayout:
        size_hint_y: None
        height: dp(54)
        spacing: 0
        canvas.before:
            Color:
                rgba: 0.16, 0.10, 0.07, 1
            Rectangle:
                pos: self.pos
                size: self.size

        MDIconButton:
            id: nav_chat
            icon: 'chat-outline'
            size_hint_x: 1
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 1
            on_release: app.switch_tab('chat')

        MDIconButton:
            id: nav_ice
            icon: 'lightning-bolt-outline'
            size_hint_x: 1
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 0.45
            on_release: app.switch_tab('icebreakers')

        MDIconButton:
            id: nav_track
            icon: 'chart-line'
            size_hint_x: 1
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 0.45
            on_release: app.switch_tab('track')

        MDIconButton:
            id: nav_motivate
            icon: 'fire'
            size_hint_x: 1
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 0.45
            on_release: app.switch_tab('motivate')

        MDIconButton:
            id: nav_settings
            icon: 'cog-outline'
            size_hint_x: 1
            theme_text_color: "Custom"
            text_color: 1, 1, 1, 0.45
            on_release: app.switch_tab('settings')

"""


# ─── App Class ────────────────────────────────────────────────────────────────

class KindlingApp(MDApp):

    def build(self):
        self.theme_cls.theme_style   = "Light"
        self.theme_cls.primary_palette = "DeepOrange"

        global _data_file
        _data_file = os.path.join(self.user_data_dir, "dating_data.json")
        self.data = load_data()
        self.current_image_path = None
        self._typing_row = None
        self._pending_content = []
        self._pending_display = ""

        root = Builder.load_string(KV)
        ids = root.ids

        # Cache widget refs
        self._chat_box      = ids.chat_box
        self._chat_scroll   = ids.chat_scroll
        self._user_input    = ids.user_input
        self._img_bar       = ids.img_bar
        self._img_name      = ids.img_name_label
        self._send_btn      = ids.send_btn
        self._ice_context   = ids.ice_context
        self._ice_box       = ids.ice_box
        self._track_note    = ids.track_note
        self._track_box     = ids.track_box
        self._wins_label    = ids.wins_label
        self._fails_label   = ids.fails_label
        self._quote_label   = ids.quote_label
        self._therapy_label = ids.therapy_label
        self._api_key_input     = ids.api_key_input
        try:
            self._style_input = ids.style_input
        except Exception:
            self._style_input = None
        self._profile_cards_box = ids.profile_cards_box
        self._settings_status   = ids.settings_status
        self._provider_note     = ids.provider_note
        self._sm  = ids.sm
        self._nav_btns = {
            'chat': ids.nav_chat, 'icebreakers': ids.nav_ice,
            'track': ids.nav_track, 'motivate': ids.nav_motivate,
            'settings': ids.nav_settings,
        }

        self._provider_btns = {
            'gemini': ids.btn_gemini,
            'claude': ids.btn_claude,
            'openai': ids.btn_openai,
        }

        # Restore saved settings
        if self.data.get('api_key'):
            self._api_key_input.text = self.data['api_key']
        # Load active profile into the text field
        _active   = self.data.get('active_profile', '')
        _profiles = self.data.get('profiles', {})
        if self._style_input and _active in _profiles:
            self._style_input.text = _profiles[_active]
        elif self._style_input and _profiles:
            _first = next(iter(_profiles))
            self.data['active_profile'] = _first
            self._style_input.text = _profiles[_first]

        saved_provider = self.data.get('provider', 'gemini')
        self.set_provider(saved_provider, save=False)
        self.refresh_profiles_ui()

        self.shuffle_quote()
        self.shuffle_therapy()
        self.refresh_track_display()

        self._add_bubble('assistant',
            "Hi! I'm Kindling, your dating assistant.\n\n"
            "I can help with message ideas, conversation tips, icebreakers "
            "for apps or in-person, and date suggestions.\n\n"
            "Tap the cog to choose your AI provider and add an API key "
            "(Gemini has a free tier), then ask me anything!")

        return root

    # ── Navigation ─────────────────────────────────────────────────────────────

    def go_to_settings(self):
        self.switch_tab('settings')

    def switch_tab(self, name: str):
        self._sm.current = name
        for n, btn in self._nav_btns.items():
            btn.text_color = (1, 1, 1, 1) if n == name else (1, 1, 1, 0.45)

    # ── Provider ───────────────────────────────────────────────────────────────

    def set_provider(self, provider, save=True):
        self.data['provider'] = provider
        notes = {
            'gemini': 'Free tier — get key at aistudio.google.com',
            'claude': 'Paid API — console.anthropic.com',
            'openai': 'Paid API — platform.openai.com',
        }
        active_bg   = self.theme_cls.primary_color
        inactive_bg = (0.88, 0.88, 0.88, 1)
        for p, btn in self._provider_btns.items():
            btn.md_bg_color = active_bg if p == provider else inactive_bg
        self._provider_note.text = notes.get(provider, '')
        self._api_key_input.hint_text = PROVIDER_HINTS.get(provider, '')
        if save:
            save_data(self.data)

    # ── Chat bubbles ───────────────────────────────────────────────────────────

    def _add_bubble(self, role: str, text: str) -> MDBoxLayout:
        is_user = (role == 'user')

        if is_user:
            card_bg   = self.theme_cls.primary_color
            txt_color = (1, 1, 1, 1)
            name_col  = (1, 1, 1, 0.75)
            radius    = [dp(12), dp(4), dp(12), dp(12)]
            align     = 'right'
        else:
            card_bg   = (0.93, 0.93, 0.94, 1)
            txt_color = (0.12, 0.12, 0.14, 1)
            name_col  = (0.50, 0.50, 0.55, 1)
            radius    = [dp(4), dp(12), dp(12), dp(12)]
            align     = 'left'

        PAD_H  = dp(12) * 2   # card left+right padding
        PAD_V  = dp(8)  * 2   # card top+bottom padding
        NAME_H = dp(16)
        SP     = dp(2)

        bubble_w = (Window.width - dp(16)) * 0.85
        text_w   = bubble_w - PAD_H

        name_lbl = MDLabel(
            text="You" if is_user else "Assistant",
            size_hint_y=None, height=NAME_H,
            font_style="Caption", bold=True,
            halign=align,
            theme_text_color="Custom", text_color=name_col,
        )
        name_lbl.text_size = (text_w, None)

        msg_lbl = MDLabel(
            text=text,
            size_hint_y=None, height=dp(40),
            font_size=dp(10) if not is_user else dp(12),
            halign=align, valign="top",
            theme_text_color="Custom", text_color=txt_color,
        )
        msg_lbl.text_size = (text_w, None)

        card = MDCard(
            orientation="vertical",
            padding=[dp(12), dp(8)], spacing=SP,
            radius=radius,
            size_hint_y=None, height=dp(70),
            size_hint_x=0.85,
            md_bg_color=card_bg,
            elevation=0,
        )
        card.add_widget(name_lbl)
        card.add_widget(msg_lbl)

        row = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None, height=dp(76),
            padding=[0, dp(3)],
        )

        def _apply_heights(ts):
            if ts[1] <= 0:
                return
            msg_lbl.height = ts[1]
            card.height    = NAME_H + SP + ts[1] + PAD_V
            row.height     = card.height + dp(6)

        def _on_tex(inst, ts):
            _apply_heights(ts)

        msg_lbl.bind(texture_size=_on_tex)
        Clock.schedule_once(lambda dt: _apply_heights(msg_lbl.texture_size), 0.05)
        Clock.schedule_once(lambda dt: _apply_heights(msg_lbl.texture_size), 0.3)

        spacer = Widget(size_hint_x=0.15)
        if is_user:
            row.add_widget(spacer)
            row.add_widget(card)
        else:
            row.add_widget(card)
            row.add_widget(spacer)

        self._chat_box.add_widget(row)
        Clock.schedule_once(lambda dt: setattr(self._chat_scroll, 'scroll_y', 0), 0.15)
        return row

    def _add_typing_indicator(self) -> MDBoxLayout:
        card = MDCard(
            orientation='horizontal',
            size_hint_y=None, height=dp(36),
            size_hint_x=0.5,
            radius=[dp(4), dp(12), dp(12), dp(12)],
            md_bg_color=(0.93, 0.93, 0.94, 1),
            padding=[dp(12), dp(8)],
            elevation=0,
        )
        card.add_widget(MDLabel(
            text="typing...",
            font_style="Caption",
            theme_text_color="Hint",
            adaptive_height=True,
        ))

        row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(42),
                          padding=[0, dp(3)])
        row.add_widget(card)
        row.add_widget(Widget(size_hint_x=0.5))

        self._chat_box.add_widget(row)
        Clock.schedule_once(lambda dt: setattr(self._chat_scroll, 'scroll_y', 0), 0.1)
        return row

    def _remove_typing_indicator(self):
        if self._typing_row:
            try:
                self._chat_box.remove_widget(self._typing_row)
            except Exception:
                pass
            self._typing_row = None

    def _add_error_bubble(self, error_text: str):
        friendly = self._parse_error(error_text)

        PAD_H = dp(12) * 2
        PAD_V = dp(8)  * 2
        SP    = dp(4)
        BTN_H = dp(32)

        bubble_w = (Window.width - dp(16)) * 0.85
        text_w   = bubble_w - PAD_H

        msg_lbl = MDLabel(
            text=friendly,
            size_hint_y=None, height=dp(36),
            font_style="Body2",
            theme_text_color="Custom",
            text_color=(0.68, 0.12, 0.12, 1),
            valign="top",
        )
        msg_lbl.text_size = (text_w, None)

        retry_btn = MDFlatButton(
            text="Retry",
            size_hint_y=None, height=BTN_H,
            theme_text_color="Custom",
            text_color=self.theme_cls.primary_color,
        )

        inner = MDBoxLayout(orientation='vertical', size_hint_y=None,
                            height=dp(70), spacing=SP)
        inner.add_widget(msg_lbl)
        inner.add_widget(retry_btn)

        card = MDCard(
            orientation='vertical',
            size_hint_y=None, height=dp(78),
            size_hint_x=0.85,
            radius=[dp(4), dp(12), dp(12), dp(12)],
            md_bg_color=(0.99, 0.92, 0.92, 1),
            padding=[dp(12), dp(8)],
            elevation=0,
        )
        card.add_widget(inner)

        row = MDBoxLayout(orientation='horizontal', size_hint_y=None, height=dp(84),
                          padding=[0, dp(3)])
        row.add_widget(card)
        row.add_widget(Widget(size_hint_x=0.15))

        def _apply_err_heights(ts):
            if ts[1] <= 0:
                return
            msg_lbl.height = ts[1]
            inner.height   = ts[1] + SP + BTN_H
            card.height    = ts[1] + SP + BTN_H + PAD_V
            row.height     = card.height + dp(6)

        msg_lbl.bind(texture_size=lambda inst, ts: _apply_err_heights(ts))
        Clock.schedule_once(lambda dt: _apply_err_heights(msg_lbl.texture_size), 0.05)
        Clock.schedule_once(lambda dt: _apply_err_heights(msg_lbl.texture_size), 0.3)

        # Capture retry state at error time
        pending_content = list(self._pending_content)
        pending_display = self._pending_display

        def on_retry(_):
            self._chat_box.remove_widget(row)
            self._send_btn.disabled = True
            self._send_btn.icon = 'timer-sand'
            self._do_send(pending_content, pending_display)

        retry_btn.bind(on_release=on_retry)

        self._chat_box.add_widget(row)
        Clock.schedule_once(lambda dt: setattr(self._chat_scroll, 'scroll_y', 0), 0.15)

    @staticmethod
    def _parse_error(error_text: str) -> str:
        e = str(error_text).lower()
        if '401' in e or '403' in e or 'unauthorized' in e or 'invalid' in e:
            return "Invalid API key. Please check Settings."
        if '429' in e or 'rate' in e or 'quota' in e:
            return "Rate limit reached. Please wait a moment and retry."
        if any(c in e for c in ('500', '502', '503')):
            return "Service error. Please try again."
        if 'timeout' in e or 'timed out' in e or 'connection' in e:
            return "Connection failed. Check your internet and retry."
        return f"Error: {error_text[:100]}"

    # ── Send flow ──────────────────────────────────────────────────────────────

    def send_message(self):
        api_key  = self.data.get('api_key', '').strip()
        provider = self.data.get('provider', 'gemini')

        if not api_key:
            pname = PROVIDER_LABELS.get(provider, provider)
            self._show_popup("API Key Required",
                             f"Please add your {pname} API key in Settings first.")
            return

        text      = self._user_input.text.strip()
        img_path  = self.current_image_path

        if not text and not img_path:
            return

        # Build content blocks (Claude format; other providers convert on the fly)
        content = []
        if img_path:
            try:
                with open(img_path, 'rb') as f:
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                ext   = os.path.splitext(img_path)[1].lower()
                mtype = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                         '.png': 'image/png',  '.gif': 'image/gif',
                         '.webp': 'image/webp'}.get(ext, 'image/jpeg')
                content.append({"type": "image",
                                 "source": {"type": "base64",
                                            "media_type": mtype, "data": b64}})
            except Exception as exc:
                self._show_popup("Image Error", str(exc))

        # Display text shown in UI
        if img_path and text:
            display_text = f"[Screenshot]\n{text}"
        elif img_path:
            display_text = "[Screenshot attached — please advise]"
        else:
            display_text = text

        # Prepend style profile on first message
        history = list(self.data.get('conversation_history', []))
        _ap    = self.data.get('active_profile', '')
        style  = self.data.get('profiles', {}).get(_ap, '').strip()
        msg_text = display_text
        if style and not history:
            msg_text = f"[About me: {style}]\n\n{display_text}"
        content.append({"type": "text", "text": msg_text})

        self._add_bubble('user', display_text)
        self._user_input.text = ''
        self.clear_image()

        self._pending_content = content
        self._pending_display = display_text

        self._send_btn.disabled = True
        self._send_btn.icon = 'timer-sand'
        self._do_send(content, display_text)

    def _do_send(self, content: list, display_text: str):
        api_key  = self.data.get('api_key', '').strip()
        provider = self.data.get('provider', 'gemini')

        history  = list(self.data.get('conversation_history', []))
        messages = history + [{"role": "user", "content": content}]

        self._typing_row = self._add_typing_indicator()

        def on_resp(resp_text, error):
            self._remove_typing_indicator()
            self._send_btn.disabled = False
            self._send_btn.icon = 'send-circle'

            if error:
                self._add_error_bubble(error)
                return

            self._add_bubble('assistant', resp_text)

            hist = self.data.get('conversation_history', [])
            hist.append({"role": "user",      "content": display_text})
            hist.append({"role": "assistant", "content": resp_text})
            if len(hist) > 20:
                hist = hist[-20:]
            self.data['conversation_history'] = hist
            save_data(self.data)

        call_ai(provider, api_key, messages, SYSTEM_PROMPT, on_resp)

    def clear_chat(self):
        self._chat_box.clear_widgets()
        self.data['conversation_history'] = []
        save_data(self.data)
        self._typing_row = None
        self._add_bubble('assistant', "Chat cleared. What would you like help with?")

    # ── Image ──────────────────────────────────────────────────────────────────

    def clear_image(self):
        self.current_image_path = None
        self._img_bar.height  = dp(0)
        self._img_bar.opacity = 0
        self._img_name.text   = ''

    def show_file_picker(self):
        # Try Android native gallery picker first (works on Android 11+)
        try:
            from jnius import autoclass
            from android import activity, mActivity

            Intent = autoclass('android.content.Intent')
            intent = Intent(Intent.ACTION_GET_CONTENT)
            intent.setType('image/*')
            intent.addCategory('android.intent.category.OPENABLE')

            def on_result(request_code, result_code, data):
                activity.unbind(on_activity_result=on_result)
                if request_code == 42 and result_code == -1 and data:
                    uri = data.getData()
                    if uri:
                        Clock.schedule_once(lambda dt: self._load_image_uri(uri), 0)

            activity.bind(on_activity_result=on_result)
            mActivity.startActivityForResult(intent, 42)
            return
        except Exception:
            pass  # Not on Android — fall through to FileChooserListView

        from kivy.graphics import Color as GColor, Rectangle as GRect
        from kivy.uix.label import Label

        candidates = [
            '/storage/emulated/0/DCIM/Camera',
            '/storage/emulated/0/Pictures',
            '/storage/emulated/0/Download',
            '/storage/emulated/0',
            os.path.expanduser('~'),
            self.user_data_dir,
            '/',
        ]
        start = '/'
        for c in candidates:
            try:
                if os.path.isdir(c) and os.listdir(c) is not None:
                    start = c
                    break
            except Exception:
                continue

        try:
            chooser = FileChooserListView(
                path=start,
                filters=['*.jpg', '*.jpeg', '*.png', '*.webp', '*.gif'],
            )
        except Exception as e:
            self._show_popup("Gallery Error", f"Could not open file browser: {e}")
            return

        # ── Themed header bar (matches MDTopAppBar style) ─────────────────────
        header = BoxLayout(size_hint_y=None, height=dp(48),
                           padding=[dp(16), 0, dp(8), 0])
        with header.canvas.before:
            GColor(0.16, 0.10, 0.07, 1)
            header_bg = GRect(pos=header.pos, size=header.size)
        header.bind(pos=lambda w, _: setattr(header_bg, 'pos', w.pos))
        header.bind(size=lambda w, _: setattr(header_bg, 'size', w.size))

        header_lbl = Label(
            text='Select Screenshot',
            color=(1, 1, 1, 1),
            font_size='15sp',
            halign='left', valign='middle',
            size_hint_x=1,
        )
        header_lbl.bind(size=lambda w, _: setattr(w, 'text_size', w.size))

        close_btn = Button(
            text='✕',
            size_hint=(None, None), size=(dp(40), dp(40)),
            background_normal='', background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 0.7),
            font_size='16sp',
        )
        header.add_widget(header_lbl)
        header.add_widget(close_btn)

        # ── File chooser area (light bg matching app) ─────────────────────────
        chooser_wrap = BoxLayout()
        with chooser_wrap.canvas.before:
            GColor(0.949, 0.949, 0.949, 1)
            cw_bg = GRect(pos=chooser_wrap.pos, size=chooser_wrap.size)
        chooser_wrap.bind(pos=lambda w, _: setattr(cw_bg, 'pos', w.pos))
        chooser_wrap.bind(size=lambda w, _: setattr(cw_bg, 'size', w.size))
        chooser_wrap.add_widget(chooser)

        # ── Button row ────────────────────────────────────────────────────────
        btn_row = BoxLayout(size_hint_y=None, height=dp(52),
                            spacing=dp(8), padding=[dp(10), dp(7)])
        with btn_row.canvas.before:
            GColor(0.91, 0.91, 0.91, 1)
            br_bg = GRect(pos=btn_row.pos, size=btn_row.size)
        btn_row.bind(pos=lambda w, _: setattr(br_bg, 'pos', w.pos))
        btn_row.bind(size=lambda w, _: setattr(br_bg, 'size', w.size))

        can_btn = Button(
            text='Cancel',
            size_hint_x=0.38,
            background_normal='', background_active='',
            background_color=(0.78, 0.78, 0.78, 1),
            color=(0.20, 0.20, 0.20, 1),
            font_size='14sp',
        )
        sel_btn = Button(
            text='Select',
            size_hint_x=0.62,
            background_normal='', background_active='',
            background_color=(0.98, 0.34, 0.08, 1),
            color=(1, 1, 1, 1),
            font_size='14sp',
            bold=True,
        )
        btn_row.add_widget(can_btn)
        btn_row.add_widget(sel_btn)

        content = BoxLayout(orientation='vertical')
        content.add_widget(header)
        content.add_widget(chooser_wrap)
        content.add_widget(btn_row)

        popup = Popup(
            title='', title_size='0sp',
            separator_height=0,
            content=content,
            size_hint=(0.95, 0.84),
            background_color=(0.16, 0.10, 0.07, 1),
        )

        def on_select(_):
            if chooser.selection:
                path  = chooser.selection[0]
                fname = os.path.basename(path)
                self.current_image_path = path
                self._img_name.text     = (fname[:26] + '…') if len(fname) > 26 else fname
                self._img_bar.height    = dp(36)
                self._img_bar.opacity   = 1
            popup.dismiss()

        sel_btn.bind(on_press=on_select)
        can_btn.bind(on_press=lambda _: popup.dismiss())
        close_btn.bind(on_press=lambda _: popup.dismiss())
        popup.open()

    def _load_image_uri(self, uri):
        def run():
            try:
                from jnius import autoclass
                from android import mActivity

                cr     = mActivity.getContentResolver()
                tmp    = os.path.join(self.user_data_dir, '_picked_img.jpg')

                # Get display name
                fname = 'image.jpg'
                try:
                    OpenableColumns = autoclass('android.provider.OpenableColumns')
                    cursor = cr.query(uri, None, None, None, None)
                    if cursor and cursor.moveToFirst():
                        col = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                        if col >= 0:
                            fname = cursor.getString(col)
                        cursor.close()
                except Exception:
                    pass

                # Copy stream to file using Android FileUtils (API 26+)
                FileUtils       = autoclass('android.os.FileUtils')
                FileOutputStream = autoclass('java.io.FileOutputStream')
                in_stream  = cr.openInputStream(uri)
                out_stream = FileOutputStream(tmp)
                FileUtils.copy(in_stream, out_stream)
                in_stream.close()
                out_stream.close()

                short = (fname[:26] + '\u2026') if len(fname) > 26 else fname

                def _apply(dt):
                    self.current_image_path = tmp
                    self._img_name.text     = short
                    self._img_bar.height    = dp(36)
                    self._img_bar.opacity   = 1
                Clock.schedule_once(_apply, 0)

            except Exception as e:
                Clock.schedule_once(
                    lambda dt: self._show_popup("Image Error", str(e)[:120]), 0)

        threading.Thread(target=run, daemon=True).start()

    # ── Icebreakers ────────────────────────────────────────────────────────────

    def generate_opener(self, kind: str):
        api_key  = self.data.get('api_key', '').strip()
        provider = self.data.get('provider', 'gemini')

        if not api_key:
            pname = PROVIDER_LABELS.get(provider, provider)
            self._show_popup("API Key Required",
                             f"Please add your {pname} API key in Settings first.")
            return

        ctx = self._ice_context.text.strip() or "No specific context provided."

        prompts = {
            'app': (
                f"Generate 3 creative, genuine opening messages for a dating app. "
                f"Context: {ctx}\n"
                "Make them conversational and authentic — not cheesy. "
                "Vary the tone (playful / thoughtful / witty)."
            ),
            'inperson': (
                f"Generate 3 natural in-person icebreakers. Context: {ctx}\n"
                "Keep them casual, confident, and easy to deliver naturally. "
                "Avoid anything corny. Include a brief delivery note for each."
            ),
            'date': (
                f"Suggest 5 creative date ideas. Context: {ctx}\n"
                "Mix low-key and more adventurous options. "
                "Include free/cheap options alongside others."
            ),
        }

        self._ice_box.clear_widgets()

        # Loading card
        loading = MDCard(orientation='horizontal', size_hint_y=None, height=dp(46),
                         radius=[dp(10)], md_bg_color=self.theme_cls.bg_dark,
                         padding=[dp(14), dp(12)], elevation=0)
        loading.add_widget(MDLabel(text="Generating ideas...", font_style="Body2",
                                   theme_text_color="Hint", adaptive_height=True))
        self._ice_box.add_widget(loading)

        messages = [{"role": "user", "content": prompts[kind]}]

        def on_resp(resp_text, error):
            self._ice_box.clear_widgets()
            body      = error if error else resp_text
            is_error  = bool(error)
            txt_color = (0.68, 0.12, 0.12, 1) if is_error else (0.12, 0.12, 0.14, 1)

            lbl = MDLabel(
                text=body,
                size_hint_y=None, height=dp(80),
                font_size=dp(11),
                theme_text_color="Custom", text_color=txt_color,
                valign="top",
            )
            lbl.text_size = (Window.width - dp(52), None)

            card = MDCard(orientation='vertical', size_hint_y=None, height=dp(100),
                          radius=[dp(10)], md_bg_color=self.theme_cls.bg_dark,
                          padding=[dp(14), dp(12)], elevation=0)

            def _apply_ice_heights(ts):
                if ts[1] <= 0:
                    return
                lbl.height  = ts[1]
                card.height = ts[1] + dp(24)
            lbl.bind(texture_size=lambda inst, ts: _apply_ice_heights(ts))
            Clock.schedule_once(lambda dt: _apply_ice_heights(lbl.texture_size), 0.05)
            Clock.schedule_once(lambda dt: _apply_ice_heights(lbl.texture_size), 0.3)

            card.add_widget(lbl)
            self._ice_box.add_widget(card)

        call_ai(provider, api_key, messages, SYSTEM_PROMPT, on_resp)

    # ── Track ──────────────────────────────────────────────────────────────────

    def log_result(self, kind: str):
        note  = self._track_note.text.strip()
        entry = {"note": note, "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
        key   = 'successes' if kind == 'success' else 'failures'
        self.data.setdefault(key, []).append(entry)
        save_data(self.data)
        self._track_note.text = ''
        self.refresh_track_display()
        label = "Win logged!" if kind == 'success' else "Logged as a learning."
        self._show_toast(label)

    def refresh_track_display(self):
        wins  = len(self.data.get('successes', []))
        fails = len(self.data.get('failures', []))

        if hasattr(self, '_wins_label'):
            self._wins_label.text  = f'Wins: {wins}'
            self._fails_label.text = f'Learning: {fails}'

        if not hasattr(self, '_track_box'):
            return

        self._track_box.clear_widgets()

        all_entries = (
            [('W', e) for e in self.data.get('successes', [])] +
            [('L', e) for e in self.data.get('failures', [])]
        )
        all_entries.sort(key=lambda x: x[1].get('date', ''), reverse=True)

        for idx, (tag, entry) in enumerate(all_entries[:30]):
            is_win    = tag == 'W'
            card_bg   = (0.90, 0.98, 0.92, 1) if is_win else (0.98, 0.91, 0.91, 1)
            txt_color = (0.10, 0.50, 0.24, 1) if is_win else (0.62, 0.12, 0.16, 1)
            marker    = "\u2022 Win" if is_win else "\u2022 Miss"
            note_text = entry.get('note') or '(no note)'


            _key = 'successes' if is_win else 'failures'

            def _find_idx(key=_key, e=entry):
                for i, x in enumerate(self.data.get(key, [])):
                    if x.get('date') == e.get('date') and x.get('note') == e.get('note'):
                        return i
                return -1

            def _on_edit(b, key=_key, e=entry):
                self._edit_track_entry(key, e)
            def _on_del(b, key=_key, e=entry):
                fi = _find_idx(key, e)
                if fi >= 0:
                    self.data.setdefault(key, []).pop(fi)
                    save_data(self.data)
                    self.refresh_track_display()

            ICON_SZ = dp(28)
            edit_icon = MDIconButton(
                icon='pencil-outline',
                size_hint=(None, None), size=(ICON_SZ, ICON_SZ),
                theme_text_color="Custom", text_color=txt_color,
            )
            del_icon = MDIconButton(
                icon='trash-can-outline',
                size_hint=(None, None), size=(ICON_SZ, ICON_SZ),
                theme_text_color="Custom", text_color=(0.78, 0.15, 0.20, 1),
            )
            edit_icon.bind(on_release=_on_edit)
            del_icon.bind(on_release=_on_del)

            # Single horizontal row: text label + icons on the right
            row = MDBoxLayout(orientation='horizontal', size_hint_y=None,
                              height=dp(36), spacing=dp(4), padding=[0, dp(2)])

            lbl = MDLabel(
                text=f"{marker}  {entry.get('date', '')}  —  {note_text}",
                size_hint_x=1,
                font_size='11sp',
                theme_text_color="Custom", text_color=txt_color,
                valign="middle",
            )
            lbl.text_size = (Window.width - dp(120), None)

            row.add_widget(lbl)
            row.add_widget(edit_icon)
            row.add_widget(del_icon)

            card = MDCard(orientation='vertical', size_hint_y=None, height=dp(44),
                          radius=[dp(8)], md_bg_color=card_bg,
                          padding=[dp(10), dp(6)], elevation=0)
            card.add_widget(row)
            self._track_box.add_widget(card)

    def _edit_track_entry(self, key, entry, body_lbl=None):
        from kivymd.uix.dialog import MDDialog
        field = MDTextField(
            text=entry.get('note', ''),
            hint_text='What happened?',
            mode='rectangle',
            multiline=True,
            size_hint_y=None, height=dp(90), font_size='13sp',
        )
        content = MDBoxLayout(orientation='vertical', size_hint_y=None, height=dp(110),
                              padding=[dp(24), dp(8), dp(24), dp(8)])
        content.add_widget(field)
        dlg = [None]
        dlg[0] = MDDialog(
            title="Edit entry", type="custom", content_cls=content,
            buttons=[
                MDFlatButton(text="Cancel", theme_text_color="Custom",
                             text_color=(0.55, 0.55, 0.55, 1),
                             on_release=lambda *_: dlg[0].dismiss()),
                MDRaisedButton(text="Save", on_release=lambda *_: self._save_track_edit(
                    key, entry, field.text.strip(), dlg[0])),
            ],
        )
        dlg[0].open()

    def _save_track_edit(self, key, entry, new_note, dlg):
        dlg.dismiss()
        lst = self.data.get(key, [])
        for e in lst:
            if e.get('date') == entry.get('date') and e.get('note') == entry.get('note'):
                e['note'] = new_note
                break
        save_data(self.data)
        self.refresh_track_display()

    # ── Motivation ─────────────────────────────────────────────────────────────

    def shuffle_quote(self):
        if hasattr(self, '_quote_label'):
            self._quote_label.text = random.choice(MOTIVATIONAL_QUOTES)

    def shuffle_therapy(self):
        if hasattr(self, '_therapy_label'):
            self._therapy_label.text = random.choice(THERAPY_TIPS)

    # ── Settings ───────────────────────────────────────────────────────────────

    def save_and_connect(self):
        key = self._api_key_input.text.strip()
        if not key:
            self._settings_status.text = "Enter an API key first."
            return
        self.data['api_key'] = key
        save_data(self.data)
        self._settings_status.text = "Testing connection..."
        provider = self.data.get('provider', 'gemini')

        def on_result(ok, err):
            if ok:
                self._settings_status.text = "Connected (OK)"
            else:
                self._settings_status.text = f"Failed: {self._parse_error(err or '')}"
            Clock.schedule_once(lambda dt: setattr(self._settings_status, 'text', ''), 4)

        self._test_connection(provider, key, on_result)

    def save_local(self):
        key = self._api_key_input.text.strip()
        self.data['api_key'] = key
        save_data(self.data)
        self._settings_status.text = "Saved." if key else "Key cleared."
        Clock.schedule_once(lambda dt: setattr(self._settings_status, 'text', ''), 2)

    def _test_connection(self, provider, api_key, callback):
        def run():
            try:
                ctx = _make_ssl_context()
                if provider == 'gemini':
                    url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
                    req = urllib.request.Request(url)
                elif provider == 'claude':
                    req = urllib.request.Request(
                        "https://api.anthropic.com/v1/models",
                        headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                    )
                else:
                    req = urllib.request.Request(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                with urllib.request.urlopen(req, timeout=10, context=ctx):
                    pass
                Clock.schedule_once(lambda dt: callback(True, None), 0)
            except urllib.error.HTTPError as e:
                Clock.schedule_once(lambda dt: callback(False, f"HTTP {e.code}"), 0)
            except Exception as e:
                Clock.schedule_once(lambda dt: callback(False, str(e)[:80]), 0)
        threading.Thread(target=run, daemon=True).start()

    # ── Profile shared helpers ─────────────────────────────────────────────────

    def _active_profile_name(self):
        return self.data.get('active_profile', '')

    def create_profile_dialog(self):
        from kivymd.uix.dialog import MDDialog
        name_field = MDTextField(
            hint_text='e.g. Casual, Serious, Adventurous...',
            mode='rectangle',
            size_hint_y=1,
            font_size='13sp',
        )
        content = MDBoxLayout(
            orientation='vertical',
            size_hint_y=None, height=dp(72),
            padding=[0, dp(4)],
        )
        content.add_widget(name_field)

        dlg = [None]
        dlg[0] = MDDialog(
            title="New Profile",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="Cancel",
                    theme_text_color="Custom",
                    text_color=(0.55, 0.55, 0.55, 1),
                    on_release=lambda *_: dlg[0].dismiss(),
                ),
                MDRaisedButton(
                    text="Create",
                    on_release=lambda *_: self._do_create_profile(
                        name_field.text.strip(), dlg[0]
                    ),
                ),
            ],
        )
        dlg[0].open()

    def _do_create_profile(self, name, dlg):
        if not name:
            return
        dlg.dismiss()
        profiles = self.data.setdefault('profiles', {})
        profiles[name] = ''
        self.data['active_profile'] = name
        save_data(self.data)
        if self._style_input:
            self._style_input.text = ''
        self.refresh_profiles_ui()

    def switch_profile(self, name):
        self.data['active_profile'] = name
        bio = self.data.get('profiles', {}).get(name, '')
        if self._style_input:
            self._style_input.text = bio
        self.refresh_profiles_ui()

    def delete_profile(self):
        active   = self._active_profile_name()
        profiles = self.data.get('profiles', {})
        if len(profiles) <= 1:
            self._settings_status.text = "Can't delete the last profile."
            Clock.schedule_once(lambda dt: setattr(self._settings_status, 'text', ''), 2)
            return
        profiles.pop(active, None)
        first = next(iter(profiles))
        self.data['active_profile'] = first
        if self._style_input:
            self._style_input.text = profiles[first]
        save_data(self.data)
        self.refresh_profiles_ui()

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _show_toast(self, msg: str):
        from kivy.uix.label import Label as KvLabel
        from kivy.core.window import Window as KvWin
        from kivy.graphics import Color as GC, RoundedRectangle as GRR
        lbl = KvLabel(
            text=msg,
            size_hint=(None, None),
            font_size='13sp',
            color=(1, 1, 1, 1),
            padding=(dp(16), dp(8)),
        )
        lbl.texture_update()
        lbl.size = (lbl.texture_size[0] + dp(32), dp(36))
        lbl.pos  = ((KvWin.width - lbl.width) / 2, dp(80))
        with lbl.canvas.before:
            GC(0.12, 0.12, 0.12, 0.88)
            GRR(pos=lbl.pos, size=lbl.size, radius=[dp(18)])
        KvWin.add_widget(lbl)
        Clock.schedule_once(lambda dt: KvWin.remove_widget(lbl), 2.0)

    def _show_popup(self, title: str, msg: str):
        from kivymd.uix.dialog import MDDialog
        dlg = MDDialog(
            title=title,
            text=msg,
            buttons=[MDFlatButton(
                text="OK",
                theme_text_color="Custom",
                text_color=self.theme_cls.primary_color,
                on_release=lambda *_: dlg.dismiss(),
            )],
        )
        dlg.open()


    def refresh_profiles_ui(self):
        self.refresh_profile_cards()

    def refresh_profile_cards(self):
        box      = self._profile_cards_box
        box.clear_widgets()
        profiles = self.data.get('profiles', {})
        active   = self._active_profile_name()

        for name, bio in profiles.items():
            is_act  = (name == active)
            card_bg = (1.0, 0.97, 0.94, 1) if is_act else (0.96, 0.96, 0.96, 1)
            CARD_PAD_H = dp(12) * 2
            CARD_PAD_V = dp(10) * 2
            ROW_H   = dp(26)
            BIO_H   = dp(18)
            BTN_H   = dp(32)
            SP      = dp(4)

            # Name + active indicator on one row
            name_row = MDBoxLayout(size_hint_y=None, height=ROW_H, spacing=dp(6))
            if is_act:
                dot = MDLabel(
                    text='\u2022',
                    size_hint=(None, None), size=(dp(14), ROW_H),
                    theme_text_color="Custom",
                    text_color=(0.18, 0.68, 0.38, 1),
                    font_size='18sp', valign='middle',
                )
                name_row.add_widget(dot)
            name_lbl = MDLabel(
                text=name,
                size_hint_y=None, height=ROW_H,
                font_size='13sp', bold=True,
                theme_text_color="Custom",
                text_color=(0.98, 0.34, 0.08, 1) if is_act else (0.22, 0.22, 0.22, 1),
                valign='middle',
            )
            name_lbl.text_size = (Window.width - dp(80), None)
            name_row.add_widget(name_lbl)

            # Bio preview
            preview = (bio[:80] + '\u2026') if len(bio) > 80 else bio if bio else 'No bio yet — tap Edit to add one.'
            bio_lbl = MDLabel(
                text=preview,
                size_hint_y=None, height=BIO_H,
                font_size='11sp',
                theme_text_color="Custom",
                text_color=(0.45, 0.45, 0.45, 1),
                valign='top',
            )
            bio_lbl.text_size = (Window.width - dp(80), None)
            bio_lbl.bind(texture_size=lambda w, ts: setattr(w, 'height', ts[1] + dp(2)))

            # Action buttons — right-aligned icon row
            btn_row = MDBoxLayout(size_hint_y=None, height=BTN_H, spacing=dp(2))
            btn_row.add_widget(Widget())  # spacer pushes buttons right

            if not is_act:
                use_btn = MDIconButton(
                    icon='check-circle-outline',
                    size_hint=(None, None), size=(dp(36), BTN_H),
                    theme_text_color="Custom",
                    text_color=(0.18, 0.68, 0.38, 1),
                )
                use_btn.bind(on_release=lambda b, n=name: self.switch_profile(n))
                btn_row.add_widget(use_btn)

            edit_btn = MDIconButton(
                icon='pencil-outline',
                size_hint=(None, None), size=(dp(36), BTN_H),
                theme_text_color="Custom",
                text_color=self.theme_cls.primary_color,
            )
            edit_btn.bind(on_release=lambda b, n=name: self.edit_profile_dialog(n))
            btn_row.add_widget(edit_btn)

            if len(profiles) > 1:
                del_btn = MDIconButton(
                    icon='trash-can-outline',
                    size_hint=(None, None), size=(dp(36), BTN_H),
                    theme_text_color="Custom", text_color=(0.78, 0.15, 0.20, 1),
                )
                del_btn.bind(on_release=lambda b, n=name: self.delete_profile_named(n))
                btn_row.add_widget(del_btn)

            card = MDCard(
                orientation='vertical', size_hint_y=None, height=dp(88),
                radius=[dp(8)], md_bg_color=card_bg,
                padding=[dp(12), dp(10)], spacing=SP,
                elevation=0,
            )
            card.add_widget(name_row)
            card.add_widget(bio_lbl)
            card.add_widget(btn_row)

            def _fix_h(card=card, bio_lbl=bio_lbl):
                card.height = ROW_H + bio_lbl.height + BTN_H + SP * 2 + CARD_PAD_V
            bio_lbl.bind(height=lambda w, h, f=_fix_h: f())

            box.add_widget(card)

    def edit_profile_dialog(self, name):
        from kivymd.uix.dialog import MDDialog
        bio = self.data.get('profiles', {}).get(name, '')
        bio_field = MDTextField(
            text=bio,
            hint_text='About you and what you\u2019re looking for...',
            mode='rectangle', multiline=True,
            size_hint_y=1, font_size='13sp',
        )
        content = MDBoxLayout(
            orientation='vertical', size_hint_y=None, height=dp(160),
            padding=[0, dp(4)],
        )
        content.add_widget(bio_field)
        dlg = [None]
        dlg[0] = MDDialog(
            title=f'Edit "{name}"', type="custom", content_cls=content,
            buttons=[
                MDFlatButton(text="Cancel", theme_text_color="Custom",
                             text_color=(0.55, 0.55, 0.55, 1),
                             on_release=lambda *_: dlg[0].dismiss()),
                MDRaisedButton(text="Save",
                               on_release=lambda *_: self._do_edit_profile(
                                   name, bio_field.text.strip(), dlg[0])),
            ],
        )
        dlg[0].open()

    def _do_edit_profile(self, name, text, dlg):
        dlg.dismiss()
        self.data.setdefault('profiles', {})[name] = text
        save_data(self.data)
        self._settings_status.text = f'"{name}" saved!'
        Clock.schedule_once(lambda dt: setattr(self._settings_status, 'text', ''), 2)
        self.refresh_profile_cards()

    def delete_profile_named(self, name):
        profiles = self.data.get('profiles', {})
        if len(profiles) <= 1:
            self._settings_status.text = "Can't delete the last profile."
            Clock.schedule_once(lambda dt: setattr(self._settings_status, 'text', ''), 2)
            return
        profiles.pop(name, None)
        if self.data.get('active_profile') == name:
            self.data['active_profile'] = next(iter(profiles))
        save_data(self.data)
        self.refresh_profile_cards()

if __name__ == '__main__':
    KindlingApp().run()
