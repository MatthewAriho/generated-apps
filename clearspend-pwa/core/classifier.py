"""Transaction auto-classifier — keyword rules + Gemini API fallback."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

_KEYWORD_RULES: list[tuple[list[str], str]] = [
    (["tim horton", "timhorton", "tims"],               "Food & Dining"),
    (["starbucks", "second cup", "coffee"],              "Food & Dining"),
    (["grocery", "groceries", "sobeys", "metro", "loblaws",
      "no frills", "food basics", "walmart grocery",
      "freshco", "superstore", "costco food"],           "Food & Dining"),
    (["whole foods", "trader joe"],                      "Food & Dining"),
    (["mcdonald", "burger king", "wendy", "kfc", "popeye",
      "subway", "chipotle", "five guys", "harvey",
      "pizza", "domino", "pizza hut", "swiss chalet",
      "boston pizza", "east side mario", "a&w"],         "Restaurants"),
    (["restaurant", "bistro", "grill", "sushi", "ramen",
      "diner", "eatery", "barbeque", "bbq", "steakhouse"],  "Restaurants"),
    (["uber", "lyft", "taxify", "bolt ride"],            "Rides (Uber/Lyft)"),
    (["taxi", "cab"],                                    "Rides (Uber/Lyft)"),
    (["gas", "petro", "shell", "esso", "circle k", "husky",
      "pioneer petro", "ultramar"],                      "Transportation"),
    (["parking", "park n go", "impark", "indigo park"],  "Transportation"),
    (["transit", "ttc", "octo", "presto", "go train",
      "via rail", "bus pass", "metro card"],             "Transportation"),
    (["airline", "air canada", "westjet", "flight",
      "porter air"],                                     "Travel"),
    (["bar ", "pub ", "nightclub", "lounge", "lcbo", "beer store",
      "saq ", "bc liquor", "liquor", "alcohol", "beer", "wine store",
      "club ", "shots ", "brewery", "cocktail"],         "Nightlife / Bars"),
    (["amazon", "amzn"],                                 "Shopping"),
    (["best buy", "bestbuy", "apple store", "the source",
      "staples", "future shop"],                         "Shopping"),
    (["zara", "h&m", "uniqlo", "forever 21", "gap ", "old navy",
      "winners", "marshalls", "tjmaxx", "nordstrom",
      "sport chek", "lululemon"],                        "Shopping"),
    (["shopify", "etsy", "ebay"],                        "Shopping"),
    (["netflix", "spotify", "apple music", "youtube premium",
      "disney+", "disney plus", "amazon prime", "hulu",
      "crave", "paramount", "deezer"],                   "Subscriptions"),
    (["icloud", "google storage", "dropbox", "microsoft 365",
      "adobe", "canva", "notion"],                       "Subscriptions"),
    (["hydro", "enbridge", "rogers", "bell canada", "telus",
      "fido", "virgin mobile", "koodo", "chatr",
      "electric", "electricity", "gas bill", "water bill",
      "internet", "wifi bill"],                          "Utilities"),
    (["pharmacy", "shoppers drug", "rexall", "london drug",
      "cvs", "walgreen", "guardian pharmacy"],           "Healthcare"),
    (["clinic", "hospital", "dental", "dentist", "physio",
      "chiro", "optometrist", "doctor", "medical"],      "Healthcare"),
    (["atm", "cash withdrawal", "withdrawal"],           "ATM / Cash"),
    (["payroll", "paycheck", "salary", "paycheque", "direct deposit",
      "e-transfer receive", "transfer in"],              "Salary / Income"),
    (["freelance", "invoice", "client payment"],         "Freelance"),
]

CATEGORIES = [
    "Food & Dining", "Restaurants", "Rides (Uber/Lyft)", "Transportation",
    "Travel", "Nightlife / Bars", "Shopping", "Subscriptions", "Utilities",
    "Healthcare", "ATM / Cash", "Salary / Income", "Freelance", "Entertainment",
    "Rent / Housing", "Investment", "Transfer", "Other",
]

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

_SYSTEM_PROMPT = (
    "You classify financial transaction descriptions into spending categories. "
    "Reply with exactly ONE category from this list and nothing else:\n"
    + ", ".join(CATEGORIES)
)


def classify_keyword(description: str) -> str | None:
    if not description:
        return None
    lower = description.lower()
    for fragments, category in _KEYWORD_RULES:
        if any(f in lower for f in fragments):
            return category
    return None


def classify_gemini(description: str, api_key: str) -> str | None:
    if not description or not api_key:
        return None
    try:
        payload = json.dumps({
            "contents": [{"parts": [
                {"text": _SYSTEM_PROMPT},
                {"text": f"Transaction: {description}"},
            ]}],
            "generationConfig": {"maxOutputTokens": 20, "temperature": 0.0},
        }).encode()
        req = urllib.request.Request(
            f"{_GEMINI_URL}?key={api_key}",
            data=payload, method="POST",
        )
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "").strip()
        )
        if text in CATEGORIES:
            return text
        lower = text.lower()
        for c in CATEGORIES:
            if c.lower() in lower or lower in c.lower():
                return c
        return None
    except Exception:
        return None


def auto_classify(description: str, api_key: str = "", force_api: bool = False) -> str:
    if not force_api:
        result = classify_keyword(description)
        if result:
            return result
    if api_key:
        result = classify_gemini(description, api_key)
        if result:
            return result
    keyword_result = classify_keyword(description)
    return keyword_result or "Other"
