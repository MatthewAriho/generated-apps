import { events, checkins, beers, leaderboard, EventData, CheckInData, BeerData, LeaderboardEntry } from "../api";
import { navigate } from "../router";

let activeEvent: EventData | null = null;
let eventCheckins: CheckInData[] = [];
let timerInterval: ReturnType<typeof setInterval> | null = null;
let searchTimeout: ReturnType<typeof setTimeout> | null = null;

export function renderHome(): string {
  return `
    <div class="home-page">
      <div id="home-content" class="home-content">
        <div class="loading-spinner">Loading...</div>
      </div>
    </div>
  `;
}

export async function initHome(): Promise<void> {
  const container = document.getElementById("home-content");
  if (!container) return;

  try {
    activeEvent = await events.active();
  } catch {
    activeEvent = null;
  }

  if (activeEvent) {
    await renderActiveEvent(container);
  } else {
    renderStartEvent(container);
  }

  renderMiniLeaderboard(container);
}

async function renderActiveEvent(container: HTMLElement): Promise<void> {
  try {
    eventCheckins = await checkins.list(activeEvent!.id);
  } catch {
    eventCheckins = [];
  }

  const beerCount = eventCheckins.length;
  const startTime = new Date(activeEvent!.started_at).getTime();

  container.innerHTML = `
    <div class="active-event-card">
      <div class="event-header">
        <div class="event-info">
          <span class="event-type-badge">${formatEventType(activeEvent!.event_type)}</span>
          <h2 class="event-name">${escapeHtml(activeEvent!.name)}</h2>
        </div>
        <div class="event-stats-row">
          <div class="event-stat">
            <span class="event-stat-value" id="beer-count">&#127866; ${beerCount}</span>
            <span class="event-stat-label">beers</span>
          </div>
          <div class="event-stat">
            <span class="event-stat-value" id="event-timer">${formatDuration(Date.now() - startTime)}</span>
            <span class="event-stat-label">duration</span>
          </div>
        </div>
      </div>

      <button class="btn btn-checkin" id="btn-add-beer">
        <span class="checkin-icon">&#127866;&#65039;</span>
        <span class="checkin-text">Add Beer</span>
      </button>

      <div id="checkin-flow" class="checkin-flow" style="display:none"></div>

      <div class="recent-checkins" id="recent-checkins">
        <h3 class="section-title">Recent Check-ins</h3>
        ${renderCheckinList(eventCheckins)}
      </div>

      <button class="btn btn-secondary btn-end-event" id="btn-end-event">
        End Event &#127937;
      </button>
    </div>

    <div id="mini-leaderboard-slot"></div>
  `;

  // Timer
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    const el = document.getElementById("event-timer");
    if (el) {
      el.textContent = formatDuration(Date.now() - startTime);
    }
  }, 1000);

  // Add Beer button
  document.getElementById("btn-add-beer")?.addEventListener("click", () => {
    showCheckinFlow();
  });

  // End Event button
  document.getElementById("btn-end-event")?.addEventListener("click", async () => {
    if (!confirm("End this event?")) return;
    try {
      await events.end(activeEvent!.id);
      if (timerInterval) clearInterval(timerInterval);
      activeEvent = null;
      const content = document.getElementById("home-content");
      if (content) {
        renderStartEvent(content);
        renderMiniLeaderboard(content);
      }
    } catch (err: any) {
      alert(err.message || "Failed to end event");
    }
  });

  // Quick repeat buttons
  bindRepeatButtons();
}

function renderCheckinList(items: CheckInData[]): string {
  if (items.length === 0) {
    return '<p class="empty-state">No beers logged yet. Tap "Add Beer" to get started!</p>';
  }

  return `<div class="checkin-list">
    ${items
      .slice()
      .reverse()
      .map(
        (c) => `
      <div class="checkin-item">
        <div class="checkin-beer-info">
          <span class="checkin-beer-name">${escapeHtml(c.beer_name)}</span>
          <span class="checkin-beer-detail">${formatSize(c.size_ml)}${c.brewery ? " - " + escapeHtml(c.brewery) : ""}</span>
        </div>
        <div class="checkin-actions">
          <button class="btn btn-pill btn-repeat" data-checkin-id="${c.id}" title="Quick repeat +1">+1</button>
          <button class="btn btn-pill btn-delete-checkin" data-checkin-id="${c.id}" title="Remove">&#128465;</button>
        </div>
        <span class="checkin-time">${formatTime(c.created_at)}</span>
      </div>
    `
      )
      .join("")}
  </div>`;
}

