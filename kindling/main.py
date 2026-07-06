"""Kindling — FastAPI backend for dating assistant PWA."""
from __future__ import annotations

import random
from datetime import datetime

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

_BASE = Path(__file__).resolve().parent
_STATIC = _BASE / "static"

from core.ai import call_ai, test_connection
from core.content import (
    SYSTEM_PROMPT, MOTIVATIONAL_QUOTES, THERAPY_TIPS,
    ICEBREAKER_PROMPTS, PROVIDERS, PROVIDER_LABELS, PROVIDER_HINTS,
)
from core.data import load_data, save_data, new_chat_session

app = FastAPI(title="Kindling")


# ── Models ────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    image_b64: str | None = None
    image_type: str | None = None  # e.g. "image/jpeg"


class IcebreakerRequest(BaseModel):
    kind: str  # "app", "inperson", "date"
    context: str = ""


class TrackRequest(BaseModel):
    kind: str  # "success" or "failure"
    note: str = ""


class TrackEditRequest(BaseModel):
    kind: str
    date: str
    old_note: str
    new_note: str


class TrackDeleteRequest(BaseModel):
    kind: str
    date: str
    note: str


class SettingsRequest(BaseModel):
    provider: str | None = None
    api_key: str | None = None


class ProfileCreate(BaseModel):
    name: str


class ProfileEdit(BaseModel):
    name: str
    bio: str


class ProfileDelete(BaseModel):
    name: str


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "app": "kindling"}


# ── Chat ──────────────────────────────────────────────────────────────────────

@app.post("/api/chat")
def chat(req: ChatRequest):
    data = load_data()
    api_key = data.get("api_key", "").strip()
    provider = data.get("provider", "gemini")

    if not api_key:
        raise HTTPException(400, f"No API key set. Add your {PROVIDER_LABELS.get(provider, provider)} key in Settings.")

    # Build message content
    content = []
    if req.image_b64 and req.image_type:
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": req.image_type, "data": req.image_b64},
        })

    # Prepend style profile on first message
    history = list(data.get("conversation_history", []))
    active = data.get("active_profile", "")
    style = data.get("profiles", {}).get(active, "").strip()
    msg_text = req.message
    if style and not history:
        msg_text = f"[About me: {style}]\n\n{req.message}"
    content.append({"type": "text", "text": msg_text})

    messages = history + [{"role": "user", "content": content}]

    try:
        reply = call_ai(provider, api_key, messages, SYSTEM_PROMPT)
    except Exception as e:
        raise HTTPException(502, _parse_error(str(e)))

    # Save to history (keep last 20)
    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": reply})
    if len(history) > 20:
        history = history[-20:]
    data["conversation_history"] = history
    save_data(data)

    return {"reply": reply}


@app.post("/api/chat/clear")
def chat_clear():
    data = load_data()
    data["conversation_history"] = []
    save_data(data)
    return {"status": "cleared"}


@app.post("/api/chat/new")
def chat_new():
    """Archive current chat and start fresh."""
    data = load_data()
    new_id = new_chat_session(data)
    return {"status": "created", "chat_id": new_id}


@app.get("/api/chat/history")
def chat_history_list():
    """List all saved chat sessions (most recent first)."""
    data = load_data()
    sessions = data.get("chat_sessions", [])
    return {"sessions": [{"id": s["id"], "title": s["title"], "date": s["date"], "count": len(s["messages"])} for s in sessions]}


@app.get("/api/chat/history/{chat_id}")
def chat_history_get(chat_id: str):
    """Get full messages for a specific chat session."""
    data = load_data()
    for s in data.get("chat_sessions", []):
        if s["id"] == chat_id:
            return {"session": s}
    raise HTTPException(404, "Chat session not found")


@app.post("/api/chat/history/{chat_id}/resume")
def chat_history_resume(chat_id: str):
    """Resume a previous chat — makes it the active conversation."""
    data = load_data()
    # Archive current chat first
    if data.get("conversation_history"):
        new_chat_session(data)
        data = load_data()
    # Find and load the session
    sessions = data.get("chat_sessions", [])
    for i, s in enumerate(sessions):
        if s["id"] == chat_id:
            data["conversation_history"] = s["messages"]
            data["active_chat_id"] = chat_id
            sessions.pop(i)
            save_data(data)
            return {"status": "resumed", "messages": s["messages"]}
    raise HTTPException(404, "Chat session not found")


