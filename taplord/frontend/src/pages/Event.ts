import { events, checkins, EventData, CheckInData } from "../api";
import { navigate } from "../router";

export function renderEvent(): string {
  return `
    <div class="event-page">
      <div id="event-content" class="event-content">
        <div class="loading-spinner">Loading event...</div>
      </div>
    </div>
  `;
}

export async function initEvent(eventId: string): Promise<void> {
  const container = document.getElementById("event-content");
  if (!container) return;

  let event: EventData;
  let eventCheckins: CheckInData[];

  try {
    event = await events.get(Number(eventId));
    eventCheckins = await checkins.list(event.id);
  } catch (err: any) {
    container.innerHTML = `<div class="error-state">Event not found. <a href="#/history">Back to history</a></div>`;
    return;
  }

  const startTime = new Date(event.started_at).getTime();
  const endTime = event.ended_at ? new Date(event.ended_at).getTime() : Date.now();
  const duration = endTime - startTime;
  const uniqueBeers = new Set(eventCheckins.map((c) => c.beer_name.toLowerCase())).size;

  container.innerHTML = `
    <div class="event-detail-card">
      <button class="btn-back" id="btn-back-history">&larr; Back</button>

      <div class="event-detail-header">
        <span class="event-type-badge">${formatEventType(event.event_type)}</span>
        <h2 class="event-detail-name" id="event-title">${escapeHtml(event.name)}</h2>
        <span class="event-detail-date">${formatDate(event.started_at)}</span>
        <span class="event-detail-status ${event.is_active ? "status-active" : "status-ended"}">${event.is_active ? "LIVE" : "Ended"}</span>
      </div>

      <div class="event-stats-grid">
        <div class="stat-card">
          <span class="stat-icon">&#127866;</span>
          <span class="stat-value">${eventCheckins.length}</span>
          <span class="stat-label">Total Beers</span>
        </div>
        <div class="stat-card">
          <span class="stat-icon">&#9201;</span>
          <span class="stat-value">${formatDuration(duration)}</span>
          <span class="stat-label">Duration</span>
        </div>
        <div class="stat-card">
          <span class="stat-icon">&#127775;</span>
          <span class="stat-value">${uniqueBeers}</span>
          <span class="stat-label">Unique Beers</span>
        </div>
      </div>

      <div class="event-edit-section">
        <h3 class="section-title">Edit Event</h3>
        <div class="form-group">
          <label>Event Name</label>
          <input type="text" id="edit-event-name" class="input-medium" value="${escapeAttr(event.name)}" />
        </div>
        <div class="form-group">
          <label>Event Type</label>
          <select id="edit-event-type" class="input-medium">
            <option value="night_out" ${event.event_type === "night_out" ? "selected" : ""}>Night Out</option>
            <option value="pub_crawl" ${event.event_type === "pub_crawl" ? "selected" : ""}>Pub Crawl</option>
            <option value="day_drinking" ${event.event_type === "day_drinking" ? "selected" : ""}>Day Drinking</option>
            <option value="beer_run" ${event.event_type === "beer_run" ? "selected" : ""}>Beer Run</option>
            <option value="custom" ${event.event_type === "custom" ? "selected" : ""}>Custom</option>
          </select>
        </div>
        <div class="form-group">
          <label>Venue</label>
          <input type="text" id="edit-event-venue" class="input-medium" value="${escapeAttr(event.venue_description || "")}" placeholder="Where were you?" />
        </div>
        <div class="toggle-row">
          <label class="toggle-label">
            <input type="checkbox" id="edit-blacked-out" ${event.blacked_out ? "checked" : ""} />
            <span class="toggle-text">&#128565; Blacked Out</span>
          </label>
        </div>
        <div class="toggle-row">
          <label class="toggle-label">
            <input type="checkbox" id="edit-vomited" ${event.vomited ? "checked" : ""} />
            <span class="toggle-text">&#129326; Vomited</span>
          </label>
        </div>
        <button class="btn btn-primary" id="btn-save-event">Save Changes</button>
      </div>

      <div class="event-checkins-section">
        <h3 class="section-title">All Check-ins (${eventCheckins.length})</h3>
        <div class="checkin-full-list">
          ${eventCheckins.length === 0 ? '<p class="empty-state">No check-ins recorded.</p>' :
            eventCheckins
              .slice()
              .reverse()
              .map(
                (c) => `
              <div class="checkin-full-item">
                <div class="checkin-full-left">
                  <span class="checkin-full-name">${escapeHtml(c.beer_name)}</span>
                  <span class="checkin-full-detail">${formatSize(c.size_ml)}${c.brewery ? " - " + escapeHtml(c.brewery) : ""}${c.beer_style ? " (" + escapeHtml(c.beer_style) + ")" : ""}</span>
                  ${c.rating ? `<span class="checkin-full-rating">${"&#9733;".repeat(c.rating)}${"&#9734;".repeat(5 - c.rating)}</span>` : ""}
                  ${c.notes ? `<span class="checkin-full-notes">${escapeHtml(c.notes)}</span>` : ""}
                </div>
                <span class="checkin-full-time">${formatTime(c.created_at)}</span>
              </div>
            `
              )
              .join("")}
        </div>
      </div>

      <div class="event-danger-zone">
        <button class="btn btn-danger" id="btn-delete-event">Delete Event</button>
      </div>
    </div>
  `;

  // Back button
  document.getElementById("btn-back-history")?.addEventListener("click", () => {
    navigate("/history");
  });

  // Save changes
  document.getElementById("btn-save-event")?.addEventListener("click", async () => {
    const name = (document.getElementById("edit-event-name") as HTMLInputElement).value.trim();
    const eventType = (document.getElementById("edit-event-type") as HTMLSelectElement).value;
    const venue = (document.getElementById("edit-event-venue") as HTMLInputElement).value.trim();
    const blackedOut = (document.getElementById("edit-blacked-out") as HTMLInputElement).checked;
    const vomited = (document.getElementById("edit-vomited") as HTMLInputElement).checked;

    try {
      await events.update(event.id, {
        name: name || event.name,
        event_type: eventType,
        venue_description: venue || undefined,
        blacked_out: blackedOut,
        vomited: vomited,
      });
      showToast("Event updated!");
    } catch (err: any) {
      alert(err.message || "Failed to save");
    }
  });

  // Delete event
  document.getElementById("btn-delete-event")?.addEventListener("click", async () => {
    if (!confirm("Are you sure you want to delete this event? This cannot be undone.")) return;
    try {
      await events.delete(event.id);
      navigate("/history");
    } catch (err: any) {
      alert(err.message || "Failed to delete");
    }
  });
}

function showToast(msg: string): void {
  const toast = document.createElement("div");
  toast.className = "toast toast-success";
  toast.textContent = msg;
  document.body.appendChild(toast);
  setTimeout(() => toast.classList.add("toast-visible"), 10);
  setTimeout(() => {
    toast.classList.remove("toast-visible");
    setTimeout(() => toast.remove(), 300);
  }, 2000);
}

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
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
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
  return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString([], { weekday: "short", month: "short", day: "numeric", year: "numeric" });
}

function escapeHtml(s: string): string {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function escapeAttr(s: string): string {
  return s.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
