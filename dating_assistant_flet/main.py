#!/usr/bin/env python3
"""
Dating Assistant App — Flet
Powered by Claude AI — chat assistant, icebreakers, tracking, motivation
"""

import os
import json
import base64
import threading
import urllib.request
import urllib.error
import ssl
import random
from datetime import datetime

import flet as ft

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

PROVIDER_LABELS = {'gemini': 'Gemini', 'claude': 'Claude', 'openai': 'OpenAI'}
PROVIDER_HINTS = {
    'gemini': 'Get free key at aistudio.google.com',
    'claude': 'sk-ant-api03-...',
    'openai': 'sk-...',
}

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

# ─── Data ─────────────────────────────────────────────────────────────────────

def load_data(path):
    try:
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "api_key": "",
        "provider": "gemini",
        "style_profile": "",
        "conversation_history": [],
        "successes": [],
        "failures": [],
    }


def save_data(path, data):
    try:
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Save error: {e}")


# ─── AI Providers ─────────────────────────────────────────────────────────────

def _make_ssl_context():
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
            callback(result["content"][0]["text"], None)
        except urllib.error.HTTPError as e:
            callback(None, f"Claude API {e.code}: {e.read().decode()[:250]}")
        except Exception as e:
            callback(None, str(e))
    threading.Thread(target=run, daemon=True).start()


def _call_openai(api_key, messages, system, callback):
    def run():
        try:
            oai_msgs = [{"role": "system", "content": system}]
            for m in messages:
                role = m["role"]
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
            callback(result["choices"][0]["message"]["content"], None)
        except urllib.error.HTTPError as e:
            callback(None, f"OpenAI API {e.code}: {e.read().decode()[:250]}")
        except Exception as e:
            callback(None, str(e))
    threading.Thread(target=run, daemon=True).start()


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
                callback(result["candidates"][0]["content"]["parts"][0]["text"], None)
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
                    continue
                else:
                    break
            except Exception as e:
                last_err = str(e)
                break

        callback(None, last_err)

    threading.Thread(target=run, daemon=True).start()


def call_ai(provider, api_key, messages, system, callback):
    if provider == 'claude':
        _call_claude(api_key, messages, system, callback)
    elif provider == 'openai':
        _call_openai(api_key, messages, system, callback)
    else:
        _call_gemini(api_key, messages, system, callback)


# ─── Flet App ─────────────────────────────────────────────────────────────────

ORANGE = "#FF6B2B"
RED    = "#E63845"
GREEN  = "#2EAD61"

BTN_ORANGE = ft.ButtonStyle(bgcolor={"": ORANGE}, color={"": "#FFFFFF"})
BTN_RED    = ft.ButtonStyle(bgcolor={"": RED},    color={"": "#FFFFFF"})
BTN_GREEN  = ft.ButtonStyle(bgcolor={"": GREEN},  color={"": "#FFFFFF"})
BTN_GREY   = ft.ButtonStyle(bgcolor={"": "#E0E0E0"}, color={"": "#404040"})


def _field(**kwargs) -> ft.TextField:
    defaults = dict(bgcolor="#F7F7F7", filled=True, border_color="#E0E0E0", text_size=14)
    defaults.update(kwargs)
    return ft.TextField(**defaults)


