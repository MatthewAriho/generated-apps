import ePub from "epubjs";
import type { Book } from "../api";
import { progress as progressApi } from "../api";

interface ReaderMargins { top: number; bottom: number; left: number; right: number; }

interface ReaderPrefs {
  theme: "light" | "sepia" | "dark";
  fontSize: number;
  margins: ReaderMargins;
}

interface Annotation {
  cfi: string;
  color: string;
  text: string;   // selected text
  note: string;   // user's comment
}

interface EpubReaderState {
  book: any;
  rendition: any;
  currentCfi: string;
  lastLocationEvent: any;
  sessionStart: Date;
  saveTimer: ReturnType<typeof setInterval> | null;
  uiTimer: ReturnType<typeof setTimeout> | null;
  prefs: ReaderPrefs;
  annotations: Annotation[];
  pendingCfi: string | null;
  pendingColor: string | null;
  pendingText: string;
  bookId: number;
  totalPages: number;
  locationsReady: boolean;
  uiVisible: boolean;
}

const DEFAULT_MARGINS: ReaderMargins = { top: 8, bottom: 8, left: 24, right: 24 };
const UI_HIDE_DELAY = 3000;

const THEMES = {
  light: { bg: "#ffffff", fg: "#2c2c2c", containerBg: "#e8e4df" },
  sepia: { bg: "#f4ecd8", fg: "#4a3728", containerBg: "#ddd0b8" },
  dark:  { bg: "#1c1c1e", fg: "#d4d4d4", containerBg: "#111111" },
};

const ANN_COLORS: Record<string, string> = {
  yellow: "rgba(255,210,0,0.45)",
  green:  "rgba(80,200,120,0.4)",
  blue:   "rgba(100,180,240,0.4)",
  pink:   "rgba(255,100,150,0.4)",
};

const ANN_BORDER: Record<string, string> = {
  yellow: "#ffd200", green: "#50c878", blue: "#64b4f0", pink: "#ff6496",
};

const state: EpubReaderState = {
  book: null, rendition: null, currentCfi: "", lastLocationEvent: null,
  sessionStart: new Date(), saveTimer: null, uiTimer: null,
  prefs: { theme: "light", fontSize: 100, margins: { ...DEFAULT_MARGINS } },
  annotations: [], pendingCfi: null, pendingColor: null, pendingText: "",
  bookId: 0, totalPages: 0, locationsReady: false, uiVisible: true,
};

// ─── HTML ────────────────────────────────────────────────────────────────────

