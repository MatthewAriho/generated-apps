/* CineQueue PWA — thin client, all logic in the API */
"use strict";

const API = "api";

// ── Tab navigation with caching ────────────────────────────────────────────
const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".panel");
let activeTab = "watch";
const tabLoaded = {};  // track which tabs have been loaded

tabs.forEach((t) => {
  t.addEventListener("click", () => {
    const id = t.dataset.tab;
    if (id === activeTab) return;
    activeTab = id;
    tabs.forEach((b) => b.classList.toggle("active", b.dataset.tab === id));
    panels.forEach((p) =>
      p.classList.toggle("active", p.id === `panel-${id}`)
    );
    if (!tabLoaded[id]) loadTab(id);
  });
});

function loadTab(id) {
  const loaders = { watch: loadWatch, suggest: loadSuggest, stats: loadStats,
                    downloads: loadDownloads, settings: loadSettings };
  if (loaders[id]) loaders[id]();
}

function invalidateTab(id) { tabLoaded[id] = false; }

// ── Helpers ─────────────────────────────────────────────────────────────────
async function api(path, opts) {
  const r = await fetch(`${API}/${path}`, opts);
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: r.statusText }));
    throw new Error(e.detail || r.statusText);
  }
  return r.json();
}

function posterSrc(movie) {
  const url = movie.poster_url;
  if (!url) return "";
  return `${API}/poster?url=${encodeURIComponent(url)}`;
}

function badge(movie) {
  if (movie.on_plex && movie.on_lb)
    return `<span class="card-badge badge-both">Plex + LB</span>`;
  if (movie.on_plex || movie.source === "plex")
    return `<span class="card-badge badge-plex">Plex</span>`;
  if (movie.on_lb || movie.source === "letterboxd")
    return `<span class="card-badge badge-lb">Letterboxd</span>`;
  return "";
}

function h(tag, cls, inner) {
  return `<${tag} class="${cls}">${inner}</${tag}>`;
}

function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

// ── Movie detail modal ─────────────────────────────────────────────────────
// Flat cache array used by modal — populated by renderMovieGrid
let _movieDetailCache = [];

window.showMovieDetail = function (cacheIdx) {
  const m = _movieDetailCache[cacheIdx];
  if (!m) return;

  const src = posterSrc(m);
  const onPlex = m.source === "plex" || m.on_plex;
  const imgTag = src
    ? `<img src="${src}" alt="${esc(m.title)}" class="detail-poster">`
    : `<div class="detail-poster detail-poster-empty">?</div>`;

  const rating = m.rating ? `<span class="detail-chip">${m.rating}/10</span>` : "";
  const runtime = m.runtime ? `<span class="detail-chip">${Math.floor(m.runtime/60)}h ${m.runtime%60}m</span>` : "";
  const country = m.country ? `<span class="detail-chip">${m.country}</span>` : "";

  // Stash movie JSON in a data attribute to avoid inline quoting issues
  const modal = document.getElementById("movie-modal");
  modal._movie = m;

  let dlBtn = "";
  if (!onPlex) {
    dlBtn = `<button class="btn btn-accent btn-block mt-8" onclick="queueFromDetail()">Queue Download</button>`;
  }

  modal.innerHTML = `
    <div class="modal-backdrop" onclick="closeModal()"></div>
    <div class="modal-sheet">
      <div class="modal-handle"></div>
      <div class="modal-body">
        <div class="detail-header">
          ${imgTag}
          <div class="detail-header-info">
            <div class="modal-title">${esc(m.title)}</div>
            <div class="detail-year">${m.year || ""}</div>
            <div class="detail-chips">
              ${rating}${runtime}${country}
            </div>
            <div class="detail-genre">${m.genre || ""}</div>
            ${badge(m)}
            <div class="modal-avail ${onPlex ? 'text-green' : 'text-gold'}">&bull; ${onPlex ? 'Available on Plex' : 'Not on Plex'}</div>
          </div>
        </div>
        ${m.director ? `<div class="detail-director">Directed by <strong>${esc(m.director)}</strong></div>` : ""}
        ${m.overview ? `<div class="modal-overview">${esc(m.overview)}</div>` : ""}
        ${dlBtn}
      </div>
    </div>`;
  modal.classList.add("open");
};

