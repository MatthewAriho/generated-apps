# ClearSpend Roadmap & App Analysis

## Current State (V3 / v0.6)

The app is functionally complete across V0.1-V3 milestones. Core tracking, bank sync (Plaid + Scotiabank mock), budgeting, trends, PIN auth, cloud backup, and charts all work. The app needs polish, UX restructuring, and a few high-impact features to go from "functional prototype" to "daily driver."

---

## Logo & Branding

**Logo concept:** Teal circle with white dollar sign + mini bar chart. Conveys finance + tracking at a glance. Works at all icon sizes (512px down to 48px notification icon).

Files:
- `assets/icon.png` - 512x512 app icon
- `assets/icon_192.png` - 192x192 notification icon
- `assets/presplash.png` - 720x1280 splash screen (dark navy + centered logo)
- `assets/generate_icon.py` - regenerate with `python assets/generate_icon.py`

---

## Priority 1: UX Restructuring

### 1.1 Reorganize Settings

Settings is currently overloaded with 8 sections. Restructure:

**Keep in Settings:**
- Security (PIN change)
- About

**Move to a "Data & Sync" sub-screen (push from Settings):**
- Cloud Backup (JSONBin)
- Data Export (CSV)
- Demo Mode / Clear Data

**Move to hidden Developer section (5-tap on version number to reveal):**
- Plaid credentials (client_id, secret, environment)
- Connectivity status

**Rationale:** Regular users should never see API keys or environment toggles. Power users can find them via the version-tap easter egg.

### 1.2 Rethink Bottom Navigation

Current tabs: Home | History | Bank | Settings

Consider: Home | History | Insights | Settings

Where "Insights" combines:
- Trends (category breakdown, donut chart, recurring detection)
- Budget (limits, forecast, pace)
- Monthly comparison

This eliminates the need for "quick action buttons" on the dashboard and gives analytics first-class navigation status. The Bank tab content moves into Settings > Accounts or becomes a section within the Home tab.

### 1.3 Improve Transaction Entry

- **Smart categorization**: If description contains "uber" -> auto-select "Rides". Build a simple keyword-to-category map.
- **Recent categories shortcut**: Show the 4 most-used categories as chips above the dropdown.
- **Quick-add mode**: Long-press the FAB for a minimal amount-only entry (category defaults to last used).

---

## Priority 2: Data Integrity & Safety

### 2.1 Protect Destructive Actions

- "Clear All Data" should require PIN entry before executing.
- Transaction delete should offer a 5-second undo Snackbar (soft delete, then hard delete after timeout).
- Budget delete should also confirm.

### 2.2 Fix Transaction Edit

Currently edit does delete + re-insert. This loses:
- `plaid_transaction_id` (breaks Plaid sync dedup)
- `bank_account_id` linkage
- `source` field

Fix: Use SQL UPDATE instead of delete/insert.

### 2.3 PIN Hardening

- Rate limit: 3 wrong attempts -> 30s lockout, 6 -> 5min, 9 -> 30min.
- Auto-lock after 5 minutes of inactivity (configurable).
- Require current PIN before allowing PIN change.

---

## Priority 3: Feature Ideas

### 3.1 Transaction Search

Add a search bar to the History tab. Search by:
- Description (fuzzy match)
- Category
- Amount range
- Date range
- Source (manual, plaid, scotiabank)

Implementation: SQLite LIKE queries with debounced input.

### 3.2 Custom Categories

Let users add, rename, hide, or reorder categories. Store custom flag in categories table. Show a "Manage Categories" button in Settings.

### 3.3 Monthly Comparison Card

On the dashboard, show: "You spent $X more/less than last month" with a color-coded arrow. Simple but high-impact for awareness.

### 3.4 Recurring Transaction Management

Currently the app detects recurring transactions but does nothing with them. Add:
- Mark a transaction as recurring (set frequency: weekly/biweekly/monthly)
- Auto-create upcoming transactions as "pending" on expected dates
- Show upcoming recurring charges on the dashboard

### 3.5 Transaction Tags

Add a tags system (multi-select per transaction):
- "Business" / "Personal" / "Reimbursable" / "Shared" / "Tax Deductible"
- Filter by tag in History
- Export only tagged transactions

### 3.6 Multi-Currency

For travelers:
- Currency selector on transaction entry (CAD, USD, EUR, GBP, etc.)
- Auto-convert to home currency for budget tracking
- Show original + converted amounts

### 3.7 Widgets

Android home screen widget showing:
- Monthly balance summary
- Quick-add transaction button
- Budget status indicator

### 3.8 Notifications & Alerts

- Budget approaching limit (80% threshold)
- Weekly spending summary (Sunday evening)
- Large transaction alert (configurable threshold)
- Recurring charge reminder (1 day before expected)

### 3.9 Receipt Scanner

Use device camera to capture receipt photos. Store as attachment linked to transaction. OCR (future) could auto-fill amount and merchant.

### 3.10 Shared Expenses

For couples or roommates:
- Mark transactions as "split"
- Track who owes whom
- Settlement summary

---

## Priority 4: Technical Improvements

### 4.1 Proper Threading

Replace `Clock.schedule_once` pattern for HTTP calls with actual background threads. The current approach blocks the UI thread during Plaid API calls and cloud sync. Use `kivy.network.urlrequest.UrlRequest` or `threading.Thread` with Clock callbacks.

### 4.2 Improve Export

- Export budgets + categories (not just transactions)
- PDF monthly report generation
- Email export option

### 4.3 Sync Improvements

- Auto-sync Plaid accounts on app open (if online, last sync > 6hrs ago)
- Background sync via Android service
- Conflict resolution for cloud restore (merge vs overwrite)

### 4.4 Testing

- Add unit tests for database queries
- Add integration tests for Plaid API flow (sandbox)
- Screenshot tests for charts

### 4.5 Performance

- Lazy-load transaction list (pagination with scroll-triggered loading)
- Cache monthly summaries (invalidate on transaction change)
- Reduce chart redraw frequency (only on data change, not every resize)

---

## Suggested Version Milestones

### V4 (Next Release)
- [ ] Reorganize settings (move dev config behind 5-tap)
- [ ] Fix transaction edit (UPDATE instead of delete/insert)
- [ ] PIN rate limiting + auto-lock timeout
- [ ] Transaction search in History tab
- [ ] Monthly comparison card on dashboard
- [ ] Protect "Clear All Data" with PIN

### V5
- [ ] Custom categories (add/rename/hide)
- [ ] Recurring transaction management
- [ ] Transaction tags
- [ ] Budget approaching alerts
- [ ] Weekly spending summary notification

### V6
- [ ] Multi-currency support
- [ ] Receipt photo attachment
- [ ] PDF monthly report
- [ ] Android home screen widget
- [ ] Auto-sync Plaid on app open

### V7
- [ ] Shared expenses / split tracking
- [ ] Smart categorization (keyword matching)
- [ ] Onboarding flow for new users
- [ ] Play Store submission prep

---

## Architecture Notes

### What's Working Well
- Single-file KV strings per screen (easy to find, easy to modify)
- Database singleton pattern (thread-safe via `check_same_thread=False`)
- Plaid cursor-based sync (incremental, efficient)
- Canvas-based charts (lightweight, no dependencies)
- JsonStore for credentials (sandboxed on Android)

### What Needs Refactoring
- Duplicated `_get_store()` / `_get_app()` helpers across screens (extract to shared util)
- Transaction edit uses delete+insert (should be UPDATE)
- Category list is hardcoded in `_seed_categories` (should support custom categories)
- Spend alert thresholds are hardcoded (should be configurable)
- `notifications_log` table exists but is never used
