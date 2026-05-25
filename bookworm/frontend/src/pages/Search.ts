import { search as searchApi, analytics as analyticsApi, type SearchResult, type ReadingProfile, ApiError } from "../api";
import { showToast } from "./toast";
import { navigate } from "../router";

export function renderSearch(): string {
  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Discover</h1>
        <p class="page-subtitle">Find your next read</p>
      </div>
    </div>

    <div style="display:flex;gap:0.75rem;margin-bottom:1.5rem">
      <input
        type="search"
        id="search-input"
        class="input"
        placeholder="Search for a book title or author…"
        style="flex:1"
      />
      <button class="btn btn-primary" id="search-btn">Search</button>
    </div>

    <div id="search-results"></div>

    <!-- Recommendations section (loaded async) -->
    <div id="recommendations-section"></div>
  `;
}

document.addEventListener("page:mounted", (e: Event) => {
  const route = (e as CustomEvent).detail;
  if (route?.name !== "search") return;

  const input = document.getElementById("search-input") as HTMLInputElement;
  const btn = document.getElementById("search-btn") as HTMLButtonElement;
  const results = document.getElementById("search-results")!;

  async function doSearch(): Promise<void> {
    const q = input.value.trim();
    if (!q) return;

    btn.disabled = true;
    btn.textContent = "Searching…";
    results.innerHTML = `<div class="loading-center"><div class="spinner"></div></div>`;

    try {
      const data = await searchApi.prowlarr(q);
      renderResults(data.results, results);
    } catch (err) {
      if (err instanceof ApiError && err.status === 502) {
        results.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-icon">🔌</div>
            <h3>Prowlarr not configured</h3>
            <p>Set your Prowlarr URL and API key in <a href="#/settings" style="color:var(--accent)">Settings</a>.</p>
          </div>`;
      } else {
        results.innerHTML = `<div class="form-error">${err instanceof Error ? err.message : "Search failed"}</div>`;
      }
    } finally {
      btn.disabled = false;
      btn.textContent = "Search";
    }
  }

  btn.addEventListener("click", doSearch);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") doSearch();
  });

  // Load recommendations
  loadRecommendations(input);
});

async function loadRecommendations(searchInput: HTMLInputElement): Promise<void> {
  const section = document.getElementById("recommendations-section");
  if (!section) return;

  try {
    const profile = await analyticsApi.profile();
    let html = "";

    // Genre suggestions as quick-search chips
    if (profile.search_suggestions.length > 0) {
      const chips = profile.search_suggestions
        .map((g) => `<button class="genre-chip" data-genre="${escapeHtml(g)}">${escapeHtml(g)}</button>`)
        .join("");
      html += `
        <div class="discover-section">
          <h3 class="discover-title">Your Top Genres</h3>
          <div class="genre-chips">${chips}</div>
        </div>`;
    }

    // Book recommendations from backlog
    if (profile.recommendations.length > 0) {
      const cards = profile.recommendations
        .map((r) => {
          const cover = r.cover_url
            ? `<img class="rec-cover" src="${r.cover_url}" alt="" />`
            : `<div class="rec-cover-placeholder">📖</div>`;
          return `
            <div class="rec-card" data-book-id="${r.book_id}">
              ${cover}
              <div class="rec-info">
                <div class="rec-title">${escapeHtml(r.title)}</div>
                <div class="rec-author">${escapeHtml(r.author ?? "Unknown")}</div>
                <div class="rec-reason">${escapeHtml(r.reason)}</div>
              </div>
            </div>`;
        })
        .join("");
      html += `
        <div class="discover-section">
          <h3 class="discover-title">Recommended from Your Library</h3>
          <div class="rec-grid">${cards}</div>
        </div>`;
    }

    // Reading profile summary
    if (profile.books_finished > 0) {
      html += `
        <div class="discover-section">
          <h3 class="discover-title">Your Reading Profile</h3>
          <div class="profile-stats">
            <div class="profile-stat"><span class="profile-stat-value">${profile.books_finished}</span> books finished</div>
            <div class="profile-stat"><span class="profile-stat-value">${profile.total_hours_read}h</span> total reading</div>
            ${profile.avg_days_per_book > 0 ? `<div class="profile-stat"><span class="profile-stat-value">${profile.avg_days_per_book}</span> days/book avg</div>` : ""}
          </div>
        </div>`;
    }

    if (html) {
      section.innerHTML = html;

      // Genre chip clicks trigger search
      section.querySelectorAll(".genre-chip").forEach((chip) => {
        chip.addEventListener("click", () => {
          searchInput.value = (chip as HTMLElement).dataset.genre ?? "";
          document.getElementById("search-btn")?.click();
        });
      });

      // Rec card clicks navigate to reader
      section.querySelectorAll(".rec-card[data-book-id]").forEach((card) => {
        card.addEventListener("click", () => {
          navigate(`/reader/${(card as HTMLElement).dataset.bookId}`);
        });
      });
    }
  } catch {
    // Profile endpoint not available or no data — silently skip
  }
}

function renderResults(items: SearchResult[], container: HTMLElement): void {
  if (!items || items.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🔍</div>
        <h3>No results found</h3>
        <p>Try a different search query.</p>
      </div>`;
    return;
  }

  const html = items
    .map((item) => {
      const size = item.size ? formatBytes(item.size) : "?";
      const seeders = item.seeders ?? 0;
      const seederColor = seeders > 5 ? "#50c878" : seeders > 0 ? "#ffa03c" : "var(--muted)";

      return `
      <div class="search-result-item">
        <div style="flex:1;min-width:0">
          <div class="search-result-title">${escapeHtml(item.title)}</div>
          <div class="search-result-meta">
            <span>📡 ${escapeHtml(item.indexer ?? "Unknown")}</span>
            <span>💾 ${size}</span>
            <span style="color:${seederColor}">↑ ${seeders} seeders</span>
            ${item.publish_date ? `<span>📅 ${new Date(item.publish_date).toLocaleDateString()}</span>` : ""}
          </div>
        </div>
        <button
          class="btn btn-primary btn-sm"
          data-guid="${escapeHtml(item.guid ?? "")}"
          data-indexer-id="${item.indexer_id ?? 0}"
        >
          Download
        </button>
      </div>`;
    })
    .join("");

  container.innerHTML = `<div class="search-results">${html}</div>`;

  container.querySelectorAll("[data-guid]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const guid = (btn as HTMLElement).dataset.guid!;
      const indexerId = parseInt((btn as HTMLElement).dataset.indexerId ?? "0");
      (btn as HTMLButtonElement).disabled = true;
      (btn as HTMLButtonElement).textContent = "Adding…";
      try {
        await searchApi.download(guid, indexerId);
        showToast("Added to download queue", "success");
        (btn as HTMLButtonElement).textContent = "Queued ✓";
      } catch (err) {
        showToast(err instanceof Error ? err.message : "Download failed", "error");
        (btn as HTMLButtonElement).disabled = false;
        (btn as HTMLButtonElement).textContent = "Download";
      }
    });
  });
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1073741824) return `${(bytes / 1048576).toFixed(1)} MB`;
  return `${(bytes / 1073741824).toFixed(2)} GB`;
}

function escapeHtml(str: string): string {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