window.closeModal = function () {
  document.getElementById("movie-modal").classList.remove("open");
};

window.queueFromDetail = async function () {
  const m = document.getElementById("movie-modal")._movie;
  if (!m) return;
  try {
    await api("downloads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: m.title, year: m.year || "", genre: m.genre || "",
        director: m.director || "", poster_url: m.poster_url || "",
        source: m.source || "",
      }),
    });
    closeModal();
    invalidateTab("downloads");
  } catch (_) {}
};

// ── Watch tab ──────────────────────────────────────────────────────────────
let watchSort = "random";
let watchCount = 3;
let _watchPlexCache = [];
let _watchRecommendCache = [];

async function loadWatch() {
  const panel = document.getElementById("panel-watch");
  panel.innerHTML = `<div class="empty-state">Loading...</div>`;

  try {
    const [plexData, recData] = await Promise.all([
      api(`movies/watch?count=${watchCount}&sort=${watchSort}&source=plex`),
      api(`movies/watch?count=${watchCount}&sort=${watchSort}&source=all`),
    ]);
    _watchPlexCache = plexData.movies;
    _watchRecommendCache = recData.movies;
    renderWatch();
    tabLoaded.watch = true;
  } catch (e) {
    panel.innerHTML = h("div", "empty-state", `Error: ${e.message}`);
  }
}

function renderWatch() {
  const panel = document.getElementById("panel-watch");
  const sorts = ["random", "plex_date", "lb_date", "foreign", "runtime"];
  const sortLabels = { random: "Shuffle", plex_date: "Newest", lb_date: "LB Date",
                       foreign: "Foreign", runtime: "Runtime" };

  _movieDetailCache = [];
  let html = "";

  // Sort chips + count in a compact header
  html += `<div class="watch-header">
    <div class="filter-row">`;
  for (const s of sorts) {
    const cls = s === watchSort ? "chip active" : "chip";
    html += `<button class="${cls}" onclick="setSort('${s}')">${sortLabels[s]}</button>`;
  }
  html += `</div>
    <div class="count-row">
      <button class="count-btn" onclick="changeCount(-1)">&minus;</button>
      <span class="count-val" id="count-val">${watchCount}</span>
      <button class="count-btn" onclick="changeCount(1)">+</button>
    </div>
  </div>`;

  // Plex section
  if (_watchPlexCache.length) {
    html += h("div", "section-label", `On Plex <span class="section-count">${_watchPlexCache.length}</span>`);
    html += renderMovieStrip(_watchPlexCache);
  } else {
    html += h("div", "empty-state", "No Plex movies. Sync in Settings.");
  }

  // Recommended section
  if (_watchRecommendCache.length) {
    html += h("div", "section-label mt-12", `Recommended <span class="section-count">${_watchRecommendCache.length}</span>`);
    html += renderMovieStrip(_watchRecommendCache);
  }

  panel.innerHTML = html;
}

function renderMovieGrid(movies) {
  let html = `<div class="movie-grid">`;
  for (const m of movies) {
    const ci = _movieDetailCache.length;
    _movieDetailCache.push(m);
    html += renderCard(m, ci);
  }
  html += `</div>`;
  return html;
}

function renderMovieStrip(movies) {
  let html = `<div class="movie-strip">`;
  for (const m of movies) {
    const ci = _movieDetailCache.length;
    _movieDetailCache.push(m);
    html += renderCard(m, ci);
  }
  html += `</div>`;
  return html;
}

function renderCard(m, cacheIdx) {
  const src = posterSrc(m);
  const imgTag = src
    ? `<img src="${src}" alt="${esc(m.title)}" loading="lazy">`
    : `<div class="card-placeholder">${esc(m.title?.charAt(0) || "?")}</div>`;
  return `<div class="movie-card" onclick="showMovieDetail(${cacheIdx})">
    ${imgTag}
    <div class="card-info">
      <div class="card-title" title="${esc(m.title)}">${esc(m.title)}</div>
      <div class="card-meta">${m.year || "?"} &middot; ${m.runtime || "?"}m</div>
      ${badge(m)}
    </div>
  </div>`;
}