export function renderEpubReader(_bookData: Book): string {
  return `
    <div class="epub-container" id="epub-viewer"></div>

    <div class="reader-controls" id="reader-controls">
      <button class="reader-ctrl-btn" id="epub-prev-btn">&#8592;</button>
      <button class="reader-ctrl-btn" id="toc-btn" title="Contents">&#9776;</button>
      <div class="reader-page-info">
        <div class="epub-progress-row">
          <input class="epub-page-input" id="epub-pct-input" type="text" value="0%" title="Jump to %" />
          <span class="epub-page-sep">·</span>
          <input class="epub-page-input" id="epub-page-input" type="text" value="—" title="Jump to page" />
          <span class="epub-page-total" id="epub-page-total"></span>
        </div>
      </div>
      <button class="reader-ctrl-btn" id="ann-list-btn" title="Highlights &amp; Notes">&#128203;</button>
      <button class="reader-ctrl-btn" id="settings-btn" title="Settings">&#9881;</button>
      <button class="reader-ctrl-btn" id="epub-next-btn">&#8594;</button>
    </div>

    <!-- TOC Panel -->
    <div class="reader-toc-panel" id="toc-panel">
      <div class="reader-toc-header"><span>Contents</span><button id="toc-close">&#10005;</button></div>
      <div class="reader-toc-list" id="toc-list"></div>
    </div>
    <div class="reader-overlay" id="reader-overlay"></div>

    <!-- Settings Sheet -->
    <div class="reader-settings-sheet" id="settings-sheet">
      <div class="settings-handle"></div>
      <div class="settings-row">
        <span class="settings-label">Theme</span>
        <div class="theme-btns">
          <button class="theme-btn" data-theme="light">Light</button>
          <button class="theme-btn" data-theme="sepia">Sepia</button>
          <button class="theme-btn" data-theme="dark">Dark</button>
        </div>
      </div>
      <div class="settings-row">
        <span class="settings-label">Font size</span>
        <div class="settings-stepper">
          <button id="font-down">A&#8722;</button>
          <span id="font-size-label">100%</span>
          <button id="font-up">A+</button>
        </div>
      </div>
      <div class="settings-row settings-row-margins">
        <span class="settings-label">Margins (px)</span>
        <div class="margin-grid">
          <label>Top<input class="margin-input" id="margin-top" type="number" min="0" max="80" value="8" /></label>
          <label>Bottom<input class="margin-input" id="margin-bottom" type="number" min="0" max="80" value="8" /></label>
          <label>Left<input class="margin-input" id="margin-left" type="number" min="0" max="120" value="24" /></label>
          <label>Right<input class="margin-input" id="margin-right" type="number" min="0" max="120" value="24" /></label>
        </div>
      </div>
    </div>

    <!-- Highlight Colour Picker -->
    <div class="annotation-picker" id="annotation-picker">
      <span class="ann-picker-label">Highlight</span>
      <button class="ann-color-btn" data-color="yellow" style="background:#ffd200"></button>
      <button class="ann-color-btn" data-color="green"  style="background:#50c878"></button>
      <button class="ann-color-btn" data-color="blue"   style="background:#64b4f0"></button>
      <button class="ann-color-btn" data-color="pink"   style="background:#ff6496"></button>
      <button class="ann-remove-btn" id="ann-remove" title="Remove">&#10005;</button>
    </div>

    <!-- Note Sheet (after picking colour) -->
    <div class="ann-comment-sheet" id="ann-comment-sheet">
      <div class="settings-handle"></div>
      <div class="ann-comment-selected" id="ann-comment-selected"></div>
      <textarea class="ann-comment-input" id="ann-comment-input" placeholder="Add a note… (optional)" rows="3"></textarea>
      <div class="ann-comment-actions">
        <button class="ann-comment-skip" id="ann-comment-skip">Skip</button>
        <button class="ann-comment-save" id="ann-comment-save">Save note</button>
      </div>
    </div>

    <!-- Annotations List Panel -->
    <div class="reader-toc-panel" id="ann-list-panel">
      <div class="reader-toc-header"><span>Highlights &amp; Notes</span><button id="ann-list-close">&#10005;</button></div>
      <div class="reader-toc-list" id="ann-list"></div>
    </div>
  `;
}

// ─── Prefs ───────────────────────────────────────────────────────────────────

function loadPrefs(): ReaderPrefs {
  try {
    const p = JSON.parse(localStorage.getItem("bookworm_reader_prefs") ?? "");
    return { theme: p.theme ?? "light", fontSize: p.fontSize ?? 100,
      margins: { ...DEFAULT_MARGINS, ...(p.margins ?? {}) } };
  } catch { return { theme: "light", fontSize: 100, margins: { ...DEFAULT_MARGINS } }; }
}
function savePrefs() {
  localStorage.setItem("bookworm_reader_prefs", JSON.stringify(state.prefs));
}

// ─── Iframe style injection ──────────────────────────────────────────────────

function applyIframeStyles() {
  if (!state.rendition) return;
  const { theme, fontSize, margins } = state.prefs;
  const t = THEMES[theme];
  const css = `
    html, body {
      background: ${t.bg} !important;
      margin: 0 !important;
      overflow: hidden !important;
    }
    body {
      color: ${t.fg} !important;
      font-size: ${fontSize}% !important;
      line-height: 1.7 !important;
      padding-top: ${margins.top}px !important;
      padding-bottom: ${margins.bottom}px !important;
      padding-left: ${margins.left}px !important;
      padding-right: ${margins.right}px !important;
      box-sizing: border-box !important;
    }
    * { max-width: 100%; box-sizing: border-box; }
    h1,h2,h3,h4,h5,h6 { color: ${t.fg} !important; }
    a { color: #6366f1 !important; }
    .bw-highlight { cursor: pointer; }
  `;
  const container = document.getElementById("epub-viewer");
  if (container) container.style.background = t.containerBg;
  try {
    state.rendition.getContents().forEach((c: any) => {
      try {
        const doc = c.document;
        if (!doc) return;
        let style = doc.getElementById("bw-custom-style");
        if (!style) {
          style = doc.createElement("style");
          style.id = "bw-custom-style";
          (doc.head ?? doc.documentElement).appendChild(style);
        }
        style.textContent = css;
      } catch {}
    });
  } catch {}
}

