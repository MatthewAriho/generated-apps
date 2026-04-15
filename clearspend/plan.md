# ClearSpend — Implementation Plan & Handoff

## Overview
KivyMD Android budget app (renamed from BudgetApp → **ClearSpend**) built in 4 version milestones. Each milestone ends with a compiled APK and git commit.

**Current Status:** V1/V1.5/V2 source written, bug fixed — ready to build V0.4 APK

---

## Version Status

| Version | Features | Status | APK |
|---------|----------|--------|-----|
| V0.1 | Core app, manual entry, bank connect UI, monthly tracking, local+cloud storage | DONE | `bin/clearspend-0.1-arm64-v8a-debug.apk` |
| V1 | Recurring detection, category trend tracking | SOURCE DONE — needs APK | - |
| V1.5 | Monthly budget, over/under calc, forecasting, saving tips | SOURCE DONE — needs APK | - |
| V2 | Push notifications, PIN/fingerprint auth | TODO | - |

---

## Architecture

### File Structure
```
main.py                     # MDApp entry point, root ScreenManager, KV root string
buildozer.spec              # Build config (api=34, minapi=26, ndk=25b, arm64)
plan.md                     # This file

models/
  __init__.py
  database.py               # SQLite singleton, all CRUD operations

screens/
  __init__.py
  dashboard.py              # DashboardTab(MDBoxLayout) - monthly summary + FAB
  add_transaction.py        # AddTransactionScreen(Screen) - full-screen form
  transaction_list.py       # TransactionListTab(MDBoxLayout) - history + filters
  bank_connect.py           # BankConnectTab(MDBoxLayout) - OAuth mock + account list
  settings.py               # SettingsTab(MDBoxLayout) - cloud sync, mode toggle
  trends.py                 # TrendsTab (V1) - category breakdown + recurring
  budget.py                 # BudgetTab (V1.5) - per-category budget + forecast

utils/
  __init__.py
  connectivity.py           # is_online() via socket ping to 8.8.8.8:53
  bank_api.py               # BankAPI(ABC), ScotiabankAPI (mock), GenericBankAPI
  cloud_sync.py             # CloudSync — JSONBin.io backup/restore
```

### Navigation
```
Root: MDScreenManager
  Screen 'home'
    MDBottomNavigation
      Tab 'dashboard' → DashboardTab
      Tab 'history'   → TransactionListTab
      Tab 'bank'      → BankConnectTab
      Tab 'settings'  → SettingsTab
  AddTransactionScreen  (full-screen push from FAB)
  TrendsScreen          (V1, accessible from Settings)
  BudgetScreen          (V1.5, accessible from Settings)
```

### Database Schema (SQLite, stdlib)
```sql
transactions(id, amount REAL, type TEXT, category TEXT, description TEXT, date TEXT, source TEXT, bank_account_id INT)
bank_accounts(id, bank_name TEXT, account_name TEXT, account_number_masked TEXT, access_token TEXT, last_sync TEXT)
categories(id, name TEXT UNIQUE, icon TEXT)      -- seeded with 14 defaults
budgets(id, month TEXT, category TEXT, amount REAL)      -- V1.5
notifications_log(id, message TEXT, created_at TEXT, read INT)  -- V2
```

### Key App Properties (Kivy Observable)
```python
app.is_online: BooleanProperty   -- drives UI connectivity chip
app.sync_status: StringProperty  -- 'idle'|'syncing'|'done'|'error'
```

---

## V0.1 — Feature Details

### Screens
1. **DashboardTab** — Month nav (prev/next), balance card (income/expenses/net), recent 10 transactions list, FAB → AddTransactionScreen
2. **AddTransactionScreen** — Amount, type toggle (Expense/Income), category dropdown, description, date (defaults today), Save/Cancel
3. **TransactionListTab** — Full history, filter chips (All/Expense/Income), month dropdown
4. **BankConnectTab** — Scotiabank tile + "Add Other Bank" button, mock OAuth dialog, connected accounts list, "Sync Now" button
5. **SettingsTab** — Online/offline chip, cloud backup (JSONBin API key + Bin ID fields), About section

