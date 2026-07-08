const BASE = "/clearspend/api";
let currentMonth = new Date().toISOString().slice(0, 7);
let budgetMonth = currentMonth;
let trendsMonth = currentMonth;
let _searchTimer = null;

// ── Init ──
document.addEventListener("DOMContentLoaded", () => {
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("/clearspend/sw.js", { scope: "/clearspend/" });
  }
  // Restore dark mode from localStorage
  if (localStorage.getItem("cs_dark") === "1") {
    document.body.classList.add("dark");
  }
  loadDashboard();
  loadMonthOptions();
});

// ── XSS ──
function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

// ── API helper ──
async function api(path, opts = {}) {
  const r = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const d = await r.json();
  if (!r.ok) throw new Error(d.detail || "Request failed");
  return d;
}

// ── Tab switching ──
function switchTab(name) {
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  document.querySelectorAll(".bottom-nav button").forEach(b => b.classList.remove("active"));
  const tab = document.getElementById("tab-" + name);
  const nav = document.getElementById("nav-" + name);
  if (tab) tab.classList.add("active");
  if (nav) {
    nav.classList.add("active");
    nav.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
  }

  // FAB only on dash/txns
  const fab = document.getElementById("fab-add");
  fab.style.display = (name === "dash" || name === "txns") ? "flex" : "none";

  if (name === "dash") loadDashboard();
  else if (name === "txns") loadTransactions();
  else if (name === "budget") loadBudgets();
  else if (name === "goals") loadGoals();
  else if (name === "trends") loadTrends();
  else if (name === "events") loadEvents();
  else if (name === "bank") loadBankAccounts();
  else if (name === "settings") loadSettings();
}

// ── Category icons ──
const CAT_ICONS = {
  "Food & Dining": "&#127829;", "Restaurants": "&#127869;", "Transportation": "&#128663;",
  "Rides (Uber/Lyft)": "&#128661;", "Shopping": "&#128722;", "Entertainment": "&#127916;",
  "Subscriptions": "&#128260;", "Utilities": "&#9889;", "Healthcare": "&#128138;",
  "ATM / Cash": "&#128181;", "Nightlife / Bars": "&#127863;", "Salary / Income": "&#128188;",
  "Freelance": "&#128187;", "Rent / Housing": "&#127968;", "Investment": "&#128200;",
  "Transfer": "&#8644;", "Travel": "&#9992;", "Other": "&#128900;",
};
function catIcon(cat) { return CAT_ICONS[cat] || "&#128900;"; }

const DONUT_COLORS = ["#1a6b3c","#2563eb","#dc2626","#f59e0b","#7c3aed","#ec4899","#14b8a6","#f97316","#6366f1","#10b981"];

// ══════════════════════════════════════════════════════════════════
// DASHBOARD
// ══════════════════════════════════════════════════════════════════
async function loadDashboard() {
  try {
    const d = await api("/dashboard");
    const s = d.summary;
    const balClass = s.balance >= 0 ? "positive" : "negative";
    let html = `
      <div class="card summary-card">
        <div class="summary-balance ${balClass}">$${Math.abs(s.balance).toLocaleString("en",{minimumFractionDigits:2})}</div>
        <div class="summary-row">
          <div class="summary-item"><div class="label">Income</div><div class="value income">$${s.income.toLocaleString("en",{minimumFractionDigits:2})}</div></div>
          <div class="summary-item"><div class="label">Expenses</div><div class="value expense">$${s.expense.toLocaleString("en",{minimumFractionDigits:2})}</div></div>
        </div>
        ${d.delta_pct !== 0 ? `<div class="summary-delta ${d.delta_pct > 0 ? 'up' : 'down'}">${d.delta_pct > 0 ? '&#9650;' : '&#9660;'} ${Math.abs(d.delta_pct)}% vs last month</div>` : ''}
      </div>`;

    if (d.trend.length > 0) {
      const maxVal = Math.max(...d.trend.map(t => Math.max(t.income, t.expense)), 1);
      html += `<div class="card"><div class="card-title">6-Month Trend</div><div class="bar-chart">`;
      for (const t of d.trend) {
        const ih = Math.max(2, t.income / maxVal * 110);
        const eh = Math.max(2, t.expense / maxVal * 110);
        html += `<div class="bar-group"><div class="bar-pair"><div class="bar income" style="height:${ih}px" title="$${t.income}"></div><div class="bar expense" style="height:${eh}px" title="$${t.expense}"></div></div><div class="bar-label">${esc(t.label)}</div></div>`;
      }
      html += `</div></div>`;
    }

    if (d.breakdown.length > 0) {
      const total = d.breakdown.reduce((a, b) => a + b.total, 0);
      html += `<div class="card"><div class="card-title">This Month by Category</div>`;
      for (const c of d.breakdown.slice(0, 6)) {
        const pct = total > 0 ? (c.total / total * 100) : 0;
        html += `<div class="cat-row"><div class="cat-icon">${catIcon(c.category)}</div><div class="cat-info"><div class="cat-name">${esc(c.category)}</div><div class="cat-bar-bg"><div class="cat-bar-fill" style="width:${pct}%"></div></div></div><div><div class="cat-amount">$${c.total.toFixed(2)}</div><div class="cat-pct">${pct.toFixed(0)}%</div></div></div>`;
      }
      html += `</div>`;
    }

    if (d.tips.length > 0) {
      html += `<div class="section-title">Insights</div>`;
      for (const tip of d.tips) {
        html += `<div class="card tip-card ${tip.severity}"><div class="tip-body"><div class="tip-title">${esc(tip.title)}</div><div class="tip-text">${esc(tip.body)}</div></div></div>`;
      }
    }

    if (d.recent.length > 0) {
      html += `<div class="section-title">Recent</div><div class="card">`;
      for (const t of d.recent) html += txnRowHtml(t);
      html += `</div>`;
    }

    document.getElementById("dash-content").innerHTML = html;
  } catch (e) {
    document.getElementById("dash-content").innerHTML = `<div class="empty-state"><div class="icon">&#128176;</div><div class="msg">${esc(e.message)}</div></div>`;
  }
}