function syncSettingsUI() {
  const { theme, fontSize, margins } = state.prefs;
  const fl = document.getElementById("font-size-label");
  if (fl) fl.textContent = `${fontSize}%`;
  document.querySelectorAll(".theme-btn").forEach(b =>
    (b as HTMLElement).classList.toggle("active", (b as HTMLElement).dataset.theme === theme)
  );
  (["top","bottom","left","right"] as (keyof ReaderMargins)[]).forEach(s => {
    const el = document.getElementById(`margin-${s}`) as HTMLInputElement;
    if (el) el.value = String(margins[s]);
  });
}

function applyPrefs() {
  if (!state.rendition) return;
  applyIframeStyles();
  syncSettingsUI();
  savePrefs();
}

// ─── Progress ────────────────────────────────────────────────────────────────

/**
 * Compute progress. Prefers the event's own percentage (epub.js computes internally
 * via its own CFI comparison path which is more reliable than calling percentageFromCfi
 * externally). Falls back to spine-based estimate before locations generate.
 */
function calcProgress(cfi: string, locationEvent: any): { pct: number; page: number | null } {
  // 1. Best source: event.start.percentage — set by epub.js after locations.generate()
  const pct_event = locationEvent?.start?.percentage;
  if (typeof pct_event === "number" && state.locationsReady) {
    const pct = Math.min(100, Math.round(pct_event * 100));
    const page = state.totalPages > 0
      ? Math.max(1, Math.min(state.totalPages, Math.round(pct_event * state.totalPages) + 1))
      : null;
    return { pct, page };
  }
  // 2. Second best: call percentageFromCfi ourselves (works when we don't have an event)
  if (state.locationsReady && cfi) {
    try {
      const pct_raw: number = state.book.locations.percentageFromCfi(cfi);
      if (typeof pct_raw === "number" && pct_raw >= 0) {
        const pct = Math.min(100, Math.round(pct_raw * 100));
        const page = state.totalPages > 0
          ? Math.max(1, Math.min(state.totalPages, Math.round(pct_raw * state.totalPages) + 1))
          : null;
        return { pct, page };
      }
    } catch {}
  }
  // 3. Spine-based estimate (before generate() completes)
  const numSections = Math.max(1, (state.book?.spine?.spineItems ?? []).length);
  const sIdx = locationEvent?.start?.index ?? 0;
  const dp = locationEvent?.start?.displayed?.page ?? 1;
  const dt = Math.max(1, locationEvent?.start?.displayed?.total ?? 1);
  const progress = (sIdx + dp / dt) / numSections;
  return { pct: Math.min(100, Math.round(progress * 100)), page: null };
}

function updateProgressDisplay(pct: number, page: number | null) {
  const pctEl = document.getElementById("epub-pct-input") as HTMLInputElement;
  if (pctEl && document.activeElement !== pctEl) pctEl.value = `${pct}%`;

  const pgEl = document.getElementById("epub-page-input") as HTMLInputElement;
  if (pgEl && document.activeElement !== pgEl)
    pgEl.value = page != null ? String(page) : (state.locationsReady ? String(Math.max(1, Math.round(pct / 100 * state.totalPages))) : "…");

  const totalEl = document.getElementById("epub-page-total");
  if (totalEl) totalEl.textContent = state.totalPages > 0 ? `/ ${state.totalPages}` : "";

  const bar = document.getElementById("reader-progress-fill");
  if (bar) (bar as HTMLElement).style.width = `${pct}%`;
  const txt = document.getElementById("reader-progress-text");
  if (txt) txt.textContent = `${pct}%`;
}

// ─── Annotations ─────────────────────────────────────────────────────────────

function loadAnnotations() {
  try { state.annotations = JSON.parse(localStorage.getItem(`bookworm_ann_${state.bookId}`) ?? "[]"); }
  catch { state.annotations = []; }
}
function saveAnnotations() {
  localStorage.setItem(`bookworm_ann_${state.bookId}`, JSON.stringify(state.annotations));
}
function applyAnnotations() {
  state.annotations.forEach(ann => {
    try {
      state.rendition.annotations.highlight(
        ann.cfi, {}, undefined, "bw-highlight", { fill: ANN_COLORS[ann.color] ?? ANN_COLORS.yellow }
      );
    } catch {}
  });
}