class ChatDeleteRequest(BaseModel):
    chat_id: str


@app.delete("/api/chat/history")
def chat_history_delete(req: ChatDeleteRequest):
    """Delete a saved chat session."""
    data = load_data()
    sessions = data.get("chat_sessions", [])
    data["chat_sessions"] = [s for s in sessions if s["id"] != req.chat_id]
    save_data(data)
    return {"status": "deleted"}


# ── Icebreakers ───────────────────────────────────────────────────────────────

@app.post("/api/icebreakers")
def icebreakers(req: IcebreakerRequest):
    data = load_data()
    api_key = data.get("api_key", "").strip()
    provider = data.get("provider", "gemini")

    if not api_key:
        raise HTTPException(400, "No API key set.")

    if req.kind not in ICEBREAKER_PROMPTS:
        raise HTTPException(400, f"Invalid kind: {req.kind}")

    ctx = req.context or "No specific context provided."
    prompt = ICEBREAKER_PROMPTS[req.kind].format(context=ctx)
    messages = [{"role": "user", "content": prompt}]

    try:
        reply = call_ai(provider, api_key, messages, SYSTEM_PROMPT)
    except Exception as e:
        raise HTTPException(502, _parse_error(str(e)))

    return {"reply": reply}


# ── Track ─────────────────────────────────────────────────────────────────────

@app.get("/api/track")
def track_list():
    data = load_data()
    successes = [{"kind": "success", **e} for e in data.get("successes", [])]
    failures = [{"kind": "failure", **e} for e in data.get("failures", [])]
    all_entries = successes + failures
    all_entries.sort(key=lambda x: x.get("date", ""), reverse=True)
    wins = len(data.get("successes", []))
    fails = len(data.get("failures", []))
    return {"entries": all_entries[:30], "wins": wins, "fails": fails}