### Bank API
- `ScotiabankAPI` is **mocked** — real Scotiabank Open Banking requires business OAuth2 registration at developer.scotiabank.com
- Mock returns 20 realistic CAD transactions + payroll deposit
- `GenericBankAPI` is a stub for Plaid-like integration

### Cloud Sync
- JSONBin.io free tier (https://jsonbin.io)
- User enters API key in Settings → stored in KV Store (kivy.storage.jsonstore)
- Data is base64-encoded before upload (basic obfuscation)
- Backup: POST to create bin, subsequent runs PUT to same bin ID

---

## V1 — Trend Tracking (next milestone)

After V0.1 APK is committed:
1. Add `screens/trends.py` with `TrendsTab(MDBoxLayout)`
2. Add 4th item in Settings linking to Trends
3. Use `db.get_recurring_transactions()` — finds same description in 2+ months
4. Use `db.get_category_breakdown()` — bar-style progress per category
5. Auto-tag: ATM Withdrawal → ATM, Uber/Lyft → Rides, Netflix/Spotify → Subscriptions

---

## V1.5 — Budgeting & Forecast

After V1 APK committed:
1. Add `screens/budget.py`
2. Per-category monthly spend limits (MDSlider or text input)
3. Dashboard card: "Spent X of Y (Z%)" per budget category
4. Forecast: `projected = (spent / days_elapsed) * total_days_in_month`
5. Saving tips: rule-based strings based on top-3 categories vs budget

---

## V2 — Notifications & Auth

After V1.5 APK committed:
1. PIN screen — 4-digit, hash stored in JsonStore; shown on every app launch
2. Biometric hook via Pyjnius (BiometricPrompt) — graceful fallback to PIN
3. Spend alerts: background check via `kivy.clock.Clock.schedule_interval`
   - Alert if >$50 or >$100 spent since last check-in
   - Notification via Android toast / plyer library

---

## Build Commands

```bash
# First time setup
pip install buildozer
buildozer android debug

# APK output
ls bin/*.apk

# Commit after each version
git add -A
git commit -m "V0.1: core app, manual entry, bank mock, cloud sync"
```

---

## Where To Continue (handoff)

**Last completed:** V0.1 APK built. V1/V1.5/V2 source all written. Bug fixed (see Gotchas).

**Next action:** Run `echo "y" | buildozer android debug` to produce V0.4 APK, then commit it.

Before building, bump `version = 0.2` in `buildozer.spec` for V1, `version = 0.3` for V1.5.

**Key files already implemented for V1:**
- `screens/trends.py` — category breakdown bars + recurring transactions detection
- `models/database.py` — `get_recurring_transactions()` and `get_category_breakdown()` implemented
- `screens/settings.py` — "View Trends" and "Set Budget" navigation (verify these buttons exist)

**Key files already implemented for V1.5:**
- `screens/budget.py` — per-category budgets, forecast engine, saving tips

**Bugs fixed (2026-04-13/14):**
- All screen KV strings used `app.theme_cls.primary_dark_color` which does not exist in KivyMD 1.x — the correct property is `app.theme_cls.primary_dark`. Fixed in all 5 screen files + `.buildozer/android/app` cached copies.
- `screens/pin_auth.py` KV used semicolons to put multiple properties on one line (e.g. `text: "1"; size_hint_x: 1; height: dp(56); size_hint_y: None`). Kivy KV does NOT support semicolons as property separators — each property must be on its own line. This caused a KV parse/eval crash when the PIN screen rendered. Fixed by expanding all button properties to individual lines.

**Gotchas:**
- KivyMD `MDBottomNavigation` tab content must be a single direct child widget
- Android storage path: use `app.user_data_dir` not hardcoded paths
- **Cython must be 0.29.37** — Cython 3.x breaks kivy/pyjnius compilation (`pip3 install "Cython==0.29.37"`)
- **buildozer pip patch** — `/usr/local/lib/python3.11/dist-packages/buildozer/targets/android.py` line ~717: add `"--break-system-packages"` to `options` list
- Android SDK API 34 and build-tools 34.0.0 must be installed via sdkmanager
- JSONBin free tier: 10,000 requests/month, 100KB per bin