// ─── UI visibility (auto-hide) ───────────────────────────────────────────────

function showUI() {
  state.uiVisible = true;
  document.getElementById("reader-toolbar")?.classList.remove("ui-hidden");
  document.getElementById("reader-controls")?.classList.remove("ui-hidden");
  resetUiTimer();
}

function hideUI() {
  // Don't hide if any panel is open
  if (document.getElementById("toc-panel")?.classList.contains("open")) return;
  if (document.getElementById("ann-list-panel")?.classList.contains("open")) return;
  if (document.getElementById("settings-sheet")?.classList.contains("open")) return;
  if (document.getElementById("ann-comment-sheet")?.classList.contains("open")) return;
  if (document.getElementById("annotation-picker")?.classList.contains("visible")) return;
  state.uiVisible = false;
  document.getElementById("reader-toolbar")?.classList.add("ui-hidden");
  document.getElementById("reader-controls")?.classList.add("ui-hidden");
}

function resetUiTimer() {
  if (state.uiTimer) clearTimeout(state.uiTimer);
  state.uiTimer = setTimeout(hideUI, UI_HIDE_DELAY);
}

// ─── Panels ──────────────────────────────────────────────────────────────────

function closeAllPanels() {
  ["toc-panel","ann-list-panel"].forEach(id => document.getElementById(id)?.classList.remove("open"));
  ["settings-sheet","ann-comment-sheet"].forEach(id => document.getElementById(id)?.classList.remove("open"));
  document.getElementById("reader-overlay")?.classList.remove("visible");
}
function openToc() {
  closeAllPanels(); showUI();
  document.getElementById("toc-panel")?.classList.add("open");
  document.getElementById("reader-overlay")?.classList.add("visible");
}
function openSettings() {
  closeAllPanels(); showUI(); syncSettingsUI();
  document.getElementById("settings-sheet")?.classList.add("open");
  document.getElementById("reader-overlay")?.classList.add("visible");
}
function openAnnList() {
  closeAllPanels(); showUI(); renderAnnList();
  document.getElementById("ann-list-panel")?.classList.add("open");
  document.getElementById("reader-overlay")?.classList.add("visible");
}
function hideAnnotationPicker() {
  document.getElementById("annotation-picker")?.classList.remove("visible");
  state.pendingCfi = null; state.pendingColor = null; state.pendingText = "";
}
function openCommentSheet() {
  const sel = document.getElementById("ann-comment-selected");
  if (sel) sel.textContent = state.pendingText.length > 120
    ? state.pendingText.slice(0, 120) + "…" : state.pendingText;
  const input = document.getElementById("ann-comment-input") as HTMLTextAreaElement;
  const existing = state.annotations.find(a => a.cfi === state.pendingCfi);
  if (input) input.value = existing?.note ?? "";
  document.getElementById("ann-comment-sheet")?.classList.add("open");
  document.getElementById("reader-overlay")?.classList.add("visible");
  setTimeout(() => input?.focus(), 250);
}

// ─── Annotation commit ───────────────────────────────────────────────────────

function commitAnnotation(note: string) {
  if (!state.pendingCfi || !state.pendingColor) return;
  const { pendingCfi: cfi, pendingColor: color, pendingText: text } = state;
  // Remove any existing annotation at this CFI first
  state.annotations = state.annotations.filter(a => a.cfi !== cfi);
  try { state.rendition.annotations.remove(cfi, "highlight"); } catch {}
  // Add new
  state.annotations.push({ cfi, color, text, note });
  saveAnnotations();
  try {
    state.rendition.annotations.highlight(cfi, {}, undefined, "bw-highlight", { fill: ANN_COLORS[color] });
  } catch {}
  hideAnnotationPicker();
  closeAllPanels();
  resetUiTimer();
}

// ─── Annotations list ────────────────────────────────────────────────────────