window.changeCount = function (d) {
  watchCount = Math.max(1, Math.min(10, watchCount + d));
  const el = document.getElementById("count-val");
  if (el) el.textContent = watchCount;
  tabLoaded.watch = false;
  loadWatch();
};

window.setSort = function (s) {
  watchSort = s;
  tabLoaded.watch = false;
  loadWatch();
};

// ── Suggest (swipe) tab ────────────────────────────────────────────────────
let suggestIdx = 0;
let suggestMovies = [];

async function loadSuggest() {
  const panel = document.getElementById("panel-suggest");
  panel.innerHTML = `<div class="empty-state">Loading...</div>`;

  try {
    const data = await api("movies");
    suggestMovies = [...data.plex, ...data.letterboxd].filter(
      (m) => m.title && m.runtime > 0
    );
    suggestIdx = 0;
    renderSuggestCard();
    tabLoaded.suggest = true;
  } catch (e) {
    panel.innerHTML = h("div", "empty-state", e.message);
  }
}

function renderSuggestCard() {
  const panel = document.getElementById("panel-suggest");
  if (!suggestMovies.length) {
    panel.innerHTML = h("div", "empty-state", "No movies available.");
    return;
  }
  if (suggestIdx >= suggestMovies.length) {
    panel.innerHTML = h("div", "empty-state", "No more movies! Refresh to start over.");
    return;
  }

  const m = suggestMovies[suggestIdx];
  const src = posterSrc(m);
  const onPlex = m.source === "plex" || m.on_plex;
  const availText = onPlex ? "On Plex" : "Not on Plex";
  const availClass = onPlex ? "text-green" : "text-gold";

  let dlBtn = "";
  if (!onPlex) {
    dlBtn = `<button class="btn btn-primary mt-8" style="font-size:12px" onclick="queueFromSuggest(${suggestIdx})">Queue Download</button>`;
  }

  const imgTag = src
    ? `<img src="${src}" alt="${esc(m.title)}">`
    : `<div class="swipe-placeholder">?</div>`;

  const overview = m.overview
    ? `<div class="swipe-overview">${esc(m.overview).substring(0, 150)}${m.overview.length > 150 ? "..." : ""}</div>`
    : "";

  const ratingStr = m.rating ? `${m.rating}/10` : "";

  panel.innerHTML = `
    <div class="swipe-container">
      <div class="swipe-card" id="swipe-card">
        ${imgTag}
        <div class="swipe-info">
          <div class="swipe-title">${esc(m.title)}</div>
          <div class="swipe-chips">
            ${m.year ? `<span class="detail-chip">${m.year}</span>` : ""}
            ${m.runtime ? `<span class="detail-chip">${m.runtime}m</span>` : ""}
            ${m.genre ? `<span class="detail-chip">${m.genre}</span>` : ""}
            ${ratingStr ? `<span class="detail-chip">${ratingStr}</span>` : ""}
          </div>
          ${m.director ? `<div class="swipe-director">Dir: ${esc(m.director)}</div>` : ""}
          <div class="swipe-avail ${availClass}">&bull; ${availText}</div>
          ${overview}
          ${dlBtn}
        </div>
      </div>
      <div class="swipe-buttons">
        <button class="swipe-btn skip" onclick="swipeAction('skip')" title="Skip">&laquo;</button>
        <button class="swipe-btn nope" onclick="swipeAction('nope')" title="Not interested">&darr;</button>
        <button class="swipe-btn accept" onclick="swipeAction('accept')" title="Watch">&check;</button>
      </div>
      <div class="swipe-toast" id="swipe-toast"></div>
    </div>`;

  // Touch/swipe handling
  const card = document.getElementById("swipe-card");
  let startX = 0, startY = 0, dx = 0, dy = 0, swiping = false;

  card.addEventListener("touchstart", (e) => {
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
    swiping = true;
    card.style.transition = "none";
  });

  card.addEventListener("touchmove", (e) => {
    if (!swiping) return;
    dx = e.touches[0].clientX - startX;
    dy = e.touches[0].clientY - startY;
    card.style.transform = `translate(${dx}px, ${Math.max(0, dy)}px) rotate(${dx * 0.05}deg)`;
  });

  card.addEventListener("touchend", () => {
    if (!swiping) return;
    swiping = false;
    card.style.transition = "transform 0.3s";
    if (Math.abs(dx) > 80) {
      swipeAction(dx > 0 ? "accept" : "skip");
    } else if (dy > 80) {
      swipeAction("nope");
    } else {
      card.style.transform = "";
    }
    dx = 0;
    dy = 0;
  });
}

