import { analytics as analyticsApi, type AnalyticsOverview, ApiError } from "../api";

export function renderAnalytics(): string {
  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Analytics</h1>
        <p class="page-subtitle">Your reading insights</p>
      </div>
    </div>
    <div id="analytics-body">
      <div class="loading-center"><div class="spinner"></div></div>
    </div>
  `;
}

document.addEventListener("page:mounted", async (e: Event) => {
  const route = (e as CustomEvent).detail;
  if (route?.name !== "analytics") return;

  const body = document.getElementById("analytics-body")!;

  try {
    const [overview, speedData, genreData, sessionsData] = await Promise.all([
      analyticsApi.overview(),
      analyticsApi.speed(),
      analyticsApi.genres(),
      analyticsApi.sessions(),
    ]);

    body.innerHTML = buildAnalyticsHtml(overview, speedData, genreData, sessionsData as any[]);
  } catch (err) {
    body.innerHTML = `<div class="form-error">${err instanceof ApiError ? err.message : "Could not load analytics"}</div>`;
  }
});

function buildAnalyticsHtml(
  overview: AnalyticsOverview,
  speed: { week: string; wpm: number; hours: number }[],
  genres: { genre: string; count: number; percentage: number }[],
  sessions: any[]
): string {
  return `
    <!-- Stats cards -->
    <div class="stats-grid">
      ${statCard("Total Books", overview.total_books, "in your library")}
      ${statCard("Hours Read", overview.total_hours_read, "total reading time")}
      ${statCard("Avg WPM", overview.avg_wpm, "words per minute")}
      ${statCard("This Month", overview.books_this_month, "books finished")}
      ${statCard("Reading", overview.books_reading, "currently active")}
      ${statCard("Finished", overview.books_read, "books completed")}
    </div>

    <!-- Speed trend -->
    <div class="chart-section">
      <div class="chart-title">Reading Speed (WPM by week)</div>
      ${buildSpeedChart(speed)}
    </div>

    <!-- Genres -->
    <div class="chart-section">
      <div class="chart-title">Genre Breakdown</div>
      ${buildGenreChart(genres)}
    </div>

    <!-- Recent sessions -->
    <div class="chart-section">
      <div class="chart-title">Recent Sessions</div>
      ${buildSessionsTable(sessions)}
    </div>
  `;
}

function statCard(label: string, value: number | string, sub: string): string {
  return `
    <div class="stat-card">
      <div class="stat-label">${label}</div>
      <div class="stat-value">${value}</div>
      <div class="stat-sub">${sub}</div>
    </div>
  `;
}

function buildSpeedChart(data: { week: string; wpm: number; hours: number }[]): string {
  if (!data || data.length === 0) {
    return `<p style="color:var(--muted);font-size:0.875rem">No reading sessions recorded yet.</p>`;
  }
  const maxWpm = Math.max(...data.map((d) => d.wpm), 1);
  const bars = data
    .slice(-12) // last 12 weeks
    .map((d) => {
      const pct = Math.round((d.wpm / maxWpm) * 100);
      return `
      <div class="bar-row">
        <div class="bar-label">${d.week}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${pct}%"></div></div>
        <div class="bar-value">${d.wpm} wpm</div>
      </div>`;
    })
    .join("");
  return `<div class="bar-chart">${bars}</div>`;
}

function buildGenreChart(data: { genre: string; count: number; percentage: number }[]): string {
  if (!data || data.length === 0) {
    return `<p style="color:var(--muted);font-size:0.875rem">No genre data available yet.</p>`;
  }
  const bars = data
    .slice(0, 10)
    .map((d) => `
      <div class="bar-row">
        <div class="bar-label">${escapeHtml(d.genre)}</div>
        <div class="bar-track"><div class="bar-fill" style="width:${d.percentage}%"></div></div>
        <div class="bar-value">${d.percentage}%</div>
      </div>`)
    .join("");
  return `<div class="bar-chart">${bars}</div>`;
}

function buildSessionsTable(sessions: any[]): string {
  if (!sessions || sessions.length === 0) {
    return `<p style="color:var(--muted);font-size:0.875rem">No sessions recorded yet.</p>`;
  }
  const rows = sessions
    .map(
      (s) => `
      <tr>
        <td>${escapeHtml(s.book_title ?? "Unknown")}</td>
        <td>${s.started_at ? new Date(s.started_at).toLocaleDateString() : "—"}</td>
        <td>${s.duration_minutes} min</td>
        <td>${s.words_read.toLocaleString()}</td>
        <td>${s.wpm > 0 ? s.wpm + " wpm" : "—"}</td>
      </tr>`
    )
    .join("");

  return `
    <table class="sessions-table">
      <thead>
        <tr>
          <th>Book</th>
          <th>Date</th>
          <th>Duration</th>
          <th>Words</th>
          <th>WPM</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>`;
}

function escapeHtml(str: string): string {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