function renderAnnList() {
  const list = document.getElementById("ann-list");
  if (!list) return;
  if (!state.annotations.length) {
    list.innerHTML = `<div class="ann-list-empty">No highlights yet.<br>Select text in the book to add one.</div>`;
    return;
  }
  list.innerHTML = "";
  [...state.annotations].reverse().forEach(ann => {
    const item = document.createElement("div");
    item.className = "ann-list-item";
    item.innerHTML = `
      <div class="ann-list-row">
        <span class="ann-list-dot" style="background:${ANN_COLORS[ann.color]};border:2px solid ${ANN_BORDER[ann.color] ?? "#999"}"></span>
        <span class="ann-list-text">${ann.text ? escHtml(ann.text.slice(0,100)) + (ann.text.length>100?"…":"") : "<em style='opacity:.5'>No text captured</em>"}</span>
        <button class="ann-list-delete" data-cfi="${escAttr(ann.cfi)}">&#10005;</button>
      </div>
      ${ann.note ? `<div class="ann-list-note">"${escHtml(ann.note)}"</div>` : ""}
      <div class="ann-list-meta">
        <button class="ann-list-jump" data-cfi="${escAttr(ann.cfi)}">Jump to page</button>
        <button class="ann-list-edit" data-cfi="${escAttr(ann.cfi)}">Edit note</button>
      </div>`;
    list.appendChild(item);
  });
  list.querySelectorAll(".ann-list-jump").forEach(btn =>
    btn.addEventListener("click", () => { state.rendition?.display((btn as HTMLElement).dataset.cfi!); closeAllPanels(); })
  );
  list.querySelectorAll(".ann-list-edit").forEach(btn =>
    btn.addEventListener("click", () => {
      const cfi = (btn as HTMLElement).dataset.cfi!;
      const ann = state.annotations.find(a => a.cfi === cfi);
      if (!ann) return;
      state.pendingCfi = cfi; state.pendingColor = ann.color; state.pendingText = ann.text;
      document.getElementById("ann-list-panel")?.classList.remove("open");
      openCommentSheet();
    })
  );
  list.querySelectorAll(".ann-list-delete").forEach(btn =>
    btn.addEventListener("click", () => {
      const cfi = (btn as HTMLElement).dataset.cfi!;
      state.annotations = state.annotations.filter(a => a.cfi !== cfi);
      saveAnnotations();
      try { state.rendition.annotations.remove(cfi, "highlight"); } catch {}
      renderAnnList();
    })
  );
}

