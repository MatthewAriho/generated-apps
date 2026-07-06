"""Data persistence for Kindling."""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime

DATA_DIR = os.environ.get("KINDLING_DATA_DIR", "/data")
DATA_FILE = os.path.join(DATA_DIR, "kindling_data.json")

DEFAULT_DATA = {
    "api_key": "",
    "provider": "gemini",
    "active_profile": "Default",
    "profiles": {"Default": ""},
    "conversation_history": [],
    "active_chat_id": None,
    "chat_sessions": [],
    "successes": [],
    "failures": [],
}


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_data() -> dict:
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
            # Migrate legacy style_profile key
            if "style_profile" in data and "profiles" not in data:
                old = data.pop("style_profile", "") or ""
                data["profiles"] = {"Default": old}
                data["active_profile"] = "Default"
            elif "profiles" not in data:
                data["profiles"] = {"Default": ""}
                data["active_profile"] = "Default"
            if "active_profile" not in data:
                data["active_profile"] = next(iter(data["profiles"]), "Default")
            # Migrate: add chat_sessions if missing
            if "chat_sessions" not in data:
                data["chat_sessions"] = []
                data["active_chat_id"] = None
            return data
    except Exception:
        pass
    return dict(DEFAULT_DATA)


def save_data(data: dict):
    _ensure_dir()
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def new_chat_session(data: dict) -> str:
    """Archive current conversation and start fresh. Returns new session ID."""
    # Save current conversation as a session if it has messages
    history = data.get("conversation_history", [])
    if history:
        session_id = data.get("active_chat_id") or str(uuid.uuid4())[:8]
        # Derive title from first user message
        title = "Chat"
        for msg in history:
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, str):
                    title = content[:50]
                break
        session = {
            "id": session_id,
            "title": title,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "messages": history,
        }
        data.setdefault("chat_sessions", []).insert(0, session)
        # Keep max 50 sessions
        data["chat_sessions"] = data["chat_sessions"][:50]

    # Start fresh
    new_id = str(uuid.uuid4())[:8]
    data["conversation_history"] = []
    data["active_chat_id"] = new_id
    save_data(data)
    return new_id