// ══════════════════════════════════════════════════════════════════
// TRANSACTIONS
// ══════════════════════════════════════════════════════════════════
function txnRowHtml(t) {
  const sign = t.type === "income" ? "+" : "-";
  const cls = t.type === "income" ? "income" : "expense";
  return `<div class="txn-row" onclick="showEditTransaction(${t.id})"><div class="txn-cat-icon">${catIcon(t.category)}</div><div class="txn-info"><div class="txn-desc">${esc(t.description || t.category)}</div><div class="txn-meta">${esc(t.category)} &middot; ${esc(t.date)}</div></div><div class="txn-amount ${cls}">${sign}$${t.amount.toFixed(2)}</div></div>`;
}

async function loadMonthOptions() {
  try {
    const d = await api("/months");
    const sel = document.getElementById("txn-month");
    sel.innerHTML = '<option value="">All Months</option>';
    for (const m of d.months) {
      const label = new Date(m + "-01").toLocaleDateString("en", { year: "numeric", month: "short" });
      sel.innerHTML += `<option value="${m}" ${m === currentMonth ? 'selected' : ''}>${label}</option>`;
    }
  } catch (e) {}
}

function debounceSearch() {
  clearTimeout(_searchTimer);
  _searchTimer = setTimeout(loadTransactions, 300);
}

async function loadTransactions() {
  const month = document.getElementById("txn-month").value;
  const type = document.getElementById("txn-type").value;
  const search = document.getElementById("txn-search").value;
  const params = new URLSearchParams();
  if (month) params.set("month", month);
  if (type) params.set("type", type);
  if (search) params.set("search", search);
  params.set("limit", "100");
  try {
    const d = await api("/transactions?" + params);
    if (d.transactions.length === 0) {
      document.getElementById("txn-list").innerHTML = `<div class="empty-state"><div class="icon">&#128179;</div><div class="msg">No transactions found</div></div>`;
      return;
    }
    let html = '<div class="card">';
    for (const t of d.transactions) html += txnRowHtml(t);
    html += '</div>';
    document.getElementById("txn-list").innerHTML = html;
  } catch (e) {
    document.getElementById("txn-list").innerHTML = `<div class="empty-state"><div class="msg">${esc(e.message)}</div></div>`;
  }
}

async function showAddTransaction() {
  const cats = await api("/categories");
  const modal = document.getElementById("modal-root");
  let catOpts = cats.categories.map(c => `<option value="${esc(c.name)}">${esc(c.name)}</option>`).join("");
  modal.innerHTML = `<div class="modal-overlay" onclick="closeModal()"><div class="modal" onclick="event.stopPropagation()">
    <h3>Add Transaction</h3>
    <div class="type-toggle"><button class="active" onclick="setAddType('expense',this)">Expense</button><button onclick="setAddType('income',this)">Income</button></div>
    <div class="form-group" style="margin-top:12px"><input type="number" id="add-amount" placeholder="Amount" step="0.01" min="0.01"></div>
    <div class="form-group"><input type="text" id="add-desc" placeholder="Description" oninput="autoClassifyAdd()"></div>
    <div class="form-group"><select id="add-cat">${catOpts}</select></div>
    <div class="form-group"><input type="date" id="add-date" value="${new Date().toISOString().slice(0,10)}"></div>
    <input type="hidden" id="add-type" value="expense">
    <div class="modal-btns"><button class="cancel" onclick="closeModal()">Cancel</button><button class="confirm" onclick="doAddTransaction()">Add</button></div>
  </div></div>`;
}

function setAddType(type, btn) {
  document.getElementById("add-type").value = type;
  document.querySelectorAll(".type-toggle button").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
}

let _classifyTimer = null;
function autoClassifyAdd() {
  clearTimeout(_classifyTimer);
  _classifyTimer = setTimeout(async () => {
    const desc = document.getElementById("add-desc").value;
    if (desc.length < 3) return;
    try {
      const d = await api("/transactions/classify", { method: "POST", body: { description: desc } });
      if (d.category && d.category !== "Other") document.getElementById("add-cat").value = d.category;
    } catch (e) {}
  }, 500);
}

