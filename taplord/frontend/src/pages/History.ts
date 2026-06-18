import { events, EventData } from "../api";

export function renderHistory(): string {
  return `
    <div class="history-page">
      <h1 class="page-title">&#128197; Event History</h1>
      <div id="history-content" class="history-content">
        <div class="loading-spinner">Loading events...</div>
      </div>
    </div>
  `;
}

export async function initHistory(): Promise<void> {
  const container = document.getElementById("history-content");
  if (!container) return;

  try {
    const allEvents = await events.list();
    const pastEvents = allEvents.filter((e) => !e.is_active).sort((a, b) => {
      return new Date(b.started_at).getTime() - new Date(a.started_at).getTime();
    });

    if (pastEvents.length === 0) {
      container.innerHTML = `
        <div class="empty-state-large">
          <span class="empty-emoji">&#127866;</span>
          <p>No past events yet.</p>
          <p class="empty-subtext">Start an event from the home page to begin tracking!</p>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div class="history-list">
        ${pastEvents.map((e) => renderEventCard(e)).join("")}
      </div>
    `;

    // Click handlers
    container.querySelectorAll(".history-card").forEach((card) => {
      card.addEventListener("click", () => {
        const id = card.getAttribute("data-event-id");
        if (id) window.location.hash = `/event/${id}`;
      });
    });
  } catch (err: any) {
    container.innerHTML = `<div class="error-state">Failed to load events. ${escapeHtml(err.message || "")}</div>`;
  }
}

function renderEventCard(event: EventData): string {
  const start = new Date(event.started_at);
  const end = event.ended_at ? new Date(event.ended_at) : null;
  const duration = end ? end.getTime() - start.getTime() : 0;
  const beerCount = event.checkin_count ?? 0;

  return `
    <div class="history-card" data-event-id="${event.id}">
      <div class="history-card-top">
        <span class="event-type-badge badge-small">${formatEventType(event.event_type)}</span>
        <span class="history-date">${formatDate(event.started_at)}</span>
      </div>
      <h3 class="history-event-name">${escapeHtml(event.name)}</h3>
      <div class="history-card-stats">
        <span class="history-stat">&#127866; ${beerCount} beers</span>
        ${duration > 0 ? `<span class="history-stat">&#9201; ${formatDuration(duration)}</span>` : ""}
        ${event.blacked_out ? '<span class="history-stat history-shame">&#128565; Blackout</span>' : ""}
        ${event.vomited ? '<span class="history-stat history-shame">&#129326; Vomited</span>' : ""}
      </div>
    </div>
  `;
}

function formatEventType(type: string): string {
  const map: Record<string, string> = {
    night_out: "&#127769;",
    pub_crawl: "&#127867;",
    day_drinking: "&#9728;&#65039;",
    beer_run: "&#127939;",
    custom: "&#127866;",
  };
  return map[type] || "&#127866;";
}

function formatDuration(ms: number): string {
  const h = Math.floor(ms / 3600000);
  const m = Math.floor((ms % 3600000) / 60000);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
}

function escapeHtml(s: string): string {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}
