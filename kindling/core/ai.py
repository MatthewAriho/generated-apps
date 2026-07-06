"""AI provider integrations: Gemini, Claude, OpenAI."""
from __future__ import annotations

import json
import ssl
import time
import urllib.error
import urllib.request


def _make_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _http_post(url: str, headers: dict, payload: bytes) -> dict:
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=30, context=_make_ssl_context()) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ── Claude ────────────────────────────────────────────────────────────────────

def _call_claude(api_key: str, messages: list, system: str) -> str:
    result = _http_post(
        "https://api.anthropic.com/v1/messages",
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json.dumps({
            "model": "claude-sonnet-4-6",
            "max_tokens": 4096,
            "system": system,
            "messages": messages,
        }).encode("utf-8"),
    )
    return result["content"][0]["text"]


# ── OpenAI ────────────────────────────────────────────────────────────────────

def _call_openai(api_key: str, messages: list, system: str) -> str:
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
                    parts.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{src['media_type']};base64,{src['data']}"
                        },
                    })
            oai_msgs.append({"role": m["role"], "content": parts})
        else:
            oai_msgs.append({"role": m["role"], "content": content})

    result = _http_post(
        "https://api.openai.com/v1/chat/completions",
        {"Authorization": f"Bearer {api_key}", "content-type": "application/json"},
        json.dumps({
            "model": "gpt-4o-mini",
            "max_tokens": 4096,
            "messages": oai_msgs,
        }).encode("utf-8"),
    )
    return result["choices"][0]["message"]["content"]


# ── Gemini ────────────────────────────────────────────────────────────────────

GEMINI_MODELS = [
    ("v1", "gemini-2.0-flash-lite"),
    ("v1", "gemini-2.0-flash"),
    ("v1", "gemini-1.5-flash"),
    ("v1beta", "gemini-2.5-flash"),
    ("v1beta", "gemini-2.5-pro"),
]


def _call_gemini(api_key: str, messages: list, system: str) -> str:
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
                    parts.append({
                        "inline_data": {
                            "mime_type": src["media_type"],
                            "data": src["data"],
                        }
                    })
            contents.append({"role": role, "parts": parts})
        else:
            contents.append({"role": role, "parts": [{"text": content}]})

    body = json.dumps({
        "contents": contents,
        "systemInstruction": {"parts": [{"text": system}]},
        "generationConfig": {"maxOutputTokens": 4096},
    }).encode("utf-8")

    last_err = "Unknown error"
    for api_ver, model in GEMINI_MODELS:
        url = (
            f"https://generativelanguage.googleapis.com/{api_ver}/models/"
            f"{model}:generateContent?key={api_key}"
        )
        try:
            result = _http_post(url, {"content-type": "application/json"}, body)
            return result["candidates"][0]["content"]["parts"][0]["text"]
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

    raise RuntimeError(last_err)


# ── Unified caller ────────────────────────────────────────────────────────────

def call_ai(provider: str, api_key: str, messages: list, system: str) -> str:
    """Call the selected AI provider. Returns response text. Raises on error."""
    if provider == "claude":
        return _call_claude(api_key, messages, system)
    elif provider == "openai":
        return _call_openai(api_key, messages, system)
    else:
        return _call_gemini(api_key, messages, system)


def test_connection(provider: str, api_key: str) -> bool:
    """Quick connectivity test. Returns True if OK, raises on failure."""
    ctx = _make_ssl_context()
    if provider == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
        req = urllib.request.Request(url)
    elif provider == "claude":
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
    return True