async function doAddTransaction() {
  const amount = parseFloat(document.getElementById("add-amount").value);
  const desc = document.getElementById("add-desc").value;
  const cat = document.getElementById("add-cat").value;
  const date = document.getElementById("add-date").value;
  const type = document.getElementById("add-type").value;
  if (!amount || amount <= 0) return alert("Enter a valid amount");
  try {
    await api("/transactions", { method: "POST", body: { amount, type, category: cat, description: desc, date } });
    closeModal();
    loadDashboard();
    loadMonthOptions();
    if (document.getElementById("tab-txns").classList.contains("active")) loadTransactions();
  } catch (e) { alert(e.message); }
}

async function showEditTransaction(id) {
  try {
    const t = await api(`/transactions/${id}`);
    const cats = await api("/categories");
    let catOpts = cats.categories.map(c => `<option value="${esc(c.name)}" ${c.name === t.category ? 'selected' : ''}>${esc(c.name)}</option>`).join("");
    const modal = document.getElementById("modal-root");
    modal.innerHTML = `<div class="modal-overlay" onclick="closeModal()"><div class="modal" onclick="event.stopPropagation()">
      <h3>Edit Transaction</h3>
      <div class="type-toggle"><button class="${t.type==='expense'?'active':''}" onclick="setEditType('expense',this)">Expense</button><button class="${t.type==='income'?'active':''}" onclick="setEditType('income',this)">Income</button></div>
      <div class="form-group" style="margin-top:12px"><input type="number" id="edit-amount" value="${t.amount}" step="0.01"></div>
      <div class="form-group"><input type="text" id="edit-desc" value="${esc(t.description || '')}"></div>
      <div class="form-group"><select id="edit-cat">${catOpts}</select></div>
      <div class="form-group"><input type="date" id="edit-date" value="${t.date}"></div>
      <input type="hidden" id="edit-type" value="${t.type}">
      <input type="hidden" id="edit-id" value="${t.id}">
      <div class="modal-btns"><button class="cancel" onclick="doDeleteTransaction(${t.id})">&#128465; Delete</button><button class="confirm" onclick="doUpdateTransaction()">Save</button></div>
    </div></div>`;
  } catch (e) { alert(e.message); }
}

function setEditType(type, btn) {
  document.getElementById("edit-type").value = type;
  btn.parentElement.querySelectorAll("button").forEach(b => b.classList.remove("active"));
  btn.classList.add("active");
}

async function doUpdateTransaction() {
  const id = document.getElementById("edit-id").value;
  try {
    await api(`/transactions/${id}`, { method: "PUT", body: {
      amount: parseFloat(document.getElementById("edit-amount").value),
      type: document.getElementById("edit-type").value,
      category: document.getElementById("edit-cat").value,
      description: document.getElementById("edit-desc").value,
      date: document.getElementById("edit-date").value,
    }});
    closeModal();
    loadTransactions();
    loadDashboard();
  } catch (e) { alert(e.message); }
}

async function doDeleteTransaction(id) {
  if (!confirm("Delete this transaction?")) return;
  try {
    await api(`/transactions/${id}`, { method: "DELETE" });
    closeModal();
    loadTransactions();
    loadDashboard();
  } catch (e) { alert(e.message); }
}

// ══════════════════════════════════════════════════════════════════
// BUDGETS
// ══════════════════════════════════════════════════════════════════
async function loadBudgets() {
  renderMonthNav("budget-month-nav", budgetMonth, (m) => { budgetMonth = m; loadBudgets(); });
  try {
    const d = await api(`/budgets?month=${budgetMonth}`);
    if (d.status.length === 0) {
      document.getElementById("budget-content").innerHTML = `<div class="empty-state"><div class="icon">&#127919;</div><div class="msg">No budgets set for this month</div><button class="btn-primary" style="margin-top:12px;width:auto;padding:10px 20px" onclick="copyPrevBudgets()">Copy from last month</button></div>`;
      return;
    }
    let html = '<div class="card">';
    for (const b of d.status) {
      const pctW = Math.min(b.pct * 100, 100);
      const cls = b.pct > 1 ? "over" : b.pct > 0.8 ? "warn" : "ok";
      html += `<div class="budget-row"><div class="budget-info"><div class="budget-cat">${catIcon(b.category)} ${esc(b.category)}</div><div class="budget-bar-bg"><div class="budget-bar-fill ${cls}" style="width:${pctW}%"></div></div>${b.forecast > 0 ? `<div class="budget-forecast">Forecast: $${b.forecast.toFixed(0)}</div>` : ''}</div><div class="budget-amounts"><div class="budget-spent">$${b.spent.toFixed(2)}</div><div class="budget-limit">of $${b.budget.toFixed(0)}</div></div></div>`;
    }
    html += '</div>';
    document.getElementById("budget-content").innerHTML = html;
  } catch (e) {
    document.getElementById("budget-content").innerHTML = `<div class="empty-state"><div class="msg">${esc(e.message)}</div></div>`;
  }
}