window.swipeAction = function (action) {
  const card = document.getElementById("swipe-card");
  const toast = document.getElementById("swipe-toast");
  if (!card) return;

  card.style.transition = "transform 0.3s, opacity 0.3s";
  if (action === "accept") {
    card.style.transform = "translateX(120vw)";
    card.style.opacity = "0";
    if (toast) { toast.textContent = `Added '${suggestMovies[suggestIdx]?.title}' to watch list!`; toast.style.opacity = "1"; }
  } else if (action === "skip") {
    card.style.transform = "translateX(-120vw)";
    card.style.opacity = "0";
  } else {
    card.style.transform = "translateY(120vh)";
    card.style.opacity = "0";
  }

  setTimeout(() => {
    suggestIdx++;
    renderSuggestCard();
    if (toast) setTimeout(() => { toast.style.opacity = "0"; }, 1500);
  }, 300);
};

window.queueFromSuggest = async function (idx) {
  const m = suggestMovies[idx];
  if (!m) return;
  try {
    await api("downloads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: m.title, year: m.year || "", genre: m.genre || "",
        director: m.director || "", poster_url: m.poster_url || "",
        source: m.source || "",
      }),
    });
    const btn = document.querySelector("#panel-suggest .btn-primary");
    if (btn) { btn.textContent = "Queued"; btn.disabled = true; btn.style.opacity = "0.5"; }
  } catch (e) {
    const btn = document.querySelector("#panel-suggest .btn-primary");
    if (btn) btn.textContent = e.message.includes("409") ? "Already queued" : "Error";
  }
};

// ── Stats tab ──────────────────────────────────────────────────────────────
async function loadStats() {
  const panel = document.getElementById("panel-stats");
  panel.innerHTML = `<div class="empty-state">Loading...</div>`;

  try {
    const d = await api("analytics");
    let html = "";

    // Summary cards
    const s = d.summary;
    html += `<div class="stat-grid">
      <div class="stat-card"><div class="stat-val text-green">${s.lb_total_watched ?? "?"}</div><div class="stat-label">LB Watched</div></div>
      <div class="stat-card"><div class="stat-val text-blue">${s.lb_watched_this_year ?? "?"}</div><div class="stat-label">This Year</div></div>
      <div class="stat-card"><div class="stat-val text-blue">${s.plex_count}</div><div class="stat-label">On Plex</div></div>
      <div class="stat-card"><div class="stat-val text-gold">${s.on_both}</div><div class="stat-label">Plex + LB</div></div>
    </div>`;

    // This year
    const ty = d.this_year;
    html += h("div", "section-title", `This Year (${ty.year})`);
    html += `<div class="stat-grid">
      <div class="stat-card"><div class="stat-val text-blue">${ty.from_watchlist}</div><div class="stat-label">Watched from<br>Watchlist</div></div>
      <div class="stat-card"><div class="stat-val text-gold">${ty.added_to_watchlist}</div><div class="stat-label">Added to<br>Watchlist</div></div>
    </div>`;

    // Progress bars
    html += h("div", "section-title", "Watch Progress");
    const bars = [
      ["Letterboxd", d.progress.letterboxd_pct, "var(--accent2)"],
      ["Plex", d.progress.plex_pct, "var(--green)"],
      ["Aggregated", d.progress.aggregated_pct, "var(--gold)"],
    ];
    for (const [label, pct, color] of bars) {
      html += `<div class="progress-row">
        <div class="progress-label">${label} (${pct}%)</div>
        <div class="progress-bar"><div class="progress-fill" style="width:${pct}%;background:${color}"></div></div>
      </div>`;
    }
    html += `<div style="font-size:11px;color:var(--gold);margin-bottom:12px">&bull; ${d.progress.overlap} titles on both Plex and Letterboxd</div>`;

    // Genres
    html += h("div", "section-title", "Genre Breakdown");
    for (const [genre, cnt] of d.genres) {
      html += `<div class="breakdown-row"><span class="label">${genre}</span><span class="value">${cnt}</span></div>`;
    }

    // Countries
    html += h("div", "section-title", "Country Breakdown");
    for (const [country, cnt] of d.countries) {
      html += `<div class="breakdown-row"><span class="label">${country}</span><span class="value">${cnt}</span></div>`;
    }

    // Watch days
    html += h("div", "section-title", "Most Active Watch Days");
    for (const [day, cnt] of d.watch_days) {
      html += `<div class="breakdown-row"><span class="label">${day}</span><span class="value">${cnt}</span></div>`;
    }

    // Averages
    html += `<div class="mt-16">
      <div style="font-size:13px;color:var(--gold)">Avg Rating: ${d.avg_rating} / 10</div>
      <div style="font-size:13px;color:var(--accent2);margin-top:4px">Avg Runtime: ${d.avg_runtime} min (${Math.floor(d.avg_runtime/60)}h ${d.avg_runtime%60}m)</div>
    </div>`;

    panel.innerHTML = html;
    tabLoaded.stats = true;
  } catch (e) {
    panel.innerHTML = h("div", "empty-state", e.message);
  }
}

