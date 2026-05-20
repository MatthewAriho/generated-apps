# ClearSpend – Pending Updates

Last updated: 2026-05-20

---

## 1. Smart Transaction Classification

**Problem:** Transactions imported from Plaid are often misclassified or uncategorized. Common cases:
- Transfers between personal bank accounts (e.g. chequing → TFSA, chequing → brokerage) tagged as expenses
- Recurring rent/mortgage payments lumped into generic "Other" or wrong categories
- Investment contributions not distinguished from regular spending

**Proposed approach:**

### A – Rule-based auto-classification (immediate, no user action)
- Maintain a keyword/pattern table (`classification_rules` in DB or a config file)
- On sync, match description against rules and assign category + type override
- Seed rules for common patterns: "e-transfer", "interac", "transfer to", "rent", "lease", "tfsa", "rrsp", "wealthsimple", "questrade", "payroll", "direct deposit"
- Add a "Transfer" type (separate from income/expense) so transfers don't inflate spending totals

### B – User prompt for ambiguous transactions (on first encounter)
- After sync, detect uncategorized or low-confidence transactions
- Show a bottom sheet / dialog: "What is this? [Rent] [Investment] [Transfer] [Other]"
- Remember the choice: if description matches again, auto-apply silently
- Store learned rules in a `user_rules` DB table keyed on description prefix/exact match

### C – Bulk re-classification UI
- In the Transactions tab, long-press a transaction to open a "Reclassify" menu
- Option to apply the new category to "all transactions with this description"

**Files to change:**
- `models/database.py` – add `user_rules` table, `classification_rules` seeding, `apply_rules()` helper
- `screens/bank_connect.py` – call `apply_rules()` after sync, collect ambiguous list, show prompt
- `screens/transaction_list.py` – add long-press reclassify action

---

## 2. Sort Filter Arrow Encoding Fix

**Problem:** The sort button labels use Unicode arrows (↓ ↑) which cause encode/decode errors on some Android builds/locales (likely a UTF-8/Latin-1 mismatch in the KV string or font rendering path).

**Fix:** Replace Unicode arrows with ASCII equivalents:
- `↓` → `v` or `(desc)`
- `↑` → `^` or `(asc)`

Affected file: `screens/transaction_list.py`, `_SORT_OPTIONS` list.

---

## 3. Transaction Tab Lag (still present in v4.2)

**Problem:** Despite moving DB queries to background threads, the Transactions tab is still the slowest to navigate to/from. Likely causes:

1. **Widget construction cost** – even chunked, building MDCard trees (6 widgets per row × hundreds of rows) is expensive on the main thread. Each MDCard triggers layout passes.
2. **ScrollView height recalculation** – `height: self.minimum_height` on the inner MDBoxLayout forces a full layout recalculation every time a widget is added.
3. **`clear_widgets()` cost** – tearing down hundreds of widgets synchronously before the new batch arrives still blocks the frame.

**Proposed fix – switch to RecycleView:**
- Replace the `ScrollView + MDBoxLayout` pattern with a `RecycleView` (Kivy's virtualized list)
- RecycleView only creates widgets for visible rows (~10–15 at a time), recycling them as the user scrolls
- This reduces widget count from O(N) to O(visible rows), making both load and scroll instant
- Requires defining a `TransactionRowView` recycleview item class

**Files to change:**
- `screens/transaction_list.py` – replace ScrollView/MDBoxLayout with RecycleView, add row viewclass

---

## 4. Event Expense Tracking ✅ (complete – v4.6)

**Feature:** Group transactions under a named event (trip, wedding, etc.)

- New `events` table: name, description, start/end date, location keyword, color
- New `event_transactions` junction table
- Events tab in bottom nav (map-marker icon)
- Create event → set name, dates, optional location keyword for auto-matching
- Auto-match: Plaid transactions whose date falls in event range AND description contains location keyword are auto-assigned
- Manual assign: from transaction detail (edit screen) → "Add to event" picker
- Event detail view: total spend, transaction list, breakdown by category

**Files:** `models/database.py`, `screens/events.py`, `screens/edit_transaction.py`, `main.py`

## 5. Financial Tips Engine ✅ (complete – v4.6)

**Feature:** Rule-based tips shown on Dashboard based on spending patterns

Rules:
- Dining > 15% of income → suggest reducing
- Subscriptions > $100/mo → list them
- No investment/transfer transactions → suggest saving
- Spending up >20% vs last month → flag
- 50/30/20 rule check (needs/wants/savings ratio)
- Largest single category → highlight

Displayed as a scrollable chip/card section at bottom of Dashboard.

**Files:** `utils/tips.py` (new), `screens/dashboard.py`

## 6. Future / Backlog

- Push notifications for budget overage alerts (requires foreground service on Android)
- CSV export of transaction history
- Multi-currency support
- Widget (home screen glanceable summary)