async function showAddBudget() {
  const cats = await api("/categories");
  const modal = document.getElementById("modal-root");
  let catOpts = cats.categories.map(c => `<option value="${esc(c.name)}">${esc(c.name)}</option>`).join("");
  modal.innerHTML = `<div class="modal-overlay" onclick="closeModal()"><div class="modal" onclick="event.stopPropagation()"><h3>Set Budget</h3><div class="form-group"><select id="budget-cat">${catOpts}</select></div><div class="form-group"><input type="number" id="budget-amount" placeholder="Monthly limit" step="1" min="1"></div><div class="modal-btns"><button class="cancel" onclick="closeModal()">Cancel</button><button class="confirm" onclick="doAddBudget()">Save</button></div></div></div>`;
}

async function doAddBudget() {
  const cat = document.getElementById("budget-cat").value;
  const amount = parseFloat(document.getElementById("budget-amount").value);
  if (!amount || amount <= 0) return alert("Enter a valid amount");
  try {
    await api("/budgets", { method: "POST", body: { month: budgetMonth, category: cat, amount } });
    closeModal(); loadBudgets();
  } catch (e) { alert(e.message); }
}

async function copyPrevBudgets() {
  const [y, m] = budgetMonth.split("-").map(Number);
  let pm = m - 1, py = y;
  if (pm <= 0) { pm = 12; py--; }
  const from = `${py}-${String(pm).padStart(2,"0")}`;
  try {
    const d = await api("/budgets/copy", { method: "POST", body: { from_month: from, to_month: budgetMonth } });
    if (d.copied > 0) loadBudgets(); else alert("No budgets found in previous month");
  } catch (e) { alert(e.message); }
}

// ══════════════════════════════════════════════════════════════════
// GOALS
// ══════════════════════════════════════════════════════════════════
async function loadGoals() {
  try {
    const d = await api("/goals");
    if (d.goals.length === 0) {
      document.getElementById("goals-content").innerHTML = `<div class="empty-state"><div class="icon">&#127942;</div><div class="msg">No savings goals yet</div></div>`;
      return;
    }
    let html = '';
    const active = d.goals.filter(g => !g.completed);
    const completed = d.goals.filter(g => g.completed);
    for (const g of active) {
      const pct = g.target > 0 ? Math.min(g.saved / g.target * 100, 100) : 0;
      html += `<div class="card goal-card"><div class="goal-name">${esc(g.name)}</div><div class="goal-progress-bg"><div class="goal-progress-fill" style="width:${pct}%"></div></div><div class="goal-amounts"><span>$${g.saved.toFixed(2)} saved</span><span>$${g.target.toFixed(2)} target</span></div>${g.deadline ? `<div class="goal-deadline">Due: ${esc(g.deadline)}</div>` : ''}<div class="goal-actions"><button class="btn-sm btn-success" onclick="showDeposit(${g.id})">+ Deposit</button><button class="btn-sm btn-outline" onclick="deleteGoal(${g.id})">Delete</button></div></div>`;
    }
    if (completed.length > 0) {
      html += `<div class="section-title">Completed</div>`;
      for (const g of completed) {
        html += `<div class="card goal-card"><div class="goal-badge">&#127881;</div><div class="goal-name">${esc(g.name)}</div><div class="goal-progress-bg"><div class="goal-progress-fill done" style="width:100%"></div></div><div class="goal-amounts"><span>$${g.saved.toFixed(2)}</span><span>$${g.target.toFixed(2)}</span></div></div>`;
      }
    }
    document.getElementById("goals-content").innerHTML = html;
  } catch (e) {
    document.getElementById("goals-content").innerHTML = `<div class="empty-state"><div class="msg">${esc(e.message)}</div></div>`;
  }
}

async function showAddGoal() {
  const modal = document.getElementById("modal-root");
  modal.innerHTML = `<div class="modal-overlay" onclick="closeModal()"><div class="modal" onclick="event.stopPropagation()"><h3>New Goal</h3><div class="form-group"><input type="text" id="goal-name" placeholder="Goal name"></div><div class="form-group"><input type="number" id="goal-target" placeholder="Target amount" step="1" min="1"></div><div class="form-group"><input type="date" id="goal-deadline" placeholder="Deadline (optional)"></div><div class="modal-btns"><button class="cancel" onclick="closeModal()">Cancel</button><button class="confirm" onclick="doAddGoal()">Create</button></div></div></div>`;
}

async function doAddGoal() {
  const name = document.getElementById("goal-name").value;
  const target = parseFloat(document.getElementById("goal-target").value);
  const deadline = document.getElementById("goal-deadline").value || null;
  if (!name || !target) return alert("Name and target required");
  try {
    await api("/goals", { method: "POST", body: { name, target, deadline } });
    closeModal(); loadGoals();
  } catch (e) { alert(e.message); }
}

