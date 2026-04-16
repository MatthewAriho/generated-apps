"""Transaction auto-classifier - hybrid keyword + Gemini API approach.

Flow:
1. Keyword rules match instantly, offline (covers ~80% of common merchants).
2. If no keyword match and online + Gemini API key set,
   send description to Gemini Flash (free tier) for classification.
3. Falls back to "Other" if both fail.

Gemini free tier: 15 RPM, 1M tokens/day (gemini-2.0-flash).
API key from: aistudio.google.com (free, no billing required).
Stored in app settings under key "gemini_api_key".

Uses plain `requests` (already in requirements) - no extra SDK needed.
"""
from __future__ import annotations

# ------------------------------------------------------------------ keyword rules
# Each entry: (pattern_fragments, category)
# All lowercase matching. First match wins.
_KEYWORD_RULES: list[tuple[list[str], str]] = [
    # Food & Dining
    (["tim horton", "timhorton", "tims"],               "Food & Dining"),
    (["starbucks", "second cup", "coffee"],              "Food & Dining"),
    (["grocery", "groceries", "sobeys", "metro", "loblaws",
      "no frills", "food basics", "walmart grocery",
      "freshco", "superstore", "costco food"],           "Food & Dining"),
    (["whole foods", "trader joe"],                      "Food & Dining"),

    # Restaurants
    (["mcdonald", "burger king", "wendy", "kfc", "popeye",
      "subway", "chipotle", "five guys", "harvey",
      "pizza", "domino", "pizza hut", "swiss chalet",
      "boston pizza", "east side mario", "a&w"],         "Restaurants"),
    (["restaurant", "bistro", "grill", "sushi", "ramen",
      "diner", "eatery", "barbeque", "bbq", "steakhouse"],  "Restaurants"),

    # Rides
    (["uber", "lyft", "taxify", "bolt ride"],            "Rides (Uber/Lyft)"),
    (["taxi", "cab"],                                    "Rides (Uber/Lyft)"),

    # Transportation
    (["gas", "petro", "shell", "esso", "circle k", "husky",
      "pioneer petro", "ultramar"],                      "Transportation"),
    (["parking", "park n go", "impark", "indigo park"],  "Transportation"),
    (["transit", "ttc", "octo", "presto", "go train",
      "via rail", "bus pass", "metro card"],             "Transportation"),
    (["airline", "air canada", "westjet", "flight",
      "porter air"],                                     "Travel"),

    # Nightlife / Bars
    (["bar ", "pub ", "nightclub", "lounge", "lcbo", "beer store",
      "saq ", "bc liquor", "liquor", "alcohol", "beer", "wine store",
      "club ", "shots ", "brewery", "cocktail"],         "Nightlife / Bars"),

    # Shopping
    (["amazon", "amzn"],                                 "Shopping"),
    (["best buy", "bestbuy", "apple store", "the source",
      "staples", "future shop"],                         "Shopping"),
    (["zara", "h&m", "uniqlo", "forever 21", "gap ", "old navy",
      "winners", "marshalls", "tjmaxx", "nordstrom",
      "sport chek", "lululemon"],                        "Shopping"),
    (["shopify", "etsy", "ebay"],                        "Shopping"),

    # Subscriptions
    (["netflix", "spotify", "apple music", "youtube premium",
      "disney+", "disney plus", "amazon prime", "hulu",
      "crave", "paramount", "deezer"],                   "Subscriptions"),
    (["icloud", "google storage", "dropbox", "microsoft 365",
      "adobe", "canva", "notion"],                       "Subscriptions"),

    # Utilities
    (["hydro", "enbridge", "rogers", "bell canada", "telus",
      "fido", "virgin mobile", "koodo", "chatr",
      "electric", "electricity", "gas bill", "water bill",
      "internet", "wifi bill"],                          "Utilities"),

    # Healthcare
    (["pharmacy", "shoppers drug", "rexall", "london drug",
      "cvs", "walgreen", "guardian pharmacy"],           "Healthcare"),
    (["clinic", "hospital", "dental", "dentist", "physio",
      "chiro", "optometrist", "doctor", "medical"],      "Healthcare"),

    # ATM / Cash
    (["atm", "cash withdrawal", "withdrawal"],           "ATM / Cash"),

    # Income
    (["payroll", "paycheck", "salary", "paycheque", "direct deposit",
      "e-transfer receive", "transfer in"],              "Salary / Income"),
    (["freelance", "invoice", "client payment"],         "Freelance"),
]

_CATEGORIES = [
    "Food & Dining", "Restaurants", "Rides (Uber/Lyft)", "Transportation",
    "Travel", "Nightlife / Bars", "Shopping", "Subscriptions", "Utilities",
    "Healthcare", "ATM / Cash", "Salary / Income", "Freelance", "Entertainment",
    "Other",
]


def classify_keyword(description: str) -> str | None:
    """Return category from keyword rules, or None if no match."""
    if not description:
        return None
    lower = description.lower()
    for fragments, category in _KEYWORD_RULES:
        if any(f in lower for f in fragments):
            return category
    return None


# ------------------------------------------------------------------ Gemini API
_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

_SYSTEM_PROMPT = (
    "You classify financial transaction descriptions into spending categories. "
    "Reply with exactly ONE category from this list and nothing else:\n"
    + ", ".join(_CATEGORIES)
)


def classify_gemini(description: str, api_key: str) -> str | None:
    """Classify via Gemini 2.0 Flash free tier.

    Returns category string or None on failure.
    Uses requests (already in buildozer requirements).
    """
    if not description or not api_key:
        return None
    try:
        import requests
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": _SYSTEM_PROMPT},
                        {"text": f"Transaction: {description}"},
                    ]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 20,
                "temperature": 0.0,
            },
        }
        resp = requests.post(
            _GEMINI_URL,
            params={"key": api_key},
            json=payload,
            timeout=8,
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )
        if text in _CATEGORIES:
            return text
        # Fuzzy match
        lower = text.lower()
        for c in _CATEGORIES:
            if c.lower() in lower or lower in c.lower():
                return c
        return None
    except Exception:
        return None


# ------------------------------------------------------------------ public API
def auto_classify(description: str, force_api: bool = False) -> str:
    """Main classification entry point.

    1. Try keyword rules (instant, offline).
    2. If no match (or force_api=True) and Gemini API key set + online,
       call Gemini Flash.
    3. Return 'Other' as fallback.
    """
    if not force_api:
        result = classify_keyword(description)
        if result:
            return result

    try:
        api_key = _get_gemini_api_key()
        if api_key:
            from utils.connectivity import is_online
            if is_online():
                result = classify_gemini(description, api_key)
                if result:
                    return result
    except Exception:
        pass

    keyword_result = classify_keyword(description)
    return keyword_result or "Other"


def _get_gemini_api_key() -> str:
    """Read Gemini API key from app settings store."""
    try:
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
        store = JsonStore(os.path.join(base, "settings.json"))
        if store.exists("gemini"):
            return store.get("gemini").get("api_key", "")
    except Exception:
        pass
    return ""
