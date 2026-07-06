"""Rule-based financial tips engine.

Generates actionable tips from spending data — no external API required.
"""
from __future__ import annotations
from datetime import datetime


# Each tip: (icon, title, body, severity)   severity: 'good'|'warn'|'info'
Tip = tuple[str, str, str, str]


def generate_tips(db) -> list[Tip]:
    """Return a list of tips based on current month's spending."""
    tips: list[Tip] = []
    now = datetime.now()
    ym  = now.strftime("%Y-%m")

    summary    = db.get_monthly_summary(ym)
    breakdown  = db.get_category_breakdown(ym)
    recurring  = db.get_recurring_transactions()

    income  = summary["income"]
    expense = summary["expense"]

    # ── Previous month for comparison ──────────────────────────────────
    pm = now.month - 1
    py = now.year
    if pm <= 0:
        pm = 12; py -= 1
    prev = db.get_monthly_summary(f"{py:04d}-{pm:02d}")
    prev_expense = prev["expense"]

    # ── 1. Spending vs income ratio ─────────────────────────────────────
    if income > 0:
        ratio = expense / income
        if ratio > 0.9:
            tips.append(("alert-circle-outline",
                "Spending nearly all income",
                f"You've spent {ratio*100:.0f}% of your income this month. "
                "Try to keep expenses below 80% to build a buffer.",
                "warn"))
        elif ratio < 0.5 and income > 0:
            tips.append(("check-circle-outline",
                "Great savings rate",
                f"You're spending only {ratio*100:.0f}% of your income. "
                "Consider putting the surplus toward investments or goals.",
                "good"))

    # ── 2. Month-over-month change ──────────────────────────────────────
    if prev_expense > 0 and expense > 0:
        delta_pct = (expense - prev_expense) / prev_expense * 100
        prev_label = datetime(py, pm, 1).strftime("%b")
        if delta_pct > 25:
            tips.append(("trending-up",
                f"Spending up {delta_pct:.0f}% vs {prev_label}",
                f"Your expenses rose from ${prev_expense:,.0f} to ${expense:,.0f}. "
                "Check which categories drove the increase.",
                "warn"))
        elif delta_pct < -15:
            tips.append(("trending-down",
                f"Spending down {abs(delta_pct):.0f}% vs {prev_label}",
                f"Good discipline — you spent ${abs(expense - prev_expense):,.0f} "
                f"less than {prev_label}.",
                "good"))

    # ── 3. Category-level checks ────────────────────────────────────────
    cat_map = {r["category"]: r["total"] for r in breakdown}

    dining = cat_map.get("Food & Dining", 0) + cat_map.get("Restaurants", 0)
    if income > 0 and dining / income > 0.15:
        tips.append(("silverware-fork-knife",
            f"Dining at {dining/income*100:.0f}% of income",
            f"You spent ${dining:,.0f} on food & dining. "
            "Cooking at home a few more nights could save significantly.",
            "warn"))

    entertainment = cat_map.get("Entertainment", 0) + cat_map.get("Nightlife / Bars", 0)
    if income > 0 and entertainment / income > 0.10:
        tips.append(("party-popper",
            f"Entertainment at {entertainment/income*100:.0f}% of income",
            f"${entertainment:,.0f} on entertainment & nightlife this month.",
            "info"))

    # ── 4. Subscriptions ────────────────────────────────────────────────
    subs = cat_map.get("Subscriptions", 0)
    sub_count = sum(1 for r in recurring if r.get("category") == "Subscriptions")
    if subs > 80:
        tips.append(("refresh-circle",
            f"${subs:,.0f}/mo in subscriptions",
            f"You have ~{sub_count} recurring subscriptions. "
            "Review which ones you actively use.",
            "info"))

    # ── 5. No investments this month ────────────────────────────────────
    investment_rows = db.conn.execute(
        "SELECT COUNT(*) as c FROM transactions WHERE date LIKE ? AND category='Investment'",
        (f"{ym}%",),
    ).fetchone()
    if (investment_rows["c"] == 0) and income > 500:
        tips.append(("chart-line",
            "No investments recorded this month",
            "Consider allocating even a small amount to savings or investments. "
            "The 50/30/20 rule suggests 20% toward financial goals.",
            "info"))

    # ── 6. Largest category ─────────────────────────────────────────────
    if breakdown:
        top = breakdown[0]
        if income > 0 and top["total"] / income > 0.30:
            tips.append(("podium",
                f"{top['category']} is your biggest spend",
                f"${top['total']:,.2f} ({top['total']/income*100:.0f}% of income) "
                f"went to {top['category']} this month.",
                "info"))

    # ── 7. Positive: no overspent budgets ───────────────────────────────
    statuses = db.get_budget_status(ym)
    over = [s for s in statuses if s["spent"] > s["budget"]]
    on_track = [s for s in statuses if s["spent"] <= s["budget"]]
    if statuses and not over:
        tips.append(("shield-check-outline",
            "All budgets on track",
            f"You're within budget on all {len(on_track)} categories. Keep it up!",
            "good"))
    elif over:
        names = ", ".join(s["category"] for s in over[:3])
        tips.append(("shield-alert-outline",
            f"{len(over)} budget(s) exceeded",
            f"Over budget in: {names}.",
            "warn"))

    # ── 8. No data yet ──────────────────────────────────────────────────
    if not tips:
        tips.append(("lightbulb-outline",
            "Add more transactions for tips",
            "Once you have income and expense data for this month, "
            "personalised tips will appear here.",
            "info"))

    return tips