async function showDeposit(id) {
  const modal = document.getElementById("modal-root");
  modal.innerHTML = `<div class="modal-overlay" onclick="closeModal()"><div class="modal" onclick="event.stopPropagation()"><h3>Deposit</h3><div class="form-group"><input type="number" id="dep-amount" placeholder="Amount" step="0.01" min="0.01"></div><div class="modal-btns"><button class="cancel" onclick="closeModal()">Cancel</button><button class="confirm" onclick="doDeposit(${id})">Deposit</button></div></div></div>`;
}

async function doDeposit(id) {
  const amount = parseFloat(document.getElementById("dep-amount").value);
  if (!amount || amount <= 0) return alert("Enter a valid amount");
  try {
    await api(`/goals/${id}/deposit`, { method: "POST", body: { amount } });
    closeModal(); loadGoals();
  } catch (e) { alert(e.message); }
}

async function deleteGoal(id) {
  if (!confirm("Delete this goal?")) return;
  try { await api(`/goals/${id}`, { method: "DELETE" }); loadGoals(); } catch (e) { alert(e.message); }
}

// ══════════════════════════════════════════════════════════════════
// TRENDS
// ══════════════════════════════════════════════════════════════════
async function loadTrends() {
  renderMonthNav("trends-month-nav", trendsMonth, (m) => { trendsMonth = m; loadTrends(); });
  try {
    const d = await api(`/trends?month=${trendsMonth}`);
    let html = '';
    if (d.breakdown.length > 0) {
      html += `<div class="card"><div class="card-title">Category Breakdown</div><div class="donut-container">${renderDonut(d.breakdown, d.total)}<div class="donut-legend">`;
      for (let i = 0; i < Math.min(d.breakdown.length, 8); i++) {
        const c = d.breakdown[i];
        html += `<div class="donut-legend-item"><div class="donut-dot" style="background:${DONUT_COLORS[i % DONUT_COLORS.length]}"></div>${esc(c.category)} (${c.pct}%)</div>`;
      }
      html += `</div></div></div><div class="card">`;
      for (const c of d.breakdown) {
        const pct = d.total > 0 ? (c.total / d.total * 100) : 0;
        html += `<div class="cat-row"><div class="cat-icon">${catIcon(c.category)}</div><div class="cat-info"><div class="cat-name">${esc(c.category)}</div><div class="cat-bar-bg"><div class="cat-bar-fill" style="width:${pct}%"></div></div></div><div><div class="cat-amount">$${c.total.toFixed(2)}</div><div class="cat-pct">${pct.toFixed(0)}%</div></div></div>`;
      }
      html += `</div>`;
    }
    if (d.recurring.length > 0) {
      html += `<div class="section-title">Recurring Expenses</div><div class="card">`;
      for (const r of d.recurring) {
        html += `<div class="recurring-row"><div class="recurring-info"><div class="recurring-desc">${esc(r.description)}</div><div class="recurring-detail">${esc(r.category || '')} &middot; ${r.month_count} months</div></div><div class="recurring-amount">~$${r.avg_amount.toFixed(2)}/mo</div></div>`;
      }
      html += `</div>`;
    }
    if (!html) html = `<div class="empty-state"><div class="icon">&#128202;</div><div class="msg">No expense data for this month</div></div>`;
    document.getElementById("trends-content").innerHTML = html;
  } catch (e) {
    document.getElementById("trends-content").innerHTML = `<div class="empty-state"><div class="msg">${esc(e.message)}</div></div>`;
  }
}

function renderDonut(breakdown, total) {
  const size = 120, cx = 60, cy = 60, r = 45, sw = 18;
  const circ = 2 * Math.PI * r;
  let offset = 0; let paths = '';
  for (let i = 0; i < Math.min(breakdown.length, 10); i++) {
    const pct = total > 0 ? breakdown[i].total / total : 0;
    const len = circ * pct;
    paths += `<circle cx="${cx}" cy="${cy}" r="${r}" fill="none" stroke="${DONUT_COLORS[i % DONUT_COLORS.length]}" stroke-width="${sw}" stroke-dasharray="${len} ${circ - len}" stroke-dashoffset="${-offset}" transform="rotate(-90 ${cx} ${cy})"/>`;
    offset += len;
  }
  return `<svg class="donut-svg" viewBox="0 0 ${size} ${size}">${paths}<text x="${cx}" y="${cy + 4}" text-anchor="middle" font-size="14" font-weight="600" fill="var(--text)">$${total.toFixed(0)}</text></svg>`;
}

// ══════════════════════════════════════════════════════════════════
// EVENTS
// ══════════════════════════════════════════════════════════════════
async function loadEvents() {
  try {
    const d = await api("/events");
    if (d.events.length === 0) {
      document.getElementById("events-content").innerHTML = `<div class="empty-state"><div class="icon">&#128197;</div><div class="msg">No events yet</div></div>`;
      return;
    }
    const colors = ["#1a6b3c","#2563eb","#dc2626","#f59e0b","#7c3aed","#14b8a6"];
    let html = '';
    for (const e of d.events) {
      const c = colors[e.color_index % colors.length];
      const s = e.summary || {};
      html += `<div class="card event-card" style="border-left-color:${c}" onclick="showEventDetail(${e.id})"><div class="event-name">${esc(e.name)}</div><div class="event-dates">${esc(e.start_date)} to ${esc(e.end_date)}</div><div class="event-summary"><span>&#128176; $${(s.total || 0).toFixed(2)}</span><span>&#128179; ${s.count || 0} txns</span></div></div>`;
    }
    document.getElementById("events-content").innerHTML = html;
  } catch (e) {
    document.getElementById("events-content").innerHTML = `<div class="empty-state"><div class="msg">${esc(e.message)}</div></div>`;
  }
}