function bindRepeatButtons(): void {
  document.querySelectorAll(".btn-repeat").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const id = Number((e.currentTarget as HTMLElement).getAttribute("data-checkin-id"));
      if (!id) return;
      (e.currentTarget as HTMLButtonElement).disabled = true;
      try {
        const newCheckin = await checkins.repeat(activeEvent!.id, id);
        eventCheckins.push(newCheckin);
        refreshCheckinUI();
      } catch (err: any) {
        alert(err.message || "Repeat failed");
      }
    });
  });

  document.querySelectorAll(".btn-delete-checkin").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      const id = Number((e.currentTarget as HTMLElement).getAttribute("data-checkin-id"));
      if (!id || !confirm("Remove this check-in?")) return;
      try {
        await checkins.delete(id);
        eventCheckins = eventCheckins.filter((c) => c.id !== id);
        refreshCheckinUI();
      } catch (err: any) {
        alert(err.message || "Delete failed");
      }
    });
  });
}

function refreshCheckinUI(): void {
  const countEl = document.getElementById("beer-count");
  if (countEl) countEl.textContent = `\u{1F37A} ${eventCheckins.length}`;

  const listEl = document.getElementById("recent-checkins");
  if (listEl) {
    listEl.innerHTML = `<h3 class="section-title">Recent Check-ins</h3>${renderCheckinList(eventCheckins)}`;
    bindRepeatButtons();
  }
}

// ==================== CHECK-IN FLOW ====================

