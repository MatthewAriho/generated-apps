import { search as searchApi, type SearchResult, ApiError } from "../api";
import { showToast } from "./toast";

export function renderSearch(): string {
  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Search</h1>
        <p class="page-subtitle">Find books via Prowlarr indexers</p>
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
});

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