async function showEventDetail(id) {
  try {
    const e = await api(`/events/${id}`);
    const modal = document.getElementById("modal-root");
    let txnHtml = '';
    for (const t of (e.transactions || [])) txnHtml += txnRowHtml(t);
    if (!txnHtml) txnHtml = '<div style="padding:12px;color:var(--text-muted)">No transactions</div>';
    const s = e.summary || {};
    modal.innerHTML = `<div class="modal-overlay" onclick="closeModal()"><div class="modal" onclick="event.stopPropagation()" style="max-height:80vh;overflow-y:auto"><h3>${esc(e.name)}</h3><div style="font-size:12px;color:var(--text-muted);margin-bottom:8px">${esc(e.start_date)} to ${esc(e.end_date)}</div><div style="font-size:14px;font-weight:600;margin-bottom:8px">Total: $${(s.total || 0).toFixed(2)} (${s.count} txns)</div>${txnHtml}<div class="modal-btns"><button class="cancel" onclick="deleteEvent(${e.id})">Delete</button><button class="confirm" onclick="closeModal()">Close</button></div></div></div>`;
  } catch (e) { alert(e.message); }
}

async function showAddEvent() {
  const modal = document.getElementById("modal-root");
  const today = new Date().toISOString().slice(0, 10);
  modal.innerHTML = `<div class="modal-overlay" onclick="closeModal()"><div class="modal" onclick="event.stopPropagation()"><h3>New Event</h3><div class="form-group"><input type="text" id="evt-name" placeholder="Event name"></div><div class="form-group"><input type="date" id="evt-start" value="${today}"></div><div class="form-group"><input type="date" id="evt-end" value="${today}"></div><div class="form-group"><input type="text" id="evt-keyword" placeholder="Location keyword (auto-match)"></div><div class="modal-btns"><button class="cancel" onclick="closeModal()">Cancel</button><button class="confirm" onclick="doAddEvent()">Create</button></div></div></div>`;
}

async function doAddEvent() {
  const name = document.getElementById("evt-name").value;
  if (!name) return alert("Name required");
  try {
    await api("/events", { method: "POST", body: { name, start_date: document.getElementById("evt-start").value, end_date: document.getElementById("evt-end").value, location_keyword: document.getElementById("evt-keyword").value } });
    closeModal(); loadEvents();
  } catch (e) { alert(e.message); }
}

async function deleteEvent(id) {
  if (!confirm("Delete this event?")) return;
  try { await api(`/events/${id}`, { method: "DELETE" }); closeModal(); loadEvents(); } catch (e) { alert(e.message); }
}

// ══════════════════════════════════════════════════════════════════
// BANK
// ══════════════════════════════════════════════════════════════════
async function loadBankAccounts() {
  try {
    const d = await api("/bank/accounts");
    let html = `<div class="card">
      <div class="btn-row">
        <button class="btn-success" onclick="plaidConnect()">&#127974; Connect Bank (Plaid)</button>
        <button class="btn-outline" onclick="mockBankConnect()">Mock Bank</button>
      </div>
    </div>`;
    if (d.accounts.length === 0) {
      html += `<div class="empty-state"><div class="icon">&#127974;</div><div class="msg">No bank accounts connected</div></div>`;
    } else {
      for (const a of d.accounts) {
        const syncBtn = a.access_token ? `<button class="btn-sm btn-outline" onclick="syncBank(${a.id})">Sync</button>` : '';
        html += `<div class="card bank-card">
          <div class="bank-icon">&#127974;</div>
          <div class="bank-info"><div class="bank-name">${esc(a.account_name || a.bank_name)}</div><div class="bank-detail">${esc(a.bank_name)} &middot; ${esc(a.account_number_masked)}</div><div class="bank-detail">Last sync: ${a.last_sync ? new Date(a.last_sync).toLocaleDateString() : 'never'}</div></div>
          <div style="display:flex;gap:4px;flex-direction:column">${syncBtn}<button class="btn-sm btn-outline" onclick="deleteBankAccount(${a.id})" style="color:var(--error);border-color:var(--error)">Remove</button></div>
        </div>`;
      }
    }
    document.getElementById("bank-content").innerHTML = html;
  } catch (e) {
    document.getElementById("bank-content").innerHTML = `<div class="empty-state"><div class="msg">${esc(e.message)}</div></div>`;
  }
}