// ── Downloads tab ──────────────────────────────────────────────────────────
const DL_STATUS_COLOR = {
  queued: "text-sub", searching: "text-gold", results_found: "text-blue",
  no_results: "text-red", grabbing: "text-gold", downloading: "text-blue",
  complete: "text-green", failed: "text-red",
};
const DL_STATUS_LABEL = {
  queued: "Queued", searching: "Searching...", results_found: "Release found",
  no_results: "No releases", grabbing: "Sending to qBit...",
  downloading: "Downloading", complete: "Complete", failed: "Failed",
};

let dlPollTimer = null;

async function loadDownloads() {
  const panel = document.getElementById("panel-downloads");
  panel.innerHTML = `<div class="empty-state">Loading...</div>`;

  try {
    const data = await api("downloads");
    renderDownloads(data.queue);
    tabLoaded.downloads = true;
    if (dlPollTimer) clearInterval(dlPollTimer);
    dlPollTimer = setInterval(pollAndRefreshDl, 30000);
  } catch (e) {
    panel.innerHTML = h("div", "empty-state", e.message);
  }
}

function renderDownloads(queue) {
  const panel = document.getElementById("panel-downloads");
  let html = "";

  if (!queue.length) {
    html += h("div", "empty-state", "No downloads queued.<br>Queue movies from Suggest or tap a movie card.");
    panel.innerHTML = html;
    return;
  }

  html += `<div class="dl-list">`;
  for (const e of queue) {
    const src = e.poster_url ? `${API}/poster?url=${encodeURIComponent(e.poster_url)}` : "";
    const imgTag = src ? `<img class="dl-poster" src="${src}">` : `<div class="dl-poster"></div>`;
    const statusCls = DL_STATUS_COLOR[e.status] || "text-sub";
    const statusLbl = DL_STATUS_LABEL[e.status] || e.status;
    const pct = Math.round((e.progress || 0) * 100);
    const errMsg = e.error ? `<div style="font-size:11px;color:var(--accent);margin-top:2px">${esc(e.error)}</div>` : "";
    const progBar = e.status === "downloading"
      ? `<div class="dl-progress"><div class="dl-progress-fill" style="width:${pct}%"></div></div>`
      : "";

    html += `<div class="dl-entry">
      ${imgTag}
      <div class="dl-info">
        <div class="dl-title">${esc(e.title)}</div>
        <div class="dl-status ${statusCls}">&bull; ${statusLbl}${pct > 0 && e.status === "downloading" ? ` (${pct}%)` : ""}</div>
        ${errMsg}
        ${progBar}
      </div>
      <button class="dl-remove" onclick="removeDl('${e.id}')" title="Remove">&times;</button>
    </div>`;
  }
  html += `</div>`;
  panel.innerHTML = html;
}