function showCheckinFlow(): void {
  const flow = document.getElementById("checkin-flow");
  if (!flow) return;
  flow.style.display = "block";
  document.getElementById("btn-add-beer")?.classList.add("hidden");

  flow.innerHTML = `
    <div class="checkin-step">
      <h3>What are you drinking?</h3>
      <div class="beer-search-wrap">
        <input type="text" id="beer-search-input" class="input-large" placeholder="Beer name..." autocomplete="off" autocapitalize="none" />
        <div id="beer-suggestions" class="beer-suggestions"></div>
      </div>

      <div id="size-step" style="display:none">
        <h3>Size</h3>
        <div class="size-pills">
          <button class="btn btn-size-pill" data-ml="355">12oz</button>
          <button class="btn btn-size-pill" data-ml="473">16oz</button>
          <button class="btn btn-size-pill" data-ml="591">20oz</button>
          <button class="btn btn-size-pill" data-ml="335">335ml</button>
          <button class="btn btn-size-pill" data-ml="500">500ml</button>
          <button class="btn btn-size-pill btn-size-custom" id="btn-custom-size">Custom</button>
        </div>
        <div id="custom-size-wrap" class="custom-size-wrap" style="display:none">
          <input type="number" id="custom-size-input" class="input-medium" placeholder="ml" min="50" max="5000" />
          <button class="btn btn-primary" id="btn-custom-size-confirm">OK</button>
        </div>
      </div>

      <button class="btn btn-secondary btn-cancel-checkin" id="btn-cancel-checkin">Cancel</button>
    </div>
  `;

  const input = document.getElementById("beer-search-input") as HTMLInputElement;
  const suggestions = document.getElementById("beer-suggestions")!;
  let selectedBeer: BeerData | null = null;
  let selectedBeerName = "";

  input.focus();

  input.addEventListener("input", () => {
    const q = input.value.trim();
    if (q.length < 2) {
      suggestions.innerHTML = "";
      suggestions.style.display = "none";
      return;
    }

    if (searchTimeout) clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
      try {
        const results = await beers.search(q);
        if (results.length === 0) {
          suggestions.innerHTML = `<div class="suggestion-item suggestion-create" data-action="create">Use "${escapeHtml(q)}" as beer name</div>`;
        } else {
          suggestions.innerHTML = results
            .slice(0, 8)
            .map(
              (b) =>
                `<div class="suggestion-item" data-beer-id="${b.id}" data-beer-name="${escapeAttr(b.name)}">
                  <span class="suggestion-name">${escapeHtml(b.name)}</span>
                  ${b.brewery ? `<span class="suggestion-brewery">${escapeHtml(b.brewery)}</span>` : ""}
                  ${b.abv ? `<span class="suggestion-abv">${b.abv}%</span>` : ""}
                </div>`
            )
            .join("");
          suggestions.innerHTML += `<div class="suggestion-item suggestion-create" data-action="create">Use "${escapeHtml(q)}" instead</div>`;
        }
        suggestions.style.display = "block";
      } catch {
        suggestions.innerHTML = `<div class="suggestion-item suggestion-create" data-action="create">Use "${escapeHtml(q)}" as beer name</div>`;
        suggestions.style.display = "block";
      }
    }, 250);
  });

  // Also allow pressing Enter on the input to proceed with free text
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      const q = input.value.trim();
      if (q.length > 0) {
        selectedBeer = null;
        selectedBeerName = q;
        suggestions.style.display = "none";
        showSizeStep();
      }
    }
  });

  suggestions.addEventListener("click", (e) => {
    const item = (e.target as HTMLElement).closest(".suggestion-item") as HTMLElement;
    if (!item) return;

    if (item.getAttribute("data-action") === "create") {
      selectedBeer = null;
      selectedBeerName = input.value.trim();
    } else {
      const beerId = Number(item.getAttribute("data-beer-id"));
      selectedBeerName = item.getAttribute("data-beer-name") || input.value.trim();
      selectedBeer = { id: beerId } as BeerData;
    }

    input.value = selectedBeerName;
    suggestions.style.display = "none";
    showSizeStep();
  });

  function showSizeStep(): void {
    const sizeStep = document.getElementById("size-step");
    if (sizeStep) sizeStep.style.display = "block";
    input.disabled = true;
  }

  // Size pill clicks
  flow.addEventListener("click", async (e) => {
    const target = e.target as HTMLElement;

    // Size pill
    if (target.classList.contains("btn-size-pill") && !target.classList.contains("btn-size-custom")) {
      const ml = Number(target.getAttribute("data-ml"));
      if (ml) await submitCheckin(selectedBeerName, ml, selectedBeer?.id);
      return;
    }

    // Custom size toggle
    if (target.id === "btn-custom-size") {
      const wrap = document.getElementById("custom-size-wrap");
      if (wrap) wrap.style.display = "flex";
      (document.getElementById("custom-size-input") as HTMLInputElement)?.focus();
      return;
    }

    // Custom size confirm
    if (target.id === "btn-custom-size-confirm") {
      const val = Number((document.getElementById("custom-size-input") as HTMLInputElement)?.value);
      if (val >= 50 && val <= 5000) {
        await submitCheckin(selectedBeerName, val, selectedBeer?.id);
      }
      return;
    }

    // Cancel
    if (target.id === "btn-cancel-checkin") {
      hideCheckinFlow();
    }
  });
}

async function submitCheckin(beerName: string, sizeMl: number, beerId?: number): Promise<void> {
  if (!activeEvent) return;
  const flow = document.getElementById("checkin-flow");

  try {
    const data: any = { beer_name: beerName, size_ml: sizeMl };
    if (beerId) data.beer_id = beerId;

    const newCheckin = await checkins.add(activeEvent.id, data);
    eventCheckins.push(newCheckin);

    // Show success animation
    showCheckinSuccess(beerName);
    refreshCheckinUI();
    hideCheckinFlow();
  } catch (err: any) {
    alert(err.message || "Check-in failed");
  }
}

function hideCheckinFlow(): void {
  const flow = document.getElementById("checkin-flow");
  if (flow) {
    flow.style.display = "none";
    flow.innerHTML = "";
  }
  document.getElementById("btn-add-beer")?.classList.remove("hidden");
}

function showCheckinSuccess(beerName: string): void {
  const toast = document.createElement("div");
  toast.className = "toast toast-success";
  toast.innerHTML = `&#127866; <strong>${escapeHtml(beerName)}</strong> logged!`;
  document.body.appendChild(toast);
  setTimeout(() => toast.classList.add("toast-visible"), 10);
  setTimeout(() => {
    toast.classList.remove("toast-visible");
    setTimeout(() => toast.remove(), 300);
  }, 2000);
}

// ==================== START EVENT ====================