@app.post("/api/track")
def track_log(req: TrackRequest):
    data = load_data()
    entry = {"note": req.note, "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
    key = "successes" if req.kind == "success" else "failures"
    data.setdefault(key, []).append(entry)
    save_data(data)
    return {"status": "logged", "kind": req.kind}


@app.put("/api/track")
def track_edit(req: TrackEditRequest):
    data = load_data()
    key = "successes" if req.kind == "success" else "failures"
    for e in data.get(key, []):
        if e.get("date") == req.date and e.get("note") == req.old_note:
            e["note"] = req.new_note
            save_data(data)
            return {"status": "updated"}
    raise HTTPException(404, "Entry not found")


@app.delete("/api/track")
def track_delete(req: TrackDeleteRequest):
    data = load_data()
    key = "successes" if req.kind == "success" else "failures"
    lst = data.get(key, [])
    for i, e in enumerate(lst):
        if e.get("date") == req.date and e.get("note") == req.note:
            lst.pop(i)
            save_data(data)
            return {"status": "deleted"}
    raise HTTPException(404, "Entry not found")


# ── Motivate ──────────────────────────────────────────────────────────────────

@app.get("/api/motivate/quote")
def motivate_quote():
    return {"quote": random.choice(MOTIVATIONAL_QUOTES)}


@app.get("/api/motivate/therapy")
def motivate_therapy():
    return {"tip": random.choice(THERAPY_TIPS)}


# ── Settings ──────────────────────────────────────────────────────────────────

@app.get("/api/settings")
def settings_get():
    data = load_data()
    return {
        "provider": data.get("provider", "gemini"),
        "has_key": bool(data.get("api_key", "").strip()),
        "active_profile": data.get("active_profile", "Default"),
        "profiles": data.get("profiles", {}),
        "providers": PROVIDERS,
        "provider_labels": PROVIDER_LABELS,
        "provider_hints": PROVIDER_HINTS,
    }


@app.post("/api/settings")
def settings_update(req: SettingsRequest):
    data = load_data()
    if req.provider is not None:
        if req.provider not in PROVIDERS:
            raise HTTPException(400, f"Invalid provider: {req.provider}")
        data["provider"] = req.provider
    if req.api_key is not None:
        data["api_key"] = req.api_key
    save_data(data)
    return {"status": "saved"}


@app.post("/api/settings/test")
def settings_test():
    data = load_data()
    api_key = data.get("api_key", "").strip()
    provider = data.get("provider", "gemini")
    if not api_key:
        raise HTTPException(400, "No API key set.")
    try:
        test_connection(provider, api_key)
        return {"status": "connected"}
    except Exception as e:
        raise HTTPException(502, _parse_error(str(e)))


# ── Profiles ──────────────────────────────────────────────────────────────────

@app.post("/api/profiles")
def profile_create(req: ProfileCreate):
    data = load_data()
    if not req.name.strip():
        raise HTTPException(400, "Profile name required")
    data.setdefault("profiles", {})[req.name.strip()] = ""
    data["active_profile"] = req.name.strip()
    save_data(data)
    return {"status": "created"}


@app.put("/api/profiles")
def profile_edit(req: ProfileEdit):
    data = load_data()
    if req.name not in data.get("profiles", {}):
        raise HTTPException(404, "Profile not found")
    data["profiles"][req.name] = req.bio
    save_data(data)
    return {"status": "updated"}


@app.delete("/api/profiles")
def profile_delete(req: ProfileDelete):
    data = load_data()
    profiles = data.get("profiles", {})
    if len(profiles) <= 1:
        raise HTTPException(400, "Cannot delete the last profile")
    profiles.pop(req.name, None)
    if data.get("active_profile") == req.name:
        data["active_profile"] = next(iter(profiles))
    save_data(data)
    return {"status": "deleted"}


@app.post("/api/profiles/switch")
def profile_switch(req: ProfileCreate):
    data = load_data()
    if req.name not in data.get("profiles", {}):
        raise HTTPException(404, "Profile not found")
    data["active_profile"] = req.name
    save_data(data)
    return {"status": "switched"}


# ── Static files & PWA ────────────────────────────────────────────────────────

@app.get("/manifest.json")
def manifest():
    return FileResponse(_STATIC / "manifest.json", media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    return FileResponse(
        _STATIC / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/kindling/", "Cache-Control": "no-cache"},
    )


@app.get("/")
def index():
    return FileResponse(_STATIC / "index.html")


@app.get("/api/debug/pwa")
def debug_pwa():
    """Check all PWA install requirements."""
    import json as _json
    issues = []
    # Check manifest
    mpath = _STATIC / "manifest.json"
    if not mpath.exists():
        issues.append("manifest.json missing")
    else:
        m = _json.loads(mpath.read_text())
        for field in ["name", "short_name", "start_url", "scope", "display", "icons"]:
            if field not in m:
                issues.append(f"manifest missing '{field}'")
        icons = m.get("icons", [])
        sizes = [i.get("sizes") for i in icons if i.get("purpose", "any") == "any"]
        if "192x192" not in sizes:
            issues.append("missing 192x192 icon")
        if "512x512" not in sizes:
            issues.append("missing 512x512 icon")
    # Check SW
    if not (_STATIC / "sw.js").exists():
        issues.append("sw.js missing")
    # Check icons exist
    for name in ["icon-192.png", "icon-512.png", "icon-192-maskable.png", "icon-512-maskable.png"]:
        if not (_STATIC / name).exists():
            issues.append(f"{name} missing")
    return {"installable": len(issues) == 0, "issues": issues}


app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_error(error_text: str) -> str:
    e = error_text.lower()
    if "401" in e or "403" in e or "unauthorized" in e or "invalid" in e:
        return "Invalid API key. Check Settings."
    if "429" in e or "rate" in e or "quota" in e:
        return "Rate limit reached. Wait a moment and retry."
    if any(c in e for c in ("500", "502", "503")):
        return "Service error. Try again."
    if "timeout" in e or "timed out" in e or "connection" in e:
        return "Connection failed. Check your internet."
    return f"Error: {error_text[:100]}"