window.removeDl = async function (id) {
  try {
    await api(`downloads/${id}`, { method: "DELETE" });
    loadDownloads();
  } catch (e) {
    alert(e.message);
  }
};

async function pollAndRefreshDl() {
  if (activeTab !== "downloads") return;
  try {
    await api("downloads/poll", { method: "POST" });
    const data = await api("downloads");
    renderDownloads(data.queue);
  } catch (_) {}
}

// ── Settings tab ───────────────────────────────────────────────────────────
const SETTINGS_SECTIONS = [
  { title: "Plex Server", fields: [
    { key: "plex_url", label: "Plex Server URL", placeholder: "http://localhost:32400" },
    { key: "plex_token", label: "Plex Token", placeholder: "xxxxxxxxxxxxxxxx", password: true },
  ]},
  { title: "Letterboxd", fields: [
    { key: "lb_username", label: "Username", placeholder: "@yourusername" },
  ]},
  { title: "Synology NAS", fields: [
    { key: "dsm_port", label: "DSM Port", placeholder: "5000" },
    { key: "dsm_username", label: "NAS Username", placeholder: "admin" },
    { key: "dsm_password", label: "NAS Password", placeholder: "password", password: true },
    { key: "qbit_project", label: "VPN+qBit Project", placeholder: "qbittorrent-gluetun" },
    { key: "arr_project", label: "Arr Stack Project", placeholder: "arr-apps" },
  ]},
  { title: "Radarr", fields: [
    { key: "radarr_url", label: "Radarr URL", placeholder: "http://localhost:7878" },
    { key: "radarr_api_key", label: "API Key", placeholder: "your-api-key", password: true },
  ]},
  { title: "qBittorrent", fields: [
    { key: "qbit_url", label: "Web UI URL", placeholder: "http://localhost:8080" },
    { key: "qbit_username", label: "Username", placeholder: "admin" },
    { key: "qbit_password", label: "Password", placeholder: "adminadmin", password: true },
  ]},
  { title: "TMDB", fields: [
    { key: "tmdb_key", label: "API Key", placeholder: "Get free key at themoviedb.org", password: true },
  ]},
];

const LS_SETTINGS_KEY = "cinequeue_settings";

function getLocalSettings() {
  try { return JSON.parse(localStorage.getItem(LS_SETTINGS_KEY)) || {}; } catch (_) { return {}; }
}

function setLocalSettings(data) {
  const prev = getLocalSettings();
  for (const [k, v] of Object.entries(data)) {
    if (v && v !== "***") prev[k] = v;
  }
  localStorage.setItem(LS_SETTINGS_KEY, JSON.stringify(prev));
}

function populateSettingsForm(data) {
  for (const section of SETTINGS_SECTIONS) {
    for (const f of section.fields) {
      const el = document.getElementById(`set-${f.key}`);
      if (el && data[f.key] && data[f.key] !== "***") {
        el.value = data[f.key];
      }
    }
  }
}

