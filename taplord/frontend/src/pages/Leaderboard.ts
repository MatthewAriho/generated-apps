import { leaderboard, LeaderboardEntry, ShameEntry } from "../api";
import { getUsername } from "../auth";

export function renderLeaderboard(): string {
  return `
    <div class="leaderboard-page">
      <div class="leaderboard-header">
        <h1>&#127942; Leaderboard</h1>
      </div>

      <div class="lb-tabs" id="lb-period-tabs">
        <button class="lb-tab active" data-period="week">Week</button>
        <button class="lb-tab" data-period="month">Month</button>
        <button class="lb-tab" data-period="season">Season</button>
        <button class="lb-tab" data-period="all_time">All Time</button>
        <button class="lb-tab lb-tab-shame" data-period="shame">&#128128; Shame</button>
      </div>

      <div class="lb-category-wrap" id="lb-category-wrap">
        <select id="lb-category" class="lb-category-select">
          <option value="total_beers">Total Beers</option>
          <option value="unique_beers">Unique Beers</option>
          <option value="events_attended">Events Attended</option>
          <option value="longest_event">Longest Event</option>
          <option value="most_single_event">Most in Single Event</option>
          <option value="current_streak">Current Streak</option>
        </select>
      </div>

      <div id="lb-content" class="lb-content">
        <div class="loading-spinner">Loading rankings...</div>
      </div>
    </div>
  `;
}

export async function initLeaderboard(): Promise<void> {
  let currentPeriod = "week";
  let currentCategory = "total_beers";
  let isShame = false;

  const content = document.getElementById("lb-content");
  const categoryWrap = document.getElementById("lb-category-wrap") as HTMLElement;

  // Period tabs
  document.querySelectorAll("#lb-period-tabs .lb-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll("#lb-period-tabs .lb-tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      const period = tab.getAttribute("data-period") || "week";
      if (period === "shame") {
        isShame = true;
        categoryWrap.style.display = "none";
        loadShame();
      } else {
        isShame = false;
        currentPeriod = period;
        categoryWrap.style.display = "block";
        loadLeaderboard();
      }
    });
  });

  // Category select
  document.getElementById("lb-category")?.addEventListener("change", (e) => {
    currentCategory = (e.target as HTMLSelectElement).value;
    loadLeaderboard();
  });

  async function loadLeaderboard(): Promise<void> {
    if (!content) return;
    content.innerHTML = '<div class="loading-spinner">Loading...</div>';

    try {
      const entries = await leaderboard.get(currentPeriod, currentCategory);
      if (entries.length === 0) {
        content.innerHTML = '<div class="empty-state">No data yet. Start drinking! &#127866;</div>';
        return;
      }
      content.innerHTML = renderEntries(entries);
    } catch (err: any) {
      content.innerHTML = `<div class="error-state">Failed to load leaderboard</div>`;
    }
  }

  async function loadShame(): Promise<void> {
    if (!content) return;
    content.innerHTML = '<div class="loading-spinner">Loading shame...</div>';

    try {
      const entries = await leaderboard.shame();
      if (entries.length === 0) {
        content.innerHTML = '<div class="empty-state">No shame... yet. &#128064;</div>';
        return;
      }
      content.innerHTML = renderShameEntries(entries);
    } catch {
      content.innerHTML = `<div class="error-state">Failed to load shame board</div>`;
    }
  }

  // Initial load
  await loadLeaderboard();
}

function renderEntries(entries: LeaderboardEntry[]): string {
  const currentUser = getUsername();

  return `<div class="lb-list">
    ${entries
      .map((e, i) => {
        const rank = e.rank || i + 1;
        const isFirst = rank === 1;
        const isMe = e.username === currentUser;

        return `
        <div class="lb-row ${isFirst ? "lb-row-first" : ""} ${isMe ? "lb-row-me" : ""}">
          <span class="lb-rank ${isFirst ? "lb-rank-crown" : ""}">${isFirst ? "&#128081;" : "#" + rank}</span>
          <span class="lb-avatar" style="background:${e.avatar_color}">${e.display_name.charAt(0).toUpperCase()}</span>
          <div class="lb-user-info">
            <span class="lb-name">${escapeHtml(e.display_name)}</span>
            <span class="lb-username">@${escapeHtml(e.username)}</span>
          </div>
          <div class="lb-value-wrap">
            <span class="lb-value">${e.value}</span>
            <span class="lb-value-label">${escapeHtml(e.label || "beers")}</span>
          </div>
        </div>
      `;
      })
      .join("")}
  </div>`;
}

function renderShameEntries(entries: ShameEntry[]): string {
  const currentUser = getUsername();

  return `<div class="lb-list lb-shame-list">
    <div class="shame-header-row">
      <span class="shame-col-rank"></span>
      <span class="shame-col-user">User</span>
      <span class="shame-col-stat">&#128565; Blackouts</span>
      <span class="shame-col-stat">&#129326; Vomits</span>
      <span class="shame-col-stat">Total</span>
    </div>
    ${entries
      .map((e, i) => {
        const isMe = e.username === currentUser;
        return `
        <div class="lb-row lb-shame-row ${i === 0 ? "lb-row-first" : ""} ${isMe ? "lb-row-me" : ""}">
          <span class="lb-rank">${i === 0 ? "&#128128;" : "#" + (i + 1)}</span>
          <div class="lb-user-info">
            <span class="lb-avatar" style="background:${e.avatar_color}">${e.display_name.charAt(0).toUpperCase()}</span>
            <span class="lb-name">${escapeHtml(e.display_name)}</span>
          </div>
          <span class="shame-stat">${e.blackouts}</span>
          <span class="shame-stat">${e.vomits}</span>
          <span class="shame-stat shame-total">${e.total}</span>
        </div>
      `;
      })
      .join("")}
  </div>`;
}

function escapeHtml(s: string): string {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}
