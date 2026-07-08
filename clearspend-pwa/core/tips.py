"""Rule-based financial tips engine."""
from __future__ import annotations

from datetime import datetime


def generate_tips(db) -> list[dict]:
    """Return tips based on current month's spending data."""
    tips: list[dict] = []
    now = datetime.now()
    ym = now.strftime("%Y-%m")

    summary = db.get_monthly_summary(ym)
    breakdown = db.get_category_breakdown(ym)
    recurring = db.get_recurring_transactions()

    income = summary["income"]
    expense = summary["expense"]

    # Previous month
    pm = now.month - 1
    py = now.year
    if pm <= 0:
        pm = 12
        py -= 1
    prev = db.get_monthly_summary(f"{py:04d}-{pm:02d}")
    prev_expense = prev["expense"]

    # 1. Spending vs income ratio
    if income > 0:
        ratio = expense / income
        if ratio > 0.9:
            tips.append({"icon": "alert-triangle", "title": "Spending nearly all income",
                         "body": f"You've spent {ratio*100:.0f}% of your income this month. Try to keep expenses below 80%.",
                         "severity": "warn"})
        elif ratio < 0.5:
            tips.append({"icon": "check-circle", "title": "Great savings rate",
                         "body": f"You're spending only {ratio*100:.0f}% of your income. Consider investing the surplus.",
                         "severity": "good"})

    # 2. Month-over-month
    if prev_expense > 0 and expense > 0:
        delta_pct = (expense - prev_expense) / prev_expense * 100
        prev_label = datetime(py, pm, 1).strftime("%b")
        if delta_pct > 25:
            tips.append({"icon": "trending-up", "title": f"Spending up {delta_pct:.0f}% vs {prev_label}",
                         "body": f"Expenses rose from ${prev_expense:,.0f} to ${expense:,.0f}.",
                         "severity": "warn"})
        elif delta_pct < -15:
            tips.append({"icon": "trending-down", "title": f"Spending down {abs(delta_pct):.0f}% vs {prev_label}",
                         "body": f"You spent ${abs(expense - prev_expense):,.0f} less than {prev_label}.",
                         "severity": "good"})

    # 3. Category checks
    cat_map = {r["category"]: r["total"] for r in breakdown}

    dining = cat_map.get("Food & Dining", 0) + cat_map.get("Restaurants", 0)
    if income > 0 and dining / income > 0.15:
        tips.append({"icon": "utensils", "title": f"Dining at {dining/income*100:.0f}% of income",
                     "body": f"You spent ${dining:,.0f} on food & dining. Cooking at home could save significantly.",
                     "severity": "warn"})

    entertainment = cat_map.get("Entertainment", 0) + cat_map.get("Nightlife / Bars", 0)
    if income > 0 and entertainment / income > 0.10:
        tips.append({"icon": "music", "title": f"Entertainment at {entertainment/income*100:.0f}% of income",
                     "body": f"${entertainment:,.0f} on entertainment & nightlife this month.",
                     "severity": "info"})

    # 4. Subscriptions
    subs = cat_map.get("Subscriptions", 0)
    sub_count = sum(1 for r in recurring if r.get("category") == "Subscriptions")
    if subs > 80:
        tips.append({"icon": "repeat", "title": f"${subs:,.0f}/mo in subscriptions",
                     "body": f"You have ~{sub_count} recurring subscriptions. Review which ones you use.",
                     "severity": "info"})

    # 5. No investments
    investment_rows = db.conn.execute(
        "SELECT COUNT(*) as c FROM transactions WHERE date LIKE ? AND category='Investment'",
        (f"{ym}%",),
    ).fetchone()
    if investment_rows["c"] == 0 and income > 500:
        tips.append({"icon": "trending-up", "title": "No investments this month",
                     "body": "Consider allocating even a small amount to savings or investments.",
                     "severity": "info"})

    # 6. Largest category
    if breakdown:
        top = breakdown[0]
        if income > 0 and top["total"] / income > 0.30:
            tips.append({"icon": "bar-chart", "title": f"{top['category']} is your biggest spend",
                         "body": f"${top['total']:,.2f} ({top['total']/income*100:.0f}% of income).",
                         "severity": "info"})

    # 7. Budget status
    statuses = db.get_budget_status(ym)
    over = [s for s in statuses if s["spent"] > s["budget"]]
    on_track = [s for s in statuses if s["spent"] <= s["budget"]]
    if statuses and not over:
        tips.append({"icon": "shield-check", "title": "All budgets on track",
                     "body": f"You're within budget on all {len(on_track)} categories.",
                     "severity": "good"})
    elif over:
        names = ", ".join(s["category"] for s in over[:3])
        tips.append({"icon": "shield-alert", "title": f"{len(over)} budget(s) exceeded",
                     "body": f"Over budget in: {names}.",
                     "severity": "warn"})

    if not tips:
        tips.append({"icon": "lightbulb", "title": "Add more transactions",
                     "body": "Once you have income and expense data, personalized tips will appear.",
                     "severity": "info"})

    return tips