def main(page: ft.Page):
    page.title = "Dating Assistant"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.WHITE
    page.padding = 0

    # ── Data ──────────────────────────────────────────────────────────────────
    data_dir = getattr(page, 'app_data_dir', None) or "."
    data_file = os.path.join(data_dir, "dating_data.json")
    data = load_data(data_file)

    image_path: list[str | None] = [None]

    # ── Helpers ───────────────────────────────────────────────────────────────

    def show_alert(title: str, msg: str):
        dlg = ft.AlertDialog(
            title=ft.Text(title, weight=ft.FontWeight.BOLD),
            content=ft.Text(msg),
            actions=[ft.TextButton("OK", on_click=lambda e: page.close(dlg))],
        )
        page.open(dlg)

    # ── File picker ───────────────────────────────────────────────────────────

    img_label = ft.Text("No image attached", color="#999999", size=11)

    def on_file_picked(e: ft.FilePickerResultEvent):
        if e.files:
            image_path[0] = e.files[0].path
            fname = os.path.basename(image_path[0])
            img_label.value = (fname[:24] + "…") if len(fname) > 24 else fname
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_picked)
    page.overlay.append(file_picker)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 0 — Assistant
    # ══════════════════════════════════════════════════════════════════════════

    chat_list = ft.ListView(
        expand=True,
        spacing=6,
        padding=ft.padding.symmetric(horizontal=8, vertical=6),
        auto_scroll=True,
    )

    def make_bubble(role: str, text: str) -> ft.Container:
        is_user = role == "user"
        return ft.Container(
            content=ft.Column([
                ft.Text(
                    "You" if is_user else "Assistant",
                    color="#3466DA" if is_user else ORANGE,
                    size=11,
                    weight=ft.FontWeight.BOLD,
                ),
                ft.Text(text, color="#1E1E1E", size=14, selectable=True),
            ], spacing=2, tight=True),
            bgcolor="#E8ECFF" if is_user else "#FFF5EE",
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
            margin=ft.margin.only(
                left=32 if is_user else 0,
                right=0 if is_user else 32,
            ),
        )

    def add_bubble(role: str, text: str):
        chat_list.controls.append(make_bubble(role, text))
        page.update()

    user_input = _field(
        hint_text="Ask for message ideas, conversation tips, icebreakers...",
        multiline=True,
        min_lines=2,
        max_lines=4,
        expand=True,
    )
    send_btn = ft.ElevatedButton(
        "Get Advice",
        expand=True,
        style=BTN_ORANGE,
        on_click=lambda e: send_message(),
    )

    def send_message():
        api_key = data.get("api_key", "").strip()
        provider = data.get("provider", "gemini")
        if not api_key:
            show_alert("API Key Required",
                       f"Please add your {PROVIDER_LABELS.get(provider, provider)} API key in Settings first.")
            return

        text = (user_input.value or "").strip()
        img = image_path[0]
        if not text and not img:
            return

        content = []
        if img:
            try:
                with open(img, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                ext = os.path.splitext(img)[1].lower()
                mtype = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                         ".png": "image/png", ".gif": "image/gif",
                         ".webp": "image/webp"}.get(ext, "image/jpeg")
                content.append({"type": "image",
                                 "source": {"type": "base64", "media_type": mtype, "data": b64}})
            except Exception as ex:
                show_alert("Image Error", str(ex))

        if img and text:
            display_text = f"[Screenshot]\n{text}"
        elif img:
            display_text = "[Screenshot attached — please advise]"
        else:
            display_text = text

        content.append({"type": "text", "text": display_text})

        history = list(data.get("conversation_history", []))
        style = data.get("style_profile", "").strip()
        if style and not history:
            content[-1]["text"] = f"[About me: {style}]\n\n{content[-1]['text']}"

        add_bubble("user", display_text)
        user_input.value = ""
        image_path[0] = None
        img_label.value = "No image attached"

        send_btn.disabled = True
        send_btn.text = "Thinking…"
        page.update()

        messages = history + [{"role": "user", "content": content}]

        def on_resp(resp_text, error):
            send_btn.disabled = False
            send_btn.text = "Get Advice"
            if error:
                add_bubble("assistant", f"Error: {error}")
                return
            add_bubble("assistant", resp_text)
            hist = data.get("conversation_history", [])
            hist.append({"role": "user", "content": display_text})
            hist.append({"role": "assistant", "content": resp_text})
            if len(hist) > 20:
                hist = hist[-20:]
            data["conversation_history"] = hist
            save_data(data_file, data)

        call_ai(provider, api_key, messages, SYSTEM_PROMPT, on_resp)

    def clear_chat(e):
        chat_list.controls.clear()
        data["conversation_history"] = []
        save_data(data_file, data)
        add_bubble("assistant", "Chat cleared. What would you like help with?")

    tab_assistant = ft.Column([
        ft.Text("Dating Assistant", color=ORANGE, size=20, weight=ft.FontWeight.BOLD),
        chat_list,
        ft.Row([
            ft.ElevatedButton("Add Screenshot", style=BTN_GREY,
                              on_click=lambda e: file_picker.pick_files(
                                  allowed_extensions=["jpg", "jpeg", "png", "webp", "gif"],
                                  allow_multiple=False)),
            img_label,
        ], spacing=8),
        ft.Row([user_input], spacing=0),
        ft.Row([
            ft.ElevatedButton("Clear", style=BTN_GREY, width=80, on_click=clear_chat),
            send_btn,
        ], spacing=8),
    ], expand=True, spacing=6)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Icebreakers
    # ══════════════════════════════════════════════════════════════════════════

    ice_context = _field(
        hint_text='e.g. "coffee shop, she is reading" or "Hinge match, loves hiking & dogs"',
        multiline=True,
        min_lines=2,
        max_lines=3,
    )
    ice_result = ft.ListView(expand=True, spacing=4, padding=ft.padding.all(4))

    def generate_opener(kind: str):
        api_key = data.get("api_key", "").strip()
        provider = data.get("provider", "gemini")
        if not api_key:
            show_alert("API Key Required",
                       f"Please add your {PROVIDER_LABELS.get(provider, provider)} API key in Settings first.")
            return

        ctx = (ice_context.value or "").strip() or "No specific context provided."
        prompts = {
            "app": (
                f"Generate 3 creative, genuine opening messages for a dating app. "
                f"Context: {ctx}\n"
                "Make them conversational and authentic — not cheesy. "
                "Vary the tone (playful / thoughtful / witty)."
            ),
            "inperson": (
                f"Generate 3 natural in-person icebreakers. Context: {ctx}\n"
                "Keep them casual, confident, and easy to deliver naturally. "
                "Avoid anything corny. Include a brief note on delivery for each."
            ),
            "date": (
                f"Suggest 5 creative date ideas. Context: {ctx}\n"
                "Mix low-key and more adventurous options. "
                "Include free/cheap options alongside others."
            ),
        }

        ice_result.controls.clear()
        ice_result.controls.append(ft.Text("Generating ideas…", color="#888888", size=14))
        page.update()

        def on_resp(resp_text, error):
            ice_result.controls.clear()
            ice_result.controls.append(
                ft.Text(error or resp_text, color="#1E1E1E", size=14, selectable=True)
            )
            page.update()

        call_ai(provider, api_key, [{"role": "user", "content": prompts[kind]}],
                SYSTEM_PROMPT, on_resp)

    tab_icebreakers = ft.Column([
        ft.Text("Icebreakers & Openers", color=ORANGE, size=20, weight=ft.FontWeight.BOLD),
        ft.Text("Describe the situation or person (optional):", color="#666666", size=13),
        ice_context,
        ft.Row([
            ft.ElevatedButton("App Opener",  expand=True, style=BTN_ORANGE,
                              on_click=lambda e: generate_opener("app")),
            ft.ElevatedButton("In-Person",   expand=True, style=BTN_RED,
                              on_click=lambda e: generate_opener("inperson")),
            ft.ElevatedButton("Date Ideas",  expand=True, style=BTN_GREEN,
                              on_click=lambda e: generate_opener("date")),
        ], spacing=6),
        ice_result,
    ], expand=True, spacing=10)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Track
    # ══════════════════════════════════════════════════════════════════════════

    track_note = _field(
        hint_text="What happened? What did you try? (optional)",
        multiline=True,
        min_lines=2,
        max_lines=3,
    )
    wins_lbl  = ft.Text("Wins: 0",     color=GREEN, size=15, weight=ft.FontWeight.BOLD)
    fails_lbl = ft.Text("Learning: 0", color=RED,   size=15, weight=ft.FontWeight.BOLD)
    track_list = ft.ListView(expand=True, spacing=4, padding=ft.padding.all(4))

    def refresh_track():
        wins  = len(data.get("successes", []))
        fails = len(data.get("failures",  []))
        wins_lbl.value  = f"Wins: {wins}"
        fails_lbl.value = f"Learning: {fails}"
        track_list.controls.clear()
        all_entries = (
            [("W", e) for e in data.get("successes", [])] +
            [("L", e) for e in data.get("failures",  [])]
        )
        all_entries.sort(key=lambda x: x[1].get("date", ""), reverse=True)
        for tag, entry in all_entries[:25]:
            is_win = tag == "W"
            track_list.controls.append(ft.Text(
                f"{'WIN' if is_win else 'LEARN'}  {entry.get('date', '')}  —  "
                f"{entry.get('note') or '(no note)'}",
                color=GREEN if is_win else RED,
                size=12,
            ))
        page.update()

    def log_result(kind: str):
        note = (track_note.value or "").strip()
        track_note.value = ""
        key = "successes" if kind == "success" else "failures"
        data.setdefault(key, []).append({
            "note": note,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        save_data(data_file, data)
        refresh_track()

    tab_track = ft.Column([
        ft.Text("Track Your Results", color=ORANGE, size=20, weight=ft.FontWeight.BOLD),
        track_note,
        ft.Row([
            ft.ElevatedButton("Log a Win!",    expand=True, style=BTN_GREEN,
                              on_click=lambda e: log_result("success")),
            ft.ElevatedButton("Didn't Work",   expand=True, style=BTN_RED,
                              on_click=lambda e: log_result("failure")),
        ], spacing=8),
        ft.Row([wins_lbl, fails_lbl], spacing=20),
        track_list,
    ], expand=True, spacing=8)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — Motivation
    # ══════════════════════════════════════════════════════════════════════════

    quote_txt   = ft.Text("", color="#2E2E2E", size=15, text_align=ft.TextAlign.CENTER)
    therapy_txt = ft.Text("", color="#4C1A1E", size=13, text_align=ft.TextAlign.CENTER)

    def shuffle_quote(e=None):
        quote_txt.value = random.choice(MOTIVATIONAL_QUOTES)
        page.update()

    def shuffle_therapy(e=None):
        therapy_txt.value = random.choice(THERAPY_TIPS)
        page.update()

    tab_motivation = ft.Column([
        ft.Text("Get Out There!", color=ORANGE, size=22, weight=ft.FontWeight.BOLD),
        ft.Container(
            content=ft.Column(
                [quote_txt],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#FFF5EE",
            border_radius=12,
            padding=14,
            height=160,
            expand=False,
        ),
        ft.ElevatedButton("Shuffle Inspiration", expand=True, style=BTN_ORANGE,
                          on_click=shuffle_quote),
        ft.Text("Therapist's Corner", color=RED, size=16, weight=ft.FontWeight.BOLD),
        ft.Container(
            content=ft.Column(
                [therapy_txt],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor="#FFF0F1",
            border_radius=12,
            padding=14,
            height=150,
            expand=False,
        ),
        ft.ElevatedButton("New Insight", expand=True, style=BTN_RED,
                          on_click=shuffle_therapy),
    ], spacing=14, scroll=ft.ScrollMode.AUTO)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — Settings
    # ══════════════════════════════════════════════════════════════════════════

    api_key_input = _field(hint_text="Get free key at aistudio.google.com",
                           password=True, can_reveal_password=True, text_size=13)
    style_input   = _field(
        hint_text='e.g. "I am a 28M, funny and laid back, looking for something serious…"',
        multiline=True, min_lines=3, max_lines=5, text_size=13,
    )
    settings_status = ft.Text("", color=GREEN, size=13)
    provider_note   = ft.Text("", color="#339955", size=12)

    btn_gemini = ft.ElevatedButton("Gemini", expand=True, style=BTN_ORANGE,
                                   on_click=lambda e: set_provider("gemini"))
    btn_claude = ft.ElevatedButton("Claude", expand=True, style=BTN_GREY,
                                   on_click=lambda e: set_provider("claude"))
    btn_openai = ft.ElevatedButton("OpenAI", expand=True, style=BTN_GREY,
                                   on_click=lambda e: set_provider("openai"))
    _prov_btns = {"gemini": btn_gemini, "claude": btn_claude, "openai": btn_openai}

    def set_provider(prov: str, save: bool = True):
        data["provider"] = prov
        notes = {
            "gemini": "Free tier available — get key at aistudio.google.com",
            "claude": "Paid API — console.anthropic.com",
            "openai": "Paid API — platform.openai.com",
        }
        provider_note.value = notes.get(prov, "")
        api_key_input.hint_text = PROVIDER_HINTS.get(prov, "")
        for p, btn in _prov_btns.items():
            btn.style = BTN_ORANGE if p == prov else BTN_GREY
        if save:
            save_data(data_file, data)
        page.update()

    def save_api_key(e):
        data["api_key"] = (api_key_input.value or "").strip()
        save_data(data_file, data)
        settings_status.value = "API key saved!" if data["api_key"] else "API key cleared."
        page.update()

    def save_style_profile(e):
        data["style_profile"] = (style_input.value or "").strip()
        save_data(data_file, data)
        settings_status.value = "Style profile saved!"
        page.update()

    tab_settings = ft.Column([
        ft.Text("Settings", color=ORANGE, size=20, weight=ft.FontWeight.BOLD),
        ft.Text("AI Provider:", color="#555555", size=13),
        ft.Row([btn_gemini, btn_claude, btn_openai], spacing=6),
        provider_note,
        ft.Text("API Key:", color="#555555", size=13),
        api_key_input,
        ft.ElevatedButton("Save Settings", expand=True, style=BTN_ORANGE,
                          on_click=save_api_key),
        settings_status,
        ft.Text("My Style Profile", color=ORANGE, size=15, weight=ft.FontWeight.BOLD),
        ft.Text("Tell the assistant about you and what you are looking for:",
                color="#666666", size=12),
        style_input,
        ft.ElevatedButton("Save Style Profile", expand=True, style=BTN_RED,
                          on_click=save_style_profile),
    ], spacing=10, scroll=ft.ScrollMode.AUTO)

    # ══════════════════════════════════════════════════════════════════════════
    # Navigation
    # ══════════════════════════════════════════════════════════════════════════

    TABS = [tab_assistant, tab_icebreakers, tab_track, tab_motivation, tab_settings]

    def switch_tab(idx: int):
        for i, t in enumerate(TABS):
            t.visible = (i == idx)
        page.update()

    nav_bar = ft.NavigationBar(
        selected_index=0,
        bgcolor="#F2F2F2",
        indicator_color=ORANGE,
        on_change=lambda e: switch_tab(e.control.selected_index),
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.CHAT_BUBBLE_OUTLINE,
                                        selected_icon=ft.Icons.CHAT_BUBBLE,
                                        label="Assistant"),
            ft.NavigationBarDestination(icon=ft.Icons.LIGHTBULB_OUTLINE,
                                        selected_icon=ft.Icons.LIGHTBULB,
                                        label="Icebreakers"),
            ft.NavigationBarDestination(icon=ft.Icons.TRACK_CHANGES_OUTLINED,
                                        selected_icon=ft.Icons.TRACK_CHANGES,
                                        label="Track"),
            ft.NavigationBarDestination(icon=ft.Icons.STAR_OUTLINE,
                                        selected_icon=ft.Icons.STAR,
                                        label="Motivate"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS_OUTLINED,
                                        selected_icon=ft.Icons.SETTINGS,
                                        label="Settings"),
        ],
    )

    # Only chat tab visible initially
    for i, t in enumerate(TABS):
        t.visible = (i == 0)

    # ── Initialise state ──────────────────────────────────────────────────────

    set_provider(data.get("provider", "gemini"), save=False)
    if data.get("api_key"):
        api_key_input.value = data["api_key"]
    if data.get("style_profile"):
        style_input.value = data["style_profile"]

    shuffle_quote()
    shuffle_therapy()
    refresh_track()

    add_bubble("assistant",
        "Hi! I'm your Dating Assistant.\n\n"
        "I can help with message ideas, conversation tips, icebreakers "
        "for apps or in person, and date suggestions.\n\n"
        "Go to Settings to choose your AI provider (Gemini is free!) "
        "and add your API key, then ask me anything!")

    # ── Root layout ───────────────────────────────────────────────────────────

    page.add(
        ft.Column([
            ft.Container(
                content=ft.Stack(TABS),
                expand=True,
                padding=ft.padding.symmetric(horizontal=10, vertical=8),
            ),
            nav_bar,
        ], expand=True, spacing=0)
    )


if __name__ == "__main__":
    ft.app(target=main)
