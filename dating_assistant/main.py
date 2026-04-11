#!/usr/bin/env python3
"""
Dating Assistant App
Powered by Claude AI — chat assistant, icebreakers, tracking, motivation
"""

import os
import json
import base64
import threading
import urllib.request
import urllib.error
import random
from datetime import datetime

from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.screenmanager import ScreenManager, Screen, NoTransition
from kivy.uix.filechooser import FileChooserListView
from kivy.graphics import Color, RoundedRectangle

Window.clearcolor = (1, 1, 1, 1)

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
                return json.load(f)
    except Exception:
        pass
    return {
        "api_key": "",
        "style_profile": "",
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
    ctx = _make_ssl_context()
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
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
            err = f"Claude API {e.code}: {e.read().decode()[:250]}"
            Clock.schedule_once(lambda dt: callback(None, err), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: callback(None, str(e)), 0)
    threading.Thread(target=run, daemon=True).start()


def _call_openai(api_key, messages, system, callback):
    def run():
        try:
            oai_msgs = [{"role": "system", "content": system}]
            for m in messages:
                role = m["role"]
                content = m["content"]
                if isinstance(content, list):
                    # Convert Claude-style content blocks to OpenAI format
                    parts = []
                    for block in content:
                        if block.get("type") == "text":
                            parts.append({"type": "text", "text": block["text"]})
                        elif block.get("type") == "image":
                            src = block["source"]
                            parts.append({"type": "image_url", "image_url": {
                                "url": f"data:{src['media_type']};base64,{src['data']}"
                            }})
                    oai_msgs.append({"role": role, "content": parts})
                else:
                    oai_msgs.append({"role": role, "content": content})
            result = _http_post(
                "https://api.openai.com/v1/chat/completions",
                {
                    "Authorization": f"Bearer {api_key}",
                    "content-type": "application/json",
                },
                json.dumps({
                    "model": "gpt-4o-mini",
                    "max_tokens": 1500,
                    "messages": oai_msgs,
                }).encode("utf-8"),
            )
            text = result["choices"][0]["message"]["content"]
            Clock.schedule_once(lambda dt: callback(text, None), 0)
        except urllib.error.HTTPError as e:
            err = f"OpenAI API {e.code}: {e.read().decode()[:250]}"
            Clock.schedule_once(lambda dt: callback(None, err), 0)
        except Exception as e:
            Clock.schedule_once(lambda dt: callback(None, str(e)), 0)
    threading.Thread(target=run, daemon=True).start()


# (api_version, model_name) — try v1 stable first, v1beta as fallback
GEMINI_MODELS = [
    ("v1", "gemini-2.0-flash-lite"),
    ("v1", "gemini-2.0-flash"),
    ("v1", "gemini-1.5-flash"),
    ("v1", "gemini-1.5-flash-002"),
    ("v1beta", "gemini-2.0-flash-lite"),
    ("v1beta", "gemini-2.0-flash"),
    ("v1beta", "gemini-2.5-flash"),
    ("v1beta", "gemini-2.5-pro"),
]


def _call_gemini(api_key, messages, system, callback):
    def run():
        import time

        # Convert messages to Gemini format once
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
                            "mime_type": src["media_type"],
                            "data": src["data"],
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
                body_txt = ""
                try:
                    body_txt = e.read().decode()[:150]
                except Exception:
                    pass
                last_err = f"Gemini {code} ({api_ver}/{model}): {body_txt}"
                if code == 429:
                    time.sleep(3)
                    continue
                elif code in (404, 400):
                    # Model not found or not supported — try next
                    continue
                else:
                    break
            except Exception as e:
                last_err = str(e)
                break

        Clock.schedule_once(lambda dt: callback(None, last_err), 0)

    threading.Thread(target=run, daemon=True).start()


def call_ai(provider, api_key, messages, system, callback):
    """Dispatch to the selected AI provider."""
    if provider == 'claude':
        _call_claude(api_key, messages, system, callback)
    elif provider == 'openai':
        _call_openai(api_key, messages, system, callback)
    else:
        _call_gemini(api_key, messages, system, callback)


# ─── KV Layout ────────────────────────────────────────────────────────────────

KV = """
#:import NoTransition kivy.uix.screenmanager.NoTransition

BoxLayout:
    orientation: 'vertical'

    ScreenManager:
        id: sm
        transition: NoTransition()

        Screen:
            name: 'assistant'
            BoxLayout:
                orientation: 'vertical'
                padding: '10dp'
                spacing: '6dp'

                Label:
                    text: 'Dating Assistant'
                    color: (1, 0.42, 0.17, 1)
                    font_size: '20sp'
                    bold: True
                    size_hint_y: None
                    height: '38dp'

                ScrollView:
                    id: chat_scroll
                    do_scroll_x: False
                    BoxLayout:
                        id: chat_box
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: '6dp'
                        padding: '2dp'

                BoxLayout:
                    size_hint_y: None
                    height: '36dp'
                    spacing: '6dp'

                    Button:
                        text: 'Add Screenshot'
                        size_hint_x: 0.45
                        background_normal: ''
                        background_color: (0.88, 0.88, 0.88, 1)
                        color: (0.25, 0.25, 0.25, 1)
                        font_size: '12sp'
                        on_press: app.show_file_picker()

                    Label:
                        id: img_label
                        text: 'No image attached'
                        color: (0.6, 0.6, 0.6, 1)
                        font_size: '11sp'
                        halign: 'left'
                        text_size: self.width, None

                TextInput:
                    id: user_input
                    hint_text: 'Ask for message ideas, conversation tips, icebreakers...'
                    size_hint_y: None
                    height: '78dp'
                    multiline: True
                    font_size: '14sp'
                    background_color: (0.97, 0.97, 0.97, 1)
                    foreground_color: (0.15, 0.15, 0.15, 1)
                    padding: ['8dp', '8dp']

                BoxLayout:
                    size_hint_y: None
                    height: '46dp'
                    spacing: '8dp'

                    Button:
                        text: 'Clear'
                        size_hint_x: 0.22
                        background_normal: ''
                        background_color: (0.88, 0.88, 0.88, 1)
                        color: (0.3, 0.3, 0.3, 1)
                        font_size: '13sp'
                        on_press: app.clear_chat()

                    Button:
                        id: send_btn
                        text: 'Get Advice'
                        size_hint_x: 0.78
                        background_normal: ''
                        background_color: (1, 0.42, 0.17, 1)
                        color: (1, 1, 1, 1)
                        font_size: '15sp'
                        bold: True
                        on_press: app.send_message()

        Screen:
            name: 'icebreakers'
            BoxLayout:
                orientation: 'vertical'
                padding: '12dp'
                spacing: '10dp'

                Label:
                    text: 'Icebreakers & Openers'
                    color: (1, 0.42, 0.17, 1)
                    font_size: '20sp'
                    bold: True
                    size_hint_y: None
                    height: '38dp'

                Label:
                    text: 'Describe the situation or person (optional):'
                    color: (0.4, 0.4, 0.4, 1)
                    font_size: '13sp'
                    size_hint_y: None
                    height: '22dp'
                    halign: 'left'
                    text_size: self.width, None

                TextInput:
                    id: ice_context
                    hint_text: 'e.g. "coffee shop, she is reading" or "Hinge match, loves hiking & dogs"'
                    size_hint_y: None
                    height: '72dp'
                    multiline: True
                    font_size: '14sp'
                    background_color: (0.97, 0.97, 0.97, 1)
                    foreground_color: (0.15, 0.15, 0.15, 1)
                    padding: ['8dp', '8dp']

                BoxLayout:
                    size_hint_y: None
                    height: '46dp'
                    spacing: '6dp'

                    Button:
                        text: 'App Opener'
                        background_normal: ''
                        background_color: (1, 0.42, 0.17, 1)
                        color: (1, 1, 1, 1)
                        font_size: '13sp'
                        bold: True
                        on_press: app.generate_opener('app')

                    Button:
                        text: 'In-Person'
                        background_normal: ''
                        background_color: (0.9, 0.22, 0.27, 1)
                        color: (1, 1, 1, 1)
                        font_size: '13sp'
                        bold: True
                        on_press: app.generate_opener('inperson')

                    Button:
                        text: 'Date Ideas'
                        background_normal: ''
                        background_color: (0.22, 0.6, 0.42, 1)
                        color: (1, 1, 1, 1)
                        font_size: '13sp'
                        bold: True
                        on_press: app.generate_opener('date')

                ScrollView:
                    do_scroll_x: False
                    BoxLayout:
                        id: ice_box
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height
                        padding: '4dp'
                        spacing: '4dp'

        Screen:
            name: 'track'
            BoxLayout:
                orientation: 'vertical'
                padding: '12dp'
                spacing: '8dp'

                Label:
                    text: 'Track Your Results'
                    color: (1, 0.42, 0.17, 1)
                    font_size: '20sp'
                    bold: True
                    size_hint_y: None
                    height: '38dp'

                TextInput:
                    id: track_note
                    hint_text: 'What happened? What did you try? (optional)'
                    size_hint_y: None
                    height: '72dp'
                    multiline: True
                    font_size: '14sp'
                    background_color: (0.97, 0.97, 0.97, 1)
                    foreground_color: (0.15, 0.15, 0.15, 1)
                    padding: ['8dp', '8dp']

                BoxLayout:
                    size_hint_y: None
                    height: '46dp'
                    spacing: '8dp'

                    Button:
                        text: 'Log a Win!'
                        background_normal: ''
                        background_color: (0.18, 0.68, 0.38, 1)
                        color: (1, 1, 1, 1)
                        font_size: '14sp'
                        bold: True
                        on_press: app.log_result('success')

                    Button:
                        text: "Didn't Work"
                        background_normal: ''
                        background_color: (0.9, 0.22, 0.27, 1)
                        color: (1, 1, 1, 1)
                        font_size: '14sp'
                        bold: True
                        on_press: app.log_result('failure')

                BoxLayout:
                    size_hint_y: None
                    height: '34dp'
                    spacing: '8dp'

                    Label:
                        id: wins_label
                        text: 'Wins: 0'
                        color: (0.18, 0.68, 0.38, 1)
                        font_size: '15sp'
                        bold: True

                    Label:
                        id: fails_label
                        text: 'Learning: 0'
                        color: (0.9, 0.22, 0.27, 1)
                        font_size: '15sp'
                        bold: True

                ScrollView:
                    do_scroll_x: False
                    BoxLayout:
                        id: track_box
                        orientation: 'vertical'
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: '5dp'
                        padding: '2dp'

        Screen:
            name: 'motivation'
            BoxLayout:
                orientation: 'vertical'
                padding: '14dp'
                spacing: '14dp'

                Label:
                    text: 'Get Out There!'
                    color: (1, 0.42, 0.17, 1)
                    font_size: '22sp'
                    bold: True
                    size_hint_y: None
                    height: '42dp'

                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: '160dp'
                    padding: '14dp'
                    canvas.before:
                        Color:
                            rgba: (1, 0.96, 0.93, 1)
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [12]

                    Label:
                        id: quote_label
                        text: ''
                        color: (0.18, 0.18, 0.18, 1)
                        font_size: '15sp'
                        text_size: self.width, None
                        halign: 'center'
                        valign: 'middle'

                Button:
                    text: 'Shuffle Inspiration'
                    size_hint_y: None
                    height: '46dp'
                    background_normal: ''
                    background_color: (1, 0.42, 0.17, 1)
                    color: (1, 1, 1, 1)
                    font_size: '15sp'
                    bold: True
                    on_press: app.shuffle_quote()

                Label:
                    text: "Therapist's Corner"
                    color: (0.9, 0.22, 0.27, 1)
                    font_size: '16sp'
                    bold: True
                    size_hint_y: None
                    height: '30dp'
                    halign: 'left'
                    text_size: self.width, None

                BoxLayout:
                    orientation: 'vertical'
                    size_hint_y: None
                    height: '150dp'
                    padding: '14dp'
                    canvas.before:
                        Color:
                            rgba: (1, 0.93, 0.94, 1)
                        RoundedRectangle:
                            pos: self.pos
                            size: self.size
                            radius: [12]

                    Label:
                        id: therapy_label
                        text: ''
                        color: (0.3, 0.1, 0.12, 1)
                        font_size: '13sp'
                        text_size: self.width, None
                        halign: 'center'
                        valign: 'middle'

                Button:
                    text: 'New Insight'
                    size_hint_y: None
                    height: '46dp'
                    background_normal: ''
                    background_color: (0.9, 0.22, 0.27, 1)
                    color: (1, 1, 1, 1)
                    font_size: '15sp'
                    bold: True
                    on_press: app.shuffle_therapy()

                Widget:

        Screen:
            name: 'settings'
            BoxLayout:
                orientation: 'vertical'
                padding: '14dp'
                spacing: '10dp'

                Label:
                    text: 'Settings'
                    color: (1, 0.42, 0.17, 1)
                    font_size: '20sp'
                    bold: True
                    size_hint_y: None
                    height: '38dp'

                Label:
                    text: 'AI Provider:'
                    color: (0.35, 0.35, 0.35, 1)
                    font_size: '13sp'
                    size_hint_y: None
                    height: '22dp'
                    halign: 'left'
                    text_size: self.width, None

                BoxLayout:
                    size_hint_y: None
                    height: '46dp'
                    spacing: '6dp'

                    Button:
                        id: btn_gemini
                        text: 'Gemini'
                        background_normal: ''
                        background_color: (1, 0.42, 0.17, 1)
                        color: (1, 1, 1, 1)
                        font_size: '14sp'
                        bold: True
                        on_press: app.set_provider('gemini')

                    Button:
                        id: btn_claude
                        text: 'Claude'
                        background_normal: ''
                        background_color: (0.88, 0.88, 0.88, 1)
                        color: (0.3, 0.3, 0.3, 1)
                        font_size: '14sp'
                        on_press: app.set_provider('claude')

                    Button:
                        id: btn_openai
                        text: 'OpenAI'
                        background_normal: ''
                        background_color: (0.88, 0.88, 0.88, 1)
                        color: (0.3, 0.3, 0.3, 1)
                        font_size: '14sp'
                        on_press: app.set_provider('openai')

                Label:
                    id: provider_note
                    text: 'Free tier available — get key at aistudio.google.com'
                    color: (0.22, 0.6, 0.35, 1)
                    font_size: '12sp'
                    size_hint_y: None
                    height: '22dp'
                    halign: 'left'
                    text_size: self.width, None

                Label:
                    text: 'API Key:'
                    color: (0.35, 0.35, 0.35, 1)
                    font_size: '13sp'
                    size_hint_y: None
                    height: '22dp'
                    halign: 'left'
                    text_size: self.width, None

                TextInput:
                    id: api_key_input
                    hint_text: 'Get free key at aistudio.google.com'
                    size_hint_y: None
                    height: '46dp'
                    multiline: False
                    password: True
                    font_size: '13sp'
                    background_color: (0.97, 0.97, 0.97, 1)
                    foreground_color: (0.15, 0.15, 0.15, 1)
                    padding: ['8dp', '12dp']

                Button:
                    text: 'Save Settings'
                    size_hint_y: None
                    height: '46dp'
                    background_normal: ''
                    background_color: (1, 0.42, 0.17, 1)
                    color: (1, 1, 1, 1)
                    font_size: '14sp'
                    bold: True
                    on_press: app.save_api_key()

                Label:
                    id: settings_status
                    text: ''
                    color: (0.18, 0.6, 0.3, 1)
                    font_size: '13sp'
                    size_hint_y: None
                    height: '26dp'

                Label:
                    text: 'My Style Profile'
                    color: (1, 0.42, 0.17, 1)
                    font_size: '15sp'
                    bold: True
                    size_hint_y: None
                    height: '30dp'
                    halign: 'left'
                    text_size: self.width, None

                Label:
                    text: 'Tell the assistant about you and what you are looking for:'
                    color: (0.4, 0.4, 0.4, 1)
                    font_size: '12sp'
                    size_hint_y: None
                    height: '22dp'
                    halign: 'left'
                    text_size: self.width, None

                TextInput:
                    id: style_input
                    hint_text: 'e.g. "I am a 28M, funny and laid back, looking for something serious. I tend to be a bit shy at first..."'
                    size_hint_y: None
                    height: '110dp'
                    multiline: True
                    font_size: '13sp'
                    background_color: (0.97, 0.97, 0.97, 1)
                    foreground_color: (0.15, 0.15, 0.15, 1)
                    padding: ['8dp', '8dp']

                Button:
                    text: 'Save Style Profile'
                    size_hint_y: None
                    height: '46dp'
                    background_normal: ''
                    background_color: (0.9, 0.22, 0.27, 1)
                    color: (1, 1, 1, 1)
                    font_size: '14sp'
                    bold: True
                    on_press: app.save_style_profile()

                Widget:

    # Bottom Navigation Bar
    BoxLayout:
        size_hint_y: None
        height: '54dp'
        canvas.before:
            Color:
                rgba: (0.95, 0.95, 0.95, 1)
            Rectangle:
                pos: self.pos
                size: self.size

        Button:
            id: nav_assistant
            text: 'Assistant'
            background_normal: ''
            background_color: (1, 0.42, 0.17, 1)
            color: (1, 1, 1, 1)
            font_size: '11sp'
            bold: True
            on_press: app.switch_screen('assistant')

        Button:
            id: nav_ice
            text: 'Icebreakers'
            background_normal: ''
            background_color: (0.95, 0.95, 0.95, 1)
            color: (0.45, 0.45, 0.45, 1)
            font_size: '10sp'
            on_press: app.switch_screen('icebreakers')

        Button:
            id: nav_track
            text: 'Track'
            background_normal: ''
            background_color: (0.95, 0.95, 0.95, 1)
            color: (0.45, 0.45, 0.45, 1)
            font_size: '11sp'
            on_press: app.switch_screen('track')

        Button:
            id: nav_motive
            text: 'Motivate'
            background_normal: ''
            background_color: (0.95, 0.95, 0.95, 1)
            color: (0.45, 0.45, 0.45, 1)
            font_size: '11sp'
            on_press: app.switch_screen('motivation')

        Button:
            id: nav_settings
            text: 'Settings'
            background_normal: ''
            background_color: (0.95, 0.95, 0.95, 1)
            color: (0.45, 0.45, 0.45, 1)
            font_size: '11sp'
            on_press: app.switch_screen('settings')
"""


# ─── App Class ────────────────────────────────────────────────────────────────

class DatingAssistantApp(App):

    def build(self):
        global _data_file
        _data_file = os.path.join(self.user_data_dir, "dating_data.json")
        self.data = load_data()
        self.current_image_path = None
        self._nav_ids = {}

        root = Builder.load_string(KV)

        # Cache frequently used widget refs
        ids = root.ids
        self._chat_box = ids.chat_box
        self._chat_scroll = ids.chat_scroll
        self._user_input = ids.user_input
        self._img_label = ids.img_label
        self._send_btn = ids.send_btn
        self._ice_context = ids.ice_context
        self._ice_box = ids.ice_box
        self._track_note = ids.track_note
        self._track_box = ids.track_box
        self._wins_label = ids.wins_label
        self._fails_label = ids.fails_label
        self._quote_label = ids.quote_label
        self._therapy_label = ids.therapy_label
        self._api_key_input = ids.api_key_input
        self._style_input = ids.style_input
        self._settings_status = ids.settings_status
        self._provider_note = ids.provider_note
        self._sm = ids.sm

        self._nav_ids = {
            'assistant': ids.nav_assistant,
            'icebreakers': ids.nav_ice,
            'track': ids.nav_track,
            'motivation': ids.nav_motive,
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
        if self.data.get('style_profile'):
            self._style_input.text = self.data['style_profile']

        # Restore / default provider
        saved_provider = self.data.get('provider', 'gemini')
        self.set_provider(saved_provider, save=False)

        # Initial content
        self.shuffle_quote()
        self.shuffle_therapy()
        self.refresh_track_display()

        self._add_bubble('assistant',
            "Hi! I'm your Dating Assistant.\n\n"
            "I can help with message ideas, conversation tips, icebreakers "
            "for apps or in person, and date suggestions.\n\n"
            "Go to Settings to choose your AI provider (Gemini is free!) "
            "and add your API key, then ask me anything!")

        return root

    # ── Provider ───────────────────────────────────────────────────────────────

    def set_provider(self, provider, save=True):
        self.data['provider'] = provider
        notes = {
            'gemini': 'Free tier available — get key at aistudio.google.com',
            'claude': 'Paid API — console.anthropic.com',
            'openai': 'Paid API — platform.openai.com',
        }
        active = (1, 0.42, 0.17, 1)
        inactive = (0.88, 0.88, 0.88, 1)
        for p, btn in self._provider_btns.items():
            if p == provider:
                btn.background_color = active
                btn.color = (1, 1, 1, 1)
                btn.bold = True
            else:
                btn.background_color = inactive
                btn.color = (0.3, 0.3, 0.3, 1)
                btn.bold = False
        self._provider_note.text = notes.get(provider, '')
        self._api_key_input.hint_text = PROVIDER_HINTS.get(provider, '')
        if save:
            save_data(self.data)

    # ── Navigation ─────────────────────────────────────────────────────────────

    def switch_screen(self, name):
        self._sm.current = name
        active = (1, 0.42, 0.17, 1)
        inactive = (0.95, 0.95, 0.95, 1)
        for n, btn in self._nav_ids.items():
            if n == name:
                btn.background_color = active
                btn.color = (1, 1, 1, 1)
                btn.bold = True
            else:
                btn.background_color = inactive
                btn.color = (0.45, 0.45, 0.45, 1)
                btn.bold = False

    # ── Chat ───────────────────────────────────────────────────────────────────

    def _add_bubble(self, role, text):
        is_user = role == 'user'
        bg = (0.90, 0.92, 1.0, 1) if is_user else (1, 0.96, 0.93, 1)
        name_color = (0.2, 0.4, 0.85, 1) if is_user else (1, 0.42, 0.17, 1)

        outer = BoxLayout(
            orientation='vertical',
            size_hint_y=None,
            padding=[dp(10), dp(8), dp(10), dp(6)],
            spacing=dp(3),
        )

        with outer.canvas.before:
            c = Color(*bg)
            rect = RoundedRectangle(pos=outer.pos, size=outer.size, radius=[dp(8)])

        outer.bind(
            pos=lambda inst, val: setattr(rect, 'pos', val),
            size=lambda inst, val: setattr(rect, 'size', val),
        )

        role_lbl = Label(
            text="You" if is_user else "Assistant",
            color=name_color,
            font_size=dp(11),
            bold=True,
            size_hint_y=None,
            height=dp(18),
            halign='right' if is_user else 'left',
        )
        role_lbl.bind(width=lambda inst, w: setattr(inst, 'text_size', (w, None)))

        msg_lbl = Label(
            text=text,
            color=(0.12, 0.12, 0.12, 1),
            font_size=dp(14),
            text_size=(Window.width - dp(44), None),
            halign='right' if is_user else 'left',
            valign='top',
            size_hint_y=None,
            height=dp(40),
        )

        def _on_texture(inst, tex_size):
            inst.height = tex_size[1]
            outer.height = (
                role_lbl.height + tex_size[1]
                + outer.padding[1] + outer.padding[3]
                + outer.spacing
            )

        msg_lbl.bind(texture_size=_on_texture)

        outer.add_widget(role_lbl)
        outer.add_widget(msg_lbl)
        outer.height = dp(80)

        self._chat_box.add_widget(outer)
        Clock.schedule_once(lambda dt: setattr(self._chat_scroll, 'scroll_y', 0), 0.12)

    def send_message(self):
        api_key = self.data.get('api_key', '').strip()
        provider = self.data.get('provider', 'gemini')
        if not api_key:
            pname = PROVIDER_LABELS.get(provider, provider)
            self._popup("API Key Required",
                        f"Please add your {pname} API key in Settings first.")
            return

        text = self._user_input.text.strip()
        img_path = self.current_image_path

        if not text and not img_path:
            return

        # Build content blocks
        content = []
        if img_path:
            try:
                with open(img_path, 'rb') as f:
                    b64 = base64.b64encode(f.read()).decode('utf-8')
                ext = os.path.splitext(img_path)[1].lower()
                mtype = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                         '.png': 'image/png', '.gif': 'image/gif',
                         '.webp': 'image/webp'}.get(ext, 'image/jpeg')
                content.append({"type": "image",
                                 "source": {"type": "base64",
                                            "media_type": mtype,
                                            "data": b64}})
            except Exception as e:
                self._popup("Image Error", str(e))

        display_text = text or "(image only)"
        if img_path and text:
            display_text = f"[Screenshot]\n{text}"
        elif img_path:
            display_text = "[Screenshot attached — please advise]"

        content.append({"type": "text", "text": display_text})

        # Add style profile to first user turn if available
        history = list(self.data.get('conversation_history', []))
        style = self.data.get('style_profile', '').strip()
        if style and not history:
            content[-1]['text'] = f"[About me: {style}]\n\n{content[-1]['text']}"

        self._add_bubble('user', display_text)
        self._user_input.text = ''
        self.current_image_path = None
        self._img_label.text = 'No image attached'

        self._send_btn.disabled = True
        self._send_btn.text = 'Thinking...'

        messages = history + [{"role": "user", "content": content}]

        def on_resp(resp_text, error):
            self._send_btn.disabled = False
            self._send_btn.text = 'Get Advice'
            if error:
                self._add_bubble('assistant', f"Error: {error}")
                return
            self._add_bubble('assistant', resp_text)
            hist = self.data.get('conversation_history', [])
            hist.append({"role": "user", "content": display_text})
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
        self._add_bubble('assistant', "Chat cleared. What would you like help with?")

    def show_file_picker(self):
        content = BoxLayout(orientation='vertical', spacing=dp(8))

        start = '/storage/emulated/0'
        if not os.path.exists(start):
            start = os.path.expanduser('~')
        if not os.path.exists(start):
            start = '/'

        chooser = FileChooserListView(
            path=start,
            filters=['*.jpg', '*.jpeg', '*.png', '*.webp', '*.gif'],
        )

        btn_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        sel_btn = Button(text='Select', background_normal='',
                         background_color=(1, 0.42, 0.17, 1),
                         color=(1, 1, 1, 1))
        can_btn = Button(text='Cancel', background_normal='',
                         background_color=(0.88, 0.88, 0.88, 1),
                         color=(0.3, 0.3, 0.3, 1))
        btn_row.add_widget(can_btn)
        btn_row.add_widget(sel_btn)
        content.add_widget(chooser)
        content.add_widget(btn_row)

        popup = Popup(title='Select Screenshot', content=content,
                      size_hint=(0.95, 0.82))

        def on_select(_):
            if chooser.selection:
                self.current_image_path = chooser.selection[0]
                fname = os.path.basename(self.current_image_path)
                self._img_label.text = (fname[:22] + '…') if len(fname) > 22 else fname
            popup.dismiss()

        sel_btn.bind(on_press=on_select)
        can_btn.bind(on_press=lambda _: popup.dismiss())
        popup.open()

    # ── Icebreakers ────────────────────────────────────────────────────────────

    def generate_opener(self, kind):
        api_key = self.data.get('api_key', '').strip()
        provider = self.data.get('provider', 'gemini')
        if not api_key:
            pname = PROVIDER_LABELS.get(provider, provider)
            self._popup("API Key Required",
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
                "Avoid anything corny. Include a brief note on delivery for each."
            ),
            'date': (
                f"Suggest 5 creative date ideas. Context: {ctx}\n"
                "Mix low-key and more adventurous options. "
                "Include free/cheap options alongside others."
            ),
        }

        self._ice_box.clear_widgets()
        loading = Label(
            text='Generating ideas...',
            color=(0.55, 0.55, 0.55, 1),
            font_size=dp(14),
            size_hint_y=None,
            height=dp(40),
        )
        self._ice_box.add_widget(loading)

        messages = [{"role": "user", "content": prompts[kind]}]

        def on_resp(resp_text, error):
            self._ice_box.clear_widgets()
            body = error or resp_text
            lbl = Label(
                text=body,
                color=(0.12, 0.12, 0.12, 1),
                font_size=dp(14),
                text_size=(Window.width - dp(40), None),
                halign='left',
                valign='top',
                size_hint_y=None,
                height=dp(60),
            )
            lbl.bind(texture_size=lambda inst, v: setattr(inst, 'height', v[1]))
            self._ice_box.add_widget(lbl)

        call_ai(provider, api_key, messages, SYSTEM_PROMPT, on_resp)

    # ── Track ──────────────────────────────────────────────────────────────────

    def log_result(self, kind):
        note = self._track_note.text.strip()
        self._track_note.text = ''

        entry = {"note": note, "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
        key = 'successes' if kind == 'success' else 'failures'
        self.data.setdefault(key, []).append(entry)
        save_data(self.data)
        self.refresh_track_display()

    def refresh_track_display(self):
        wins = len(self.data.get('successes', []))
        fails = len(self.data.get('failures', []))

        if hasattr(self, '_wins_label'):
            self._wins_label.text = f'Wins: {wins}'
            self._fails_label.text = f'Learning: {fails}'

        if not hasattr(self, '_track_box'):
            return

        self._track_box.clear_widgets()

        all_entries = (
            [('W', e) for e in self.data.get('successes', [])] +
            [('L', e) for e in self.data.get('failures', [])]
        )
        all_entries.sort(key=lambda x: x[1].get('date', ''), reverse=True)

        for tag, entry in all_entries[:25]:
            is_win = tag == 'W'
            color = (0.12, 0.55, 0.28, 1) if is_win else (0.75, 0.15, 0.20, 1)
            icon = "WIN" if is_win else "LEARN"
            note_text = entry.get('note') or '(no note)'
            lbl = Label(
                text=f"[{icon}]  {entry.get('date', '')}  —  {note_text}",
                color=color,
                font_size=dp(12),
                text_size=(Window.width - dp(30), None),
                halign='left',
                valign='top',
                size_hint_y=None,
                height=dp(32),
            )
            lbl.bind(texture_size=lambda inst, v: setattr(inst, 'height', v[1] + dp(4)))
            self._track_box.add_widget(lbl)

    # ── Motivation ─────────────────────────────────────────────────────────────

    def shuffle_quote(self):
        if hasattr(self, '_quote_label'):
            self._quote_label.text = random.choice(MOTIVATIONAL_QUOTES)

    def shuffle_therapy(self):
        if hasattr(self, '_therapy_label'):
            self._therapy_label.text = random.choice(THERAPY_TIPS)

    # ── Settings ───────────────────────────────────────────────────────────────

    def save_api_key(self):
        key = self._api_key_input.text.strip()
        self.data['api_key'] = key
        save_data(self.data)
        self._settings_status.text = "API key saved!" if key else "API key cleared."
        Clock.schedule_once(
            lambda dt: setattr(self._settings_status, 'text', ''), 2.5)

    def save_style_profile(self):
        profile = self._style_input.text.strip()
        self.data['style_profile'] = profile
        save_data(self.data)
        self._settings_status.text = "Style profile saved!"
        Clock.schedule_once(
            lambda dt: setattr(self._settings_status, 'text', ''), 2.5)

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _popup(self, title, msg):
        content = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
        lbl = Label(text=msg, color=(0.15, 0.15, 0.15, 1),
                    text_size=(Window.width * 0.72, None), halign='center')
        btn = Button(text='OK', size_hint_y=None, height=dp(44),
                     background_normal='', background_color=(1, 0.42, 0.17, 1),
                     color=(1, 1, 1, 1))
        content.add_widget(lbl)
        content.add_widget(btn)
        pop = Popup(title=title, content=content, size_hint=(0.82, 0.38))
        btn.bind(on_press=lambda _: pop.dismiss())
        pop.open()


if __name__ == '__main__':
    DatingAssistantApp().run()