async function loadSettings() {
  const panel = document.getElementById("panel-settings");
  let html = `<div class="settings-status" id="settings-status"></div>`;

  for (const section of SETTINGS_SECTIONS) {
    html += `<div class="settings-section">`;
    html += h("div", "section-title", section.title);
    for (const f of section.fields) {
      const type = f.password ? "password" : "text";
      html += `<div class="field-group">
        <div class="field-label">${f.label}</div>
        <input class="field-input" type="${type}" id="set-${f.key}"
               placeholder="${f.placeholder}" data-key="${f.key}">
      </div>`;
    }
    html += `</div>`;
  }

  html += `<div class="btn-row">`;
  html += `<button class="btn btn-primary flex-1" onclick="saveSettings()">Save</button>`;
  html += `<button class="btn btn-outline flex-1" onclick="pullSettings()">Pull from Server</button>`;
  html += `</div>`;

  // Service control
  html += h("div", "section-title", "Service Control");
  html += `<div id="svc-panel">
    <div class="svc-row"><span class="svc-name">Plex Media Server</span><span class="svc-status text-sub" id="svc-plex">&bull; unknown</span>
      <button class="svc-btn text-green" onclick="svcAction('plex','start')">&#9654;</button>
      <button class="svc-btn text-red" onclick="svcAction('plex','stop')">&#9632;</button></div>
    <div class="svc-row"><span class="svc-name">VPN + qBittorrent</span><span class="svc-status text-sub" id="svc-qbit_proj">&bull; unknown</span>
      <button class="svc-btn text-green" onclick="svcAction('qbit_proj','start')">&#9654;</button>
      <button class="svc-btn text-red" onclick="svcAction('qbit_proj','stop')">&#9632;</button></div>
    <div class="svc-row"><span class="svc-name">Prowlarr / Sonarr / Radarr</span><span class="svc-status text-sub" id="svc-arr_proj">&bull; unknown</span>
      <button class="svc-btn text-green" onclick="svcAction('arr_proj','start')">&#9654;</button>
      <button class="svc-btn text-red" onclick="svcAction('arr_proj','stop')">&#9632;</button></div>
  </div>`;
  html += `<button class="btn btn-outline btn-block mt-8" onclick="refreshServices()">Refresh All</button>`;

  // Server logs toggle
  html += `<button class="btn btn-outline btn-block mt-8" onclick="toggleDebugConsole()">Server Logs</button>`;
  html += `<div id="debug-console" class="debug-console" style="display:none">
    <div class="debug-toolbar">
      <button class="debug-tb-btn" onclick="fetchServerLogs()">Refresh</button>
      <button class="debug-tb-btn" onclick="document.getElementById('debug-entries').innerHTML=''">Clear</button>
      <select id="debug-filter" class="debug-tb-btn" onchange="fetchServerLogs()">
        <option value="">All</option>
        <option value="error">Errors</option>
        <option value="warn">Warnings</option>
        <option value="info">Info</option>
        <option value="debug">Debug</option>
      </select>
    </div>
    <div id="debug-entries" class="debug-entries"></div>
  </div>`;

  // Sync
  html += h("div", "section-title mt-12", "Data Sync");
  html += `<button class="btn btn-outline btn-block" onclick="triggerSync()">Sync Plex + Letterboxd</button>`;

  panel.innerHTML = html;
  tabLoaded.settings = true;

  // Populate from localStorage
  const local = getLocalSettings();
  populateSettingsForm(local);

  // First boot: auto-pull
  if (!Object.keys(local).length) {
    await pullSettings();
  }
}