async function plaidConnect() {
  try {
    const d = await api("/bank/connect/plaid/link", { method: "POST" });
    if (d.url) {
      // Open Plaid Hosted Link in new window
      const plaidWindow = window.open(d.url, "_blank");
      // Poll for completion — user will be redirected back after connecting
      const sessionId = d.session_id;
      const modal = document.getElementById("modal-root");
      modal.innerHTML = `<div class="modal-overlay"><div class="modal" style="text-align:center">
        <h3>Connecting to bank...</h3>
        <p style="color:var(--text-muted);font-size:13px;margin:12px 0">Complete the connection in the Plaid window, then click below.</p>
        <button class="btn-primary" onclick="completePlaid('${sessionId}')">I've finished connecting</button>
        <button class="btn-outline" style="margin-top:8px;width:100%" onclick="closeModal()">Cancel</button>
      </div></div>`;
    }
  } catch (e) {
    alert("Plaid not configured. Go to Settings and enter your Plaid Server URL and API Key.\n\n" + e.message);
  }
}

async function completePlaid(sessionId) {
  try {
    const d = await api("/bank/connect/plaid/complete", { method: "POST", body: { session_id: sessionId } });
    closeModal();
    if (d.message) alert(d.message);
    else alert(`Connected! ${d.accounts} account(s) added.`);
    loadBankAccounts();
    loadDashboard();
  } catch (e) { alert(e.message); }
}

async function mockBankConnect() {
  try {
    const d = await api("/bank/connect/mock", { method: "POST", body: { username: "demo", password: "demo" } });
    if (d.message) alert(d.message);
    else alert(`Connected! ${d.accounts} accounts, ${d.transactions} transactions imported.`);
    loadBankAccounts();
    loadDashboard();
  } catch (e) { alert(e.message); }
}

async function syncBank(id) {
  try {
    const d = await api(`/bank/sync/${id}`, { method: "POST" });
    alert(`Synced: ${d.added} added, ${d.removed} removed`);
    loadBankAccounts();
    loadDashboard();
  } catch (e) { alert(e.message); }
}

async function deleteBankAccount(id) {
  if (!confirm("Remove this bank account and all its synced transactions?")) return;
  try {
    await api(`/bank/accounts/${id}`, { method: "DELETE" });
    loadBankAccounts();
    loadDashboard();
  } catch (e) { alert(e.message); }
}

// ══════════════════════════════════════════════════════════════════
// SETTINGS
// ══════════════════════════════════════════════════════════════════
async function loadSettings() {
  try {
    const d = await api("/settings");
    const isDark = localStorage.getItem("cs_dark") === "1";
    let html = `
      <div class="card">
        <div class="toggle-row">
          <div class="toggle-label">Dark Mode</div>
          <button class="toggle ${isDark ? 'on' : ''}" onclick="toggleDark(this)"></button>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Classification</div>
        <div class="setting-group">
          <div class="setting-label">Gemini API Key</div>
          <input type="password" id="set-gemini" placeholder="${d.gemini_api_key === '***' ? 'Saved (hidden)' : 'For auto-classification'}">
          <div class="setting-hint">Free at aistudio.google.com — classifies unknown transactions</div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Plaid Bank Connection</div>
        <div class="setting-hint" style="margin-bottom:10px">The Plaid proxy server handles bank OAuth. One Plaid connection = one bank. All accounts under that bank share one access token.</div>
        <div class="setting-group">
          <div class="setting-label">Plaid Server URL</div>
          <input type="text" id="set-plaid-url" value="${esc(d.plaid_server_url || '')}" placeholder="https://your-server.ts.net">
        </div>
        <div class="setting-group">
          <div class="setting-label">Plaid API Key</div>
          <input type="password" id="set-plaid-key" placeholder="${d.plaid_api_key === '***' ? 'Saved (hidden)' : 'Shared secret (X-API-Key)'}">
        </div>
        <div class="setting-group">
          <div class="setting-label">Plaid Environment</div>
          <select id="set-plaid-env">
            <option value="sandbox" ${d.plaid_env === 'sandbox' ? 'selected' : ''}>Sandbox (test data)</option>
            <option value="production" ${d.plaid_env === 'production' ? 'selected' : ''}>Production (real banks)</option>
          </select>
          <div class="setting-hint">Plaid no longer offers Development — use Sandbox for testing, Production for real banks</div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Cloud Backup</div>
        <div class="setting-group">
          <div class="setting-label">JSONBin API Key</div>
          <input type="password" id="set-cloud-key" placeholder="${d.cloud_api_key === '***' ? 'Saved (hidden)' : 'jsonbin.io API key'}">
        </div>
        <div class="setting-group">
          <div class="setting-label">Bin ID</div>
          <input type="text" id="set-cloud-bin" value="${esc(d.cloud_bin_id || '')}" placeholder="Auto-created on first backup">
        </div>
        <div class="btn-row">
          <button class="btn-success" onclick="cloudBackup()">Backup</button>
          <button class="btn-outline" onclick="cloudRestore()">Restore</button>
        </div>
        <div id="cloud-status"></div>
      </div>

      <div class="card">
        <div class="card-title">Data Management</div>
        <div class="btn-row" style="margin-bottom:8px">
          <button class="btn-outline" onclick="exportData()">Export JSON</button>
          <button class="btn-outline" onclick="seedDemo()">Load Demo Data</button>
        </div>
        <button class="btn-danger btn-sm" style="width:100%;padding:10px" onclick="confirmClear()">Clear All Data</button>
      </div>

      <button class="btn-primary" onclick="saveAllSettings()" style="margin-bottom:12px">Save All Settings</button>
      <div id="settings-status"></div>
    `;
    document.getElementById("settings-content").innerHTML = html;
  } catch (e) {
    document.getElementById("settings-content").innerHTML = `<div class="empty-state"><div class="msg">${esc(e.message)}</div></div>`;
  }
}

