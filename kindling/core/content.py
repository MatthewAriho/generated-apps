"""Static content: motivational quotes, therapy tips, icebreaker prompts."""

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

ICEBREAKER_PROMPTS = {
    "app": (
        "Generate 3 creative, genuine opening messages for a dating app. "
        "Context: {context}\n"
        "Make them conversational and authentic — not cheesy. "
        "Vary the tone (playful / thoughtful / witty)."
    ),
    "inperson": (
        "Generate 3 natural in-person icebreakers. Context: {context}\n"
        "Keep them casual, confident, and easy to deliver naturally. "
        "Avoid anything corny. Include a brief delivery note for each."
    ),
    "date": (
        "Suggest 5 creative date ideas. Context: {context}\n"
        "Mix low-key and more adventurous options. "
        "Include free/cheap options alongside others."
    ),
}

PROVIDERS = ["gemini", "claude", "openai"]
PROVIDER_LABELS = {"gemini": "Gemini", "claude": "Claude", "openai": "OpenAI"}
PROVIDER_HINTS = {
    "gemini": "Get free key at aistudio.google.com",
    "claude": "sk-ant-api03-...",
    "openai": "sk-...",
}