window.saveSettings = async function () {
  const body = {};
  document.querySelectorAll(".field-input").forEach((el) => {
    const key = el.dataset.key;
    const val = el.value.trim();
    if (val && val !== "***") body[key] = val;
  });
  const status = document.getElementById("settings-status");
  try {
    await api("settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setLocalSettings(body);
    status.textContent = "Saved!";
    status.style.color = "var(--green)";
    // Invalidate data tabs since settings changed
    invalidateTab("watch");
    invalidateTab("suggest");
    invalidateTab("stats");
  } catch (e) {
    status.textContent = `Error: ${e.message}`;
    status.style.color = "var(--accent)";
  }
};

window.pullSettings = async function () {
  const status = document.getElementById("settings-status");
  try {
    if (status) { status.textContent = "Pulling..."; status.style.color = "var(--gold)"; }
    const data = await api("settings");
    setLocalSettings(data);
    populateSettingsForm(getLocalSettings());
    if (status) { status.textContent = "Pulled from server"; status.style.color = "var(--green)"; }
  } catch (e) {
    if (status) { status.textContent = `Pull failed: ${e.message}`; status.style.color = "var(--accent)"; }
  }
};

window.toggleDebugConsole = function () {
  const el = document.getElementById("debug-console");
  if (!el) return;
  const open = el.style.display !== "none";
  el.style.display = open ? "none" : "block";
  if (!open) fetchServerLogs();
};

window.fetchServerLogs = async function () {
  const entries = document.getElementById("debug-entries");
  if (!entries) return;
  const filter = document.getElementById("debug-filter")?.value || "";
  try {
    const data = await api("logs?limit=100");
    const filtered = filter ? data.filter(l => l.level === filter) : data;
    entries.innerHTML = filtered.map(l => {
      const cls = l.level === "error" ? "log-error" : l.level === "warn" ? "log-warn" : l.level === "debug" ? "log-debug" : "log-info";
      const detail = l.detail ? `<pre class="log-detail">${esc(l.detail)}</pre>` : "";
      return `<div class="log-entry ${cls}">
        <span class="log-ts">${l.ts}</span>
        <span class="log-level">${l.level.toUpperCase()}</span>
        <span class="log-src">${esc(l.source)}</span>
        <span class="log-msg">${esc(l.message)}</span>
        ${detail}
      </div>`;
    }).join("") || `<div class="log-entry log-info">No logs${filter ? ` matching "${filter}"` : ""}</div>`;
  } catch (e) {
    entries.innerHTML = `<div class="log-entry log-error">Failed to fetch logs: ${esc(e.message)}</div>`;
  }
};

window.refreshServices = async function () {
  for (const id of ["svc-plex", "svc-qbit_proj", "svc-arr_proj"]) {
    const el = document.getElementById(id);
    if (el) { el.textContent = "\u2022 checking..."; el.className = "svc-status text-gold"; }
  }
  try {
    const data = await api("services/status");
    for (const [key, status] of Object.entries(data)) {
      const el = document.getElementById(`svc-${key}`);
      if (!el) continue;
      const isUp = status === "running";
      el.textContent = `\u2022 ${status}`;
      el.className = `svc-status ${isUp ? "text-green" : "text-sub"}`;
    }
  } catch (e) {
    const status = document.getElementById("settings-status");
    if (status) { status.textContent = e.message; status.style.color = "var(--accent)"; }
  }
};

window.svcAction = async function (service, action) {
  const el = document.getElementById(`svc-${service}`);
  if (el) { el.textContent = `\u2022 ${action}ing...`; el.className = "svc-status text-gold"; }
  try {
    const r = await api("services/action", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ service, action }),
    });
    if (r.success) {
      if (el) {
        el.textContent = action === "start" ? "\u2022 running" : "\u2022 stopped";
        el.className = `svc-status ${action === "start" ? "text-green" : "text-sub"}`;
      }
    } else {
      if (el) { el.textContent = `\u2022 error ${r.error_code || ""}`; el.className = "svc-status text-red"; }
    }
  } catch (e) {
    if (el) { el.textContent = "\u2022 error"; el.className = "svc-status text-red"; }
  }
};

window.triggerSync = async function () {
  const status = document.getElementById("settings-status");
  try {
    await api("sync", { method: "POST" });
    if (status) { status.textContent = "Sync started..."; status.style.color = "var(--accent2)"; }
    // Invalidate data tabs
    invalidateTab("watch");
    invalidateTab("suggest");
    invalidateTab("stats");
  } catch (e) {
    if (status) { status.textContent = e.message; status.style.color = "var(--accent)"; }
  }
};

// ── PWA install prompt ─────────────────────────────────────────────────────
let _deferredInstallPrompt = null;

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  _deferredInstallPrompt = e;
  showInstallBanner();
});

function showInstallBanner() {
  if (document.getElementById("install-banner")) return;
  const banner = document.createElement("div");
  banner.id = "install-banner";
  banner.innerHTML = `
    <span>Install CineQueue</span>
    <button id="install-btn" class="btn btn-primary" style="padding:6px 16px;font-size:12px">Install</button>
    <button class="btn btn-outline" style="padding:6px 10px;font-size:12px" onclick="this.parentElement.remove()">Later</button>`;
  document.body.appendChild(banner);
  document.getElementById("install-btn").addEventListener("click", async () => {
    if (!_deferredInstallPrompt) return;
    _deferredInstallPrompt.prompt();
    await _deferredInstallPrompt.userChoice;
    _deferredInstallPrompt = null;
    banner.remove();
  });
}

// ── Init ────────────────────────────────────────────────────────────────────
loadTab("watch");