function renderStartEvent(container: HTMLElement): void {
  container.innerHTML = `
    <div class="start-event-section">
      <div class="start-hero">
        <div class="start-emoji">&#127866;</div>
        <h2>Ready to drink?</h2>
        <p class="start-subtext">Start an event to begin tracking</p>
      </div>

      <div class="start-form">
        <div class="form-group">
          <input type="text" id="event-name-input" class="input-large" placeholder="Event name (e.g. Friday Night)" />
        </div>
        <div class="form-group">
          <div class="event-type-pills">
            <button class="btn btn-type-pill active" data-type="night_out">&#127769; Night Out</button>
            <button class="btn btn-type-pill" data-type="pub_crawl">&#127867; Pub Crawl</button>
            <button class="btn btn-type-pill" data-type="day_drinking">&#9728;&#65039; Day Drinking</button>
            <button class="btn btn-type-pill" data-type="beer_run">&#127939; Beer Run</button>
          </div>
        </div>
        <button class="btn btn-primary btn-large btn-start-event" id="btn-start-event">
          &#127866; Start Event
        </button>
      </div>
    </div>

    <div id="mini-leaderboard-slot"></div>
  `;

  let selectedType = "night_out";

  document.querySelectorAll(".btn-type-pill").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".btn-type-pill").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      selectedType = btn.getAttribute("data-type") || "night_out";
    });
  });

  document.getElementById("btn-start-event")?.addEventListener("click", async () => {
    const nameInput = document.getElementById("event-name-input") as HTMLInputElement;
    const name = nameInput?.value.trim() || "Untitled Event";
    const btn = document.getElementById("btn-start-event") as HTMLButtonElement;
    btn.disabled = true;
    btn.textContent = "Starting...";

    try {
      activeEvent = await events.start(name, selectedType);
      const content = document.getElementById("home-content");
      if (content) {
        await renderActiveEvent(content);
        renderMiniLeaderboard(content);
      }
    } catch (err: any) {
      alert(err.message || "Failed to start event");
      btn.disabled = false;
      btn.innerHTML = "&#127866; Start Event";
    }
  });
}

// ==================== MINI LEADERBOARD ====================

async function renderMiniLeaderboard(container: HTMLElement): Promise<void> {
  const slot = container.querySelector("#mini-leaderboard-slot") || container;
  try {
    const entries = await leaderboard.get("week", "total_beers");
    const top3 = entries.slice(0, 3);
    if (top3.length === 0) {
      slot.innerHTML = "";
      return;
    }

    const slotEl = container.querySelector("#mini-leaderboard-slot");
    if (slotEl) {
      slotEl.innerHTML = `
        <div class="mini-leaderboard">
          <div class="mini-lb-header">
            <h3>&#127942; This Week</h3>
            <a href="#/leaderboard" class="mini-lb-link">See all</a>
          </div>
          <div class="mini-lb-list">
            ${top3
              .map(
                (e, i) => `
              <div class="mini-lb-row ${i === 0 ? "mini-lb-first" : ""}">
                <span class="mini-lb-rank">${i === 0 ? "&#128081;" : "#" + (i + 1)}</span>
                <span class="mini-lb-avatar" style="background:${e.avatar_color}">${e.display_name.charAt(0).toUpperCase()}</span>
                <span class="mini-lb-name">${escapeHtml(e.display_name)}</span>
                <span class="mini-lb-value">${e.value} &#127866;</span>
              </div>
            `
              )
              .join("")}
          </div>
        </div>
      `;
    }
  } catch {
    // Leaderboard not available yet, no problem
  }
}

// ==================== HELPERS ====================

function formatEventType(type: string): string {
  const map: Record<string, string> = {
    night_out: "&#127769; Night Out",
    pub_crawl: "&#127867; Pub Crawl",
    day_drinking: "&#9728;&#65039; Day Drinking",
    beer_run: "&#127939; Beer Run",
    custom: "&#127866; Custom",
  };
  return map[type] || type;
}

function formatDuration(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  if (h > 0) return `${h}h ${String(m).padStart(2, "0")}m`;
  return `${m}m ${String(s).padStart(2, "0")}s`;
}

function formatSize(ml: number): string {
  if (ml === 355) return "12oz";
  if (ml === 473) return "16oz";
  if (ml === 591) return "20oz";
  if (ml === 335) return "335ml";
  if (ml === 500) return "500ml";
  return `${ml}ml`;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function escapeHtml(s: string): string {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function escapeAttr(s: string): string {
  return s.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

export function destroyHome(): void {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}