function toggleDark(btn) {
  const isDark = document.body.classList.toggle("dark");
  btn.classList.toggle("on", isDark);
  localStorage.setItem("cs_dark", isDark ? "1" : "0");
}

async function saveAllSettings() {
  const body = {};
  const gemini = document.getElementById("set-gemini").value;
  const plaidUrl = document.getElementById("set-plaid-url").value;
  const plaidKey = document.getElementById("set-plaid-key").value;
  const plaidEnv = document.getElementById("set-plaid-env").value;
  if (gemini) body.gemini_api_key = gemini;
  if (plaidUrl) body.plaid_server_url = plaidUrl;
  if (plaidKey) body.plaid_api_key = plaidKey;
  body.plaid_env = plaidEnv;
  try {
    await api("/settings", { method: "POST", body });
    showStatus("settings-status", "Settings saved!", "ok");
  } catch (e) { showStatus("settings-status", e.message, "err"); }
}

async function cloudBackup() {
  const key = document.getElementById("set-cloud-key").value;
  const bin = document.getElementById("set-cloud-bin").value;
  if (key) await api("/settings", { method: "POST", body: { cloud_api_key: key, cloud_bin_id: bin } });
  try {
    const d = await api("/cloud/backup", { method: "POST" });
    if (d.success) {
      showStatus("cloud-status", "Backup complete!", "ok");
      if (d.bin_id) document.getElementById("set-cloud-bin").value = d.bin_id;
    } else showStatus("cloud-status", d.error, "err");
  } catch (e) { showStatus("cloud-status", e.message, "err"); }
}

async function cloudRestore() {
  const key = document.getElementById("set-cloud-key").value;
  const bin = document.getElementById("set-cloud-bin").value;
  if (key) await api("/settings", { method: "POST", body: { cloud_api_key: key, cloud_bin_id: bin } });
  if (!confirm("Import data from cloud backup?")) return;
  try {
    const d = await api("/cloud/restore", { method: "POST" });
    if (d.success) showStatus("cloud-status", "Restore complete!", "ok");
    else showStatus("cloud-status", d.error, "err");
  } catch (e) { showStatus("cloud-status", e.message, "err"); }
}

async function exportData() {
  try {
    const d = await api("/data/export");
    const blob = new Blob([JSON.stringify(d, null, 2)], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
    a.download = `clearspend-export-${new Date().toISOString().slice(0,10)}.json`; a.click();
  } catch (e) { alert(e.message); }
}

async function confirmClear() {
  if (!confirm("This will delete ALL data. Are you sure?")) return;
  if (!confirm("Really? This cannot be undone.")) return;
  try {
    await api("/data/clear", { method: "POST", body: {} });
    alert("All data cleared.");
    loadDashboard();
  } catch (e) { alert(e.message); }
}

async function seedDemo() {
  try {
    await api("/data/demo", { method: "POST" });
    alert("Demo data loaded!");
    loadDashboard(); loadMonthOptions();
  } catch (e) { alert(e.message); }
}

// ══════════════════════════════════════════════════════════════════
// HELPERS
// ══════════════════════════════════════════════════════════════════
function closeModal() { document.getElementById("modal-root").innerHTML = ""; }

function showStatus(id, msg, type) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = "status-msg " + type;
  el.textContent = msg;
  setTimeout(() => { el.textContent = ""; el.className = "status-msg"; }, 4000);
}

function renderMonthNav(containerId, month, onChange) {
  const d = new Date(month + "-01");
  const label = d.toLocaleDateString("en", { year: "numeric", month: "long" });
  document.getElementById(containerId).innerHTML = `<div class="month-nav"><button onclick="navMonth('${containerId}', '${month}', -1)">&#9664;</button><div class="month-label">${label}</div><button onclick="navMonth('${containerId}', '${month}', 1)">&#9654;</button></div>`;
  document.getElementById(containerId)._onChange = onChange;
}

function navMonth(containerId, current, delta) {
  const [y, m] = current.split("-").map(Number);
  let nm = m + delta, ny = y;
  if (nm > 12) { nm = 1; ny++; }
  if (nm < 1) { nm = 12; ny--; }
  const newMonth = `${ny}-${String(nm).padStart(2, "0")}`;
  const fn = document.getElementById(containerId)._onChange;
  if (fn) fn(newMonth);
}