function escHtml(s: string) {
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function escAttr(s: string) { return s.replace(/"/g,"&quot;"); }

// ─── TOC ─────────────────────────────────────────────────────────────────────

async function buildToc() {
  try {
    await state.book.loaded.navigation;
    const toc = state.book.navigation?.toc ?? [];
    const list = document.getElementById("toc-list");
    if (!list || !toc.length) return;
    list.innerHTML = "";
    function renderItems(items: any[], depth = 0) {
      items.forEach((item: any) => {
        const btn = document.createElement("button");
        btn.className = "toc-item";
        btn.style.paddingLeft = `${1 + depth * 1.25}rem`;
        btn.textContent = item.label?.trim() ?? "";
        btn.addEventListener("click", () => { state.rendition?.display(item.href); closeAllPanels(); });
        list.appendChild(btn);
        if (item.subitems?.length) renderItems(item.subitems, depth + 1);
      });
    }
    renderItems(toc);
  } catch {}
}

// ─── Locations (async page count) ────────────────────────────────────────────

async function generateLocations() {
  try {
    await state.book.locations.generate(1024);
    state.totalPages = state.book.locations.length();
    state.locationsReady = true;
    console.log(`[epub] locations ready: ${state.totalPages} total`);
    // Re-compute with the last known location event (has percentage set now)
    if (state.currentCfi) {
      const { pct, page } = calcProgress(state.currentCfi, state.lastLocationEvent);
      updateProgressDisplay(pct, page);
    }
  } catch (e) { console.warn("[epub] locations.generate failed:", e); }
}

// ─── Init ─────────────────────────────────────────────────────────────────────

export async function initEpubReader(bookData: Book, onStatus?: (msg: string) => void): Promise<void> {
  const log = (msg: string) => { console.log(`[epub] ${msg}`); onStatus?.(msg); };

  state.sessionStart = new Date();
  state.currentCfi = "";
  state.bookId = bookData.id;
  state.totalPages = 0;
  state.locationsReady = false;
  state.prefs = loadPrefs();
  loadAnnotations();

  if (state.book) { try { state.book.destroy(); } catch {} state.book = null; state.rendition = null; }

  const token = localStorage.getItem("bookworm_token") ?? "";
  const fileUrl = `/api/reader/${bookData.id}/file?token=${encodeURIComponent(token)}`;
  log("Loading epub…");

  const container = document.getElementById("epub-viewer")!;
  // CSS handles sizing; no explicit px dimensions (avoids wrong size before fullscreen settles)
  container.style.cssText = `position:absolute;inset:0;overflow:hidden`;

  try { state.book = ePub(fileUrl, { openAs: "epub" }); } catch (e) { log(`ERROR: ${e}`); return; }

  try {
    await Promise.race([state.book.ready,
      new Promise((_,r) => setTimeout(() => r(new Error("timeout")), 20000))]);
    log("Book ready");
  } catch (e) { log(`ERROR: ${e}`); return; }

  // Wait for fullscreen to settle so we measure the real viewport
  await new Promise<void>(resolve => {
    if (document.fullscreenElement) { resolve(); return; }
    let done = false;
    const fin = () => { if (!done) { done = true; resolve(); } };
    document.addEventListener("fullscreenchange", fin, { once: true });
    setTimeout(fin, 500); // fallback if no fullscreen
  });

  const w = container.offsetWidth || window.innerWidth;
  const h = container.offsetHeight || window.innerHeight;
  log(`Viewport: ${w}x${h}`);

  try {
    state.rendition = state.book.renderTo(container, { width: w, height: h, spread: "none", flow: "paginated" });
  } catch (e) { log(`ERROR: ${e}`); return; }

  // Resize rendition if fullscreen state changes after init
  const onFullscreenResize = () => {
    const nw = container.offsetWidth || window.innerWidth;
    const nh = container.offsetHeight || window.innerHeight;
    state.rendition?.resize(nw, nh);
  };
  document.addEventListener("fullscreenchange", onFullscreenResize);

  try {
    const saved = await progressApi.get(bookData.id);
    if (saved?.position) state.currentCfi = saved.position;
  } catch {}

  try {
    await Promise.race([state.rendition.display(state.currentCfi || undefined),
      new Promise((_,r) => setTimeout(() => r(new Error("display() timeout")), 20000))]);
    log("SUCCESS");
  } catch (e) { log(`ERROR: ${e}`); return; }

  applyPrefs();
  applyAnnotations();
  buildToc();
  generateLocations(); // async — page count appears when ready

  // ── Navigation helpers ──
  const iframePrev = () => { state.rendition?.prev(); resetUiTimer(); };
  const iframeNext = () => { state.rendition?.next(); resetUiTimer(); };

  // ── Touch overlay ──
  // The ONLY reliable way to prevent epub.js's internal scroll: place a transparent
  // div on top of everything that intercepts ALL touch events. We handle swipe/tap
  // ourselves and call rendition.prev()/next() programmatically.
  const overlay = document.createElement("div");
  overlay.id = "epub-touch-overlay";
  overlay.style.cssText = "position:absolute;inset:0;z-index:10;touch-action:none;";
  container.appendChild(overlay);

  let touchStartX = 0, touchStartY = 0, touchStartTime = 0;

  overlay.addEventListener("touchstart", (e: TouchEvent) => {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
    touchStartTime = Date.now();
  }, { passive: true });

  overlay.addEventListener("touchmove", (e: TouchEvent) => {
    // Block all native scroll/gesture from this overlay
    e.preventDefault();
  }, { passive: false });

  overlay.addEventListener("touchend", (e: TouchEvent) => {
    const dx = e.changedTouches[0].clientX - touchStartX;
    const dy = e.changedTouches[0].clientY - touchStartY;
    const dt = Date.now() - touchStartTime;

    // Swipe
    if (dt < 400 && Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 2) {
      dx < 0 ? iframeNext() : iframePrev();
      return;
    }

    // Tap
    if (dt < 300 && Math.abs(dx) < 15 && Math.abs(dy) < 15) {
      const w = overlay.clientWidth;
      const tapX = e.changedTouches[0].clientX;

      if (tapX < w * 0.3) {
        iframePrev();
      } else if (tapX > w * 0.7) {
        iframeNext();
      } else {
        // Center tap — toggle UI
        if (state.uiVisible) hideUI(); else showUI();
      }
      return;
    }
  }, { passive: true });

  // For text selection: long-press should pass through to iframe.
  // Temporarily hide overlay during long-press so user can select text.
  let longPressTimer: ReturnType<typeof setTimeout> | null = null;
  overlay.addEventListener("touchstart", () => {
    longPressTimer = setTimeout(() => {
      overlay.style.pointerEvents = "none";
    }, 500);
  });
  overlay.addEventListener("touchend", () => {
    if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }
    // Re-enable overlay after a short delay (selection might still be active)
    setTimeout(() => { overlay.style.pointerEvents = "auto"; }, 100);
  });
  overlay.addEventListener("touchmove", () => {
    // If finger moves, cancel long-press
    if (longPressTimer) { clearTimeout(longPressTimer); longPressTimer = null; }
  });

  // ── Re-apply styles on every page render ──
  state.rendition.on("rendered", () => {
    applyIframeStyles();
    applyAnnotations();
  });

  // ── Progress + auto-save ──
  let saveDebounce: ReturnType<typeof setTimeout> | null = null;
  state.rendition.on("locationChanged", (location: any) => {
    const cfi = location?.start?.cfi ?? "";
    state.currentCfi = cfi;
    state.lastLocationEvent = location;
    const { pct, page } = calcProgress(cfi, location);
    updateProgressDisplay(pct, page);
    if (saveDebounce) clearTimeout(saveDebounce);
    saveDebounce = setTimeout(() => saveProgress(bookData.id), 800);
  });

  // ── Text selection → capture IMMEDIATELY then show colour picker ──
  state.rendition.on("selected", (cfiRange: string, contents: any) => {
    // Capture the selection text right now, before anything clears it
    let text = "";
    try { text = contents?.window?.getSelection()?.toString() ?? ""; } catch {}
    if (!text && cfiRange) {
      try { text = state.rendition.getContents()[0]?.window?.getSelection()?.toString() ?? ""; } catch {}
    }
    state.pendingCfi = cfiRange;
    state.pendingText = text;
    state.pendingColor = null;
    showUI();
    document.getElementById("annotation-picker")?.classList.add("visible");
  });

  // ── Tap on existing highlight → show note ──
  state.rendition.on("markClicked", (cfi: string) => {
    const ann = state.annotations.find(a => a.cfi === cfi);
    if (!ann) return;
    state.pendingCfi = cfi; state.pendingColor = ann.color; state.pendingText = ann.text;
    openCommentSheet();
  });

  // ── Navigation: buttons ──
  document.getElementById("epub-prev-btn")?.addEventListener("click", iframePrev);
  document.getElementById("epub-next-btn")?.addEventListener("click", iframeNext);

  // ── Progress inputs ──
  const pctInput = document.getElementById("epub-pct-input") as HTMLInputElement;
  pctInput?.addEventListener("focus", () => pctInput.select());
  pctInput?.addEventListener("keydown", e => {
    if (e.key !== "Enter") return;
    pctInput.blur();
    const pct = parseFloat(pctInput.value.replace("%","").trim());
    if (!isNaN(pct) && pct >= 0 && pct <= 100) {
      if (state.locationsReady) {
        const cfi = state.book.locations.cfiFromPercentage(pct / 100);
        if (cfi) { state.rendition?.display(cfi); return; }
      }
      // Fallback: jump by spine section
      const numSections = (state.book?.spine?.spineItems ?? []).length;
      const targetSection = Math.floor((pct / 100) * numSections);
      const section = state.book?.spine?.spineItems[targetSection];
      if (section) state.rendition?.display(section.href);
    }
  });
  pctInput?.addEventListener("blur", () => {
    const { pct } = calcProgress(state.currentCfi, null);
    pctInput.value = `${pct}%`;
  });

  const pageInput = document.getElementById("epub-page-input") as HTMLInputElement;
  pageInput?.addEventListener("focus", () => pageInput.select());
  pageInput?.addEventListener("keydown", e => {
    if (e.key !== "Enter") return;
    pageInput.blur();
    const page = parseInt(pageInput.value.trim(), 10);
    if (isNaN(page)) return;
    if (state.locationsReady && state.totalPages > 0) {
      // Convert page → percentage → CFI (all from same locations system)
      const pct = Math.min(1, Math.max(0, (page - 1) / (state.totalPages - 1)));
      const cfi = state.book.locations.cfiFromPercentage(pct);
      if (cfi) { state.rendition?.display(cfi); return; }
    }
    // Fallback: spine section jump
    const numSections = (state.book?.spine?.spineItems ?? []).length;
    const totalEst = state.totalPages || numSections * 10;
    const targetSection = Math.min(numSections - 1, Math.floor(((page - 1) / totalEst) * numSections));
    const section = state.book?.spine?.spineItems[targetSection];
    if (section) state.rendition?.display(section.href);
  });
  pageInput?.addEventListener("blur", () => {
    const { page } = calcProgress(state.currentCfi, null);
    pageInput.value = page != null ? String(page) : "…";
  });

  // ── TOC + panels ──
  document.getElementById("toc-btn")?.addEventListener("click", openToc);
  document.getElementById("toc-close")?.addEventListener("click", closeAllPanels);
  document.getElementById("ann-list-btn")?.addEventListener("click", openAnnList);
  document.getElementById("ann-list-close")?.addEventListener("click", closeAllPanels);
  document.getElementById("settings-btn")?.addEventListener("click", openSettings);
  document.getElementById("reader-overlay")?.addEventListener("click", () => {
    closeAllPanels(); hideAnnotationPicker();
  });

  // ── Theme ──
  document.querySelectorAll(".theme-btn").forEach(btn =>
    btn.addEventListener("click", () => {
      state.prefs.theme = (btn as HTMLElement).dataset.theme as any;
      applyPrefs();
    })
  );

  // ── Font size ──
  document.getElementById("font-up")?.addEventListener("click", () => { state.prefs.fontSize = Math.min(state.prefs.fontSize + 10, 200); applyPrefs(); });
  document.getElementById("font-down")?.addEventListener("click", () => { state.prefs.fontSize = Math.max(state.prefs.fontSize - 10, 60); applyPrefs(); });

  // ── Margins ──
  (["top","bottom","left","right"] as (keyof ReaderMargins)[]).forEach(side => {
    const input = document.getElementById(`margin-${side}`) as HTMLInputElement;
    input?.addEventListener("change", () => {
      const val = Math.max(0, Math.min(120, parseInt(input.value,10) || 0));
      input.value = String(val);
      state.prefs.margins[side] = val;
      applyPrefs();
    });
  });

  // ── Colour picker → note sheet ──
  document.querySelectorAll(".ann-color-btn").forEach(btn =>
    btn.addEventListener("click", () => {
      if (!state.pendingCfi) return;
      state.pendingColor = (btn as HTMLElement).dataset.color!;
      document.getElementById("annotation-picker")?.classList.remove("visible");
      openCommentSheet();
    })
  );
  document.getElementById("ann-remove")?.addEventListener("click", () => {
    if (state.pendingCfi) {
      state.annotations = state.annotations.filter(a => a.cfi !== state.pendingCfi);
      saveAnnotations();
      try { state.rendition.annotations.remove(state.pendingCfi, "highlight"); } catch {}
    }
    hideAnnotationPicker();
  });

  // ── Note sheet: save / skip ──
  document.getElementById("ann-comment-save")?.addEventListener("click", () => {
    const note = (document.getElementById("ann-comment-input") as HTMLTextAreaElement)?.value.trim() ?? "";
    commitAnnotation(note);
  });
  document.getElementById("ann-comment-skip")?.addEventListener("click", () => commitAnnotation(""));

  // ── Start UI hide timer ──
  showUI();

  // ── Cleanup ──
  state.saveTimer = setInterval(() => saveProgress(bookData.id), 30_000);
  const cleanup = () => {
    if (state.saveTimer) clearInterval(state.saveTimer);
    if (state.uiTimer) clearTimeout(state.uiTimer);
    document.removeEventListener("fullscreenchange", onFullscreenResize);
    saveProgress(bookData.id);
    try { state.book?.destroy(); } catch {}
    document.removeEventListener("page:mounted", cleanup);
  };
  document.addEventListener("page:mounted", cleanup, { once: true });
}

// ─── Save progress ───────────────────────────────────────────────────────────

async function saveProgress(bookId: number): Promise<void> {
  if (!state.currentCfi) return;
  const now = new Date();
  const { pct } = calcProgress(state.currentCfi, null);
  try {
    await progressApi.update(bookId, state.currentCfi, pct, 0, 0,
      state.sessionStart.toISOString(), now.toISOString());
    state.sessionStart = now;
  } catch {}
}
