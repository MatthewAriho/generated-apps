import ePub from "epubjs";
import type { Book } from "../api";
import { progress as progressApi } from "../api";

interface ReaderMargins { top: number; bottom: number; left: number; right: number; }

type ReadingMode = "scroll" | "pages";

interface ReaderPrefs {
  theme: "light" | "sepia" | "dark";
  fontSize: number;
  margins: ReaderMargins;
  readingMode: ReadingMode;
}

interface Annotation {
  cfi: string;
  color: string;
  text: string;
  note: string;
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
  // Per-spine-item location counts, so chapter-based progress estimates are
  // weighted by actual chapter length instead of treating every spine item
  // (cover, copyright, 60-page chapter) as equal.
  spineWeights: { counts: number[]; cum: number[]; total: number } | null;
  uiVisible: boolean;
  // Custom paginated mode state
  pageMode: {
    active: boolean;
    container: HTMLElement | null;
    currentPage: number;
    totalPageCount: number;
    chapterIndex: number;
    chapterHtml: string;
    columnWidth: number;
  };
}

const DEFAULT_MARGINS: ReaderMargins = { top: 8, bottom: 8, left: 24, right: 24 };
const UI_HIDE_DELAY = 3000;

const THEMES: Record<string, { bg: string; fg: string; containerBg: string }> = {
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
  prefs: { theme: "light", fontSize: 100, margins: { ...DEFAULT_MARGINS }, readingMode: "scroll" },
  annotations: [], pendingCfi: null, pendingColor: null, pendingText: "",
  bookId: 0, totalPages: 0, locationsReady: false, spineWeights: null, uiVisible: true,
  pageMode: { active: false, container: null, currentPage: 0, totalPageCount: 0, chapterIndex: 0, chapterHtml: "", columnWidth: 0 },
};

// ─── HTML ────────────────────────────────────────────────────────────────────

export function renderEpubReader(_bookData: Book): string {
  return `
    <div class="reader-epub-shell" id="epub-viewer"></div>

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
        <span class="settings-label">Reading mode</span>
        <div class="theme-btns">
          <button class="mode-btn" data-mode="scroll">Scroll</button>
          <button class="mode-btn" data-mode="pages">Pages</button>
        </div>
      </div>
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
    return {
      theme: p.theme ?? "light",
      fontSize: p.fontSize ?? 100,
      margins: { ...DEFAULT_MARGINS, ...(p.margins ?? {}) },
      readingMode: p.readingMode ?? "scroll",
    };
  } catch {
    return { theme: "light", fontSize: 100, margins: { ...DEFAULT_MARGINS }, readingMode: "scroll" };
  }
}
function savePrefs() {
  localStorage.setItem("bookworm_reader_prefs", JSON.stringify(state.prefs));
}

// ─── epub.js theme ───────────────────────────────────────────────────────────
// Registered on the rendition BEFORE display() so epub.js measures each
// section WITH the theme applied. (Previously we injected a <style> into each
// iframe on the "rendered" event — that reflowed content AFTER epub.js had
// measured it, corrupting the manager's height/position map and causing the
// blank-pages-then-jump behaviour.)

function themeRules() {
  const { theme, margins } = state.prefs;
  const t = THEMES[theme];
  return {
    "html, body": {
      "background": `${t.bg} !important`,
      "margin": "0 !important",
    },
    "body": {
      "color": `${t.fg} !important`,
      "line-height": "1.7 !important",
      "padding-top": `${margins.top}px !important`,
      "padding-bottom": `${margins.bottom}px !important`,
      "padding-left": `${margins.left}px !important`,
      "padding-right": `${margins.right}px !important`,
      "box-sizing": "border-box !important",
    },
    "*": { "max-width": "100%", "box-sizing": "border-box" },
    "h1,h2,h3,h4,h5,h6": { "color": `${t.fg} !important` },
    "a": { "color": "#6366f1 !important" },
    ".bw-highlight": { "cursor": "pointer" },
  };
}

function applyRenditionTheme() {
  if (!state.rendition) return;
  const t = THEMES[state.prefs.theme];
  const container = document.getElementById("epub-viewer");
  if (container) container.style.background = t.containerBg;
  try {
    // Re-registering under the same name replaces the rules; select() pushes
    // the update into already-rendered contents. fontSize() goes through the
    // themes pipeline too, so epub.js re-measures instead of drifting.
    state.rendition.themes.register("bw", themeRules());
    state.rendition.themes.select("bw");
    state.rendition.themes.fontSize(`${state.prefs.fontSize}%`);
  } catch {}
}

// ─── Custom paginated styles (Option B) ─────────────────────────────────────

function applyCustomPageStyles(el: HTMLElement) {
  const { theme, fontSize, margins } = state.prefs;
  const t = THEMES[theme];
  el.style.background = t.bg;
  el.style.color = t.fg;
  el.style.fontSize = `${fontSize}%`;
  el.style.lineHeight = "1.7";
  el.style.paddingTop = `${margins.top}px`;
  el.style.paddingBottom = `${margins.bottom}px`;
  el.style.paddingLeft = `${margins.left}px`;
  el.style.paddingRight = `${margins.right}px`;
}

function syncSettingsUI() {
  const { theme, fontSize, margins, readingMode } = state.prefs;
  const fl = document.getElementById("font-size-label");
  if (fl) fl.textContent = `${fontSize}%`;
  document.querySelectorAll(".theme-btn").forEach(b =>
    (b as HTMLElement).classList.toggle("active", (b as HTMLElement).dataset.theme === theme)
  );
  document.querySelectorAll(".mode-btn").forEach(b =>
    (b as HTMLElement).classList.toggle("active", (b as HTMLElement).dataset.mode === readingMode)
  );
  (["top","bottom","left","right"] as (keyof ReaderMargins)[]).forEach(s => {
    const el = document.getElementById(`margin-${s}`) as HTMLInputElement;
    if (el) el.value = String(margins[s]);
  });
}

function applyPrefs() {
  if (!state.rendition && !state.pageMode.active) return;
  if (state.rendition) applyRenditionTheme();
  if (state.pageMode.active && state.pageMode.container) {
    const inner = state.pageMode.container.querySelector(".pages-inner") as HTMLElement;
    if (inner) {
      applyCustomPageStyles(inner);
      recalcCustomPages();
    }
  }
  syncSettingsUI();
  savePrefs();
}

// ─── Progress ────────────────────────────────────────────────────────────────

// Chapter index + fraction-within-chapter → global 0..1 progress.
// Weighted by per-chapter location counts when available, else equal spine
// weighting (the old behaviour, which made progress "jump to 1/3" on books
// with few, unevenly sized spine items).
function chapterProgress(chapterIndex: number, chapterFraction: number): number {
  const numSections = Math.max(1, (state.book?.spine?.spineItems ?? []).length);
  const w = state.spineWeights;
  if (w && w.counts[chapterIndex] != null) {
    return (w.cum[chapterIndex] + chapterFraction * w.counts[chapterIndex]) / w.total;
  }
  return (chapterIndex + chapterFraction) / numSections;
}

function calcProgress(_cfi: string, locationEvent: any): { pct: number; page: number | null } {
  let progress: number;

  if (state.pageMode.active) {
    // Custom paginated mode — our own page tracking
    const pm = state.pageMode;
    const chapterFraction = pm.totalPageCount > 0 ? pm.currentPage / pm.totalPageCount : 0;
    progress = chapterProgress(pm.chapterIndex, chapterFraction);
  } else {
    // Scrolled mode. NOTE: epub.js emits two location events with DIFFERENT
    // payload shapes:
    //   "relocated"       → { start: { cfi, index, displayed, percentage }, end: {...} }
    //   "locationChanged" → { index, href, start: <cfi string>, end, percentage }
    // We subscribe to "relocated", but read both shapes defensively.
    const sIdx = locationEvent?.start?.index ?? locationEvent?.index ?? 0;
    const dp = locationEvent?.start?.displayed?.page ?? 1;
    const dt = Math.max(1, locationEvent?.start?.displayed?.total ?? 1);
    const spineProgress = chapterProgress(sIdx, dp / dt);

    // Prefer epub.js's own locations-based percentage once generate() is done
    const pct_event = locationEvent?.start?.percentage ?? locationEvent?.percentage;
    const useLocations = state.locationsReady && typeof pct_event === "number" && pct_event > 0;
    progress = useLocations ? pct_event : spineProgress;
  }

  const pct = Math.min(100, Math.round(progress * 100));
  const page = state.totalPages > 0
    ? Math.max(1, Math.min(state.totalPages, Math.round(progress * state.totalPages) + 1))
    : null;
  return { pct, page };
}

function updateProgressDisplay(pct: number, page: number | null) {
  const pctEl = document.getElementById("epub-pct-input") as HTMLInputElement;
  if (pctEl && document.activeElement !== pctEl) pctEl.value = `${pct}%`;

  const pgEl = document.getElementById("epub-page-input") as HTMLInputElement;
  if (pgEl && document.activeElement !== pgEl)
    pgEl.value = page != null ? String(page) : String(Math.max(1, Math.round(pct / 100 * Math.max(1, state.totalPages))));

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
  if (!state.rendition) return;
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
  state.annotations = state.annotations.filter(a => a.cfi !== cfi);
  try { state.rendition?.annotations.remove(cfi, "highlight"); } catch {}
  state.annotations.push({ cfi, color, text, note });
  saveAnnotations();
  try {
    state.rendition?.annotations.highlight(cfi, {}, undefined, "bw-highlight", { fill: ANN_COLORS[color] });
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
    btn.addEventListener("click", () => {
      if (state.rendition) state.rendition.display((btn as HTMLElement).dataset.cfi!);
      closeAllPanels();
    })
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
      try { state.rendition?.annotations.remove(cfi, "highlight"); } catch {}
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
        btn.addEventListener("click", () => {
          if (state.pageMode.active) {
            navigateToTocItem(item.href);
          } else {
            state.rendition?.display(item.href);
          }
          closeAllPanels();
        });
        list!.appendChild(btn);
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
    state.spineWeights = buildSpineWeights();
    console.log(`[epub] locations ready: ${state.totalPages} total`);
    // Refresh the display now that we have real weights/percentages
    const { pct, page } = calcProgress(state.currentCfi, state.lastLocationEvent);
    updateProgressDisplay(pct, page);
  } catch (e) { console.warn("[epub] locations.generate failed:", e); }
}

// Count how many generated locations fall inside each spine item. Location
// CFIs look like "epubcfi(/6/8[chap01]!/4/2/1:0)" and each spine item exposes
// its cfiBase ("/6/8[chap01]"), so `cfiBase + "!"` is an unambiguous prefix key.
function buildSpineWeights(): { counts: number[]; cum: number[]; total: number } | null {
  try {
    const locs: string[] = state.book?.locations?._locations ?? [];
    const spineItems: any[] = state.book?.spine?.spineItems ?? [];
    if (!locs.length || !spineItems.length) return null;
    const counts = spineItems.map((s: any) => {
      const key = `${s.cfiBase}!`;
      return locs.reduce((n, l) => n + (l.includes(key) ? 1 : 0), 0);
    });
    const cum: number[] = [];
    let running = 0;
    for (const c of counts) { cum.push(running); running += c; }
    return running > 0 ? { counts, cum, total: running } : null;
  } catch { return null; }
}

// ═══════════════════════════════════════════════════════════════════════════════
// ─── OPTION B: Custom Paginated Renderer ────────────────────────────────────
// Uses epub.js for parsing only. Renders chapter HTML into a non-scrollable
// div with CSS columns. Navigation via CSS transform — no native scroll.
// ═══════════════════════════════════════════════════════════════════════════════

async function initCustomPaginated(bookData: Book, log: (msg: string) => void) {
  const container = document.getElementById("epub-viewer")!;
  container.style.cssText = "position:absolute;inset:0;overflow:hidden;";

  const t = THEMES[state.prefs.theme];
  container.style.background = t.containerBg;

  // Create the pages wrapper
  const wrapper = document.createElement("div");
  wrapper.className = "pages-wrapper";
  wrapper.style.cssText = "position:absolute;inset:0;overflow:hidden;";
  container.appendChild(wrapper);

  const inner = document.createElement("div");
  inner.className = "pages-inner";
  inner.style.cssText = `
    height: 100%;
    column-fill: auto;
    box-sizing: border-box;
    overflow: hidden;
    transition: transform 0.25s ease;
    word-wrap: break-word;
    overflow-wrap: break-word;
  `;
  wrapper.appendChild(inner);

  state.pageMode.active = true;
  state.pageMode.container = wrapper;
  state.pageMode.currentPage = 0;

  applyCustomPageStyles(inner);

  // Determine starting chapter + page
  let startChapter = 0;
  let startPage = 0;
  try {
    const saved = await progressApi.get(bookData.id);
    if (saved?.position) {
      // Positions saved from pages mode: "chapter:X:page:Y"
      const m = saved.position.match(/^chapter:(\d+):page:(\d+)$/);
      if (m) {
        startChapter = parseInt(m[1], 10);
        startPage = parseInt(m[2], 10);
      } else if (saved.position.startsWith("epubcfi(")) {
        // Positions saved from scroll mode: a CFI — map it to a spine section
        state.currentCfi = saved.position;
        const spineItems = state.book.spine?.spineItems ?? [];
        for (let i = 0; i < spineItems.length; i++) {
          const cfiBase = spineItems[i].cfiBase;
          if (cfiBase && state.currentCfi.includes(`${cfiBase}!`)) {
            startChapter = i;
            break;
          }
        }
      }
    }
  } catch {}

  state.pageMode.chapterIndex = startChapter;
  await loadChapter(startChapter, log, startPage);

  // Touch handling for custom pages — simple, no hacks needed
  let touchStartX = 0, touchStartY = 0, touchStartTime = 0;

  wrapper.addEventListener("touchstart", (e: TouchEvent) => {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
    touchStartTime = Date.now();
  }, { passive: true });

  wrapper.addEventListener("touchend", (e: TouchEvent) => {
    const dx = e.changedTouches[0].clientX - touchStartX;
    const dy = e.changedTouches[0].clientY - touchStartY;
    const dt = Date.now() - touchStartTime;

    // Swipe
    if (dt < 400 && Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(dy) * 2) {
      if (dx < 0) customPageNext();
      else customPagePrev();
      return;
    }

    // Tap
    if (dt < 300 && Math.abs(dx) < 15 && Math.abs(dy) < 15) {
      const w = wrapper.clientWidth;
      const tapX = e.changedTouches[0].clientX;

      // Check if tapped a link
      const target = document.elementFromPoint(tapX, e.changedTouches[0].clientY);
      if (target?.closest?.("a")) return; // let link work

      if (tapX < w * 0.3) {
        customPagePrev();
      } else if (tapX > w * 0.7) {
        customPageNext();
      } else {
        if (state.uiVisible) hideUI(); else showUI();
      }
    }
  }, { passive: true });

  // Mouse click for desktop
  wrapper.addEventListener("click", (e: MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target?.closest?.("a")) {
      e.preventDefault();
      const href = (target.closest("a") as HTMLAnchorElement).getAttribute("href");
      if (href) navigateToTocItem(href);
      return;
    }

    const w = wrapper.clientWidth;
    if (e.clientX < w * 0.3) customPagePrev();
    else if (e.clientX > w * 0.7) customPageNext();
    else { if (state.uiVisible) hideUI(); else showUI(); }
  });

  log("Custom paginated mode ready");
}

// initialPage: 0-based page within the chapter to land on; -1 means last page
// (used when paging backwards across a chapter boundary).
async function loadChapter(index: number, log?: (msg: string) => void, initialPage = 0) {
  const spineItems = state.book.spine?.spineItems ?? [];
  if (index < 0 || index >= spineItems.length) return;

  state.pageMode.chapterIndex = index;
  const section = spineItems[index];

  log?.(`Loading chapter ${index + 1}/${spineItems.length}...`);

  try {
    const contents = await section.load(state.book.load.bind(state.book));
    const serializer = new XMLSerializer();
    const html = serializer.serializeToString(contents);

    const wrapper = state.pageMode.container;
    if (!wrapper) return;
    const inner = wrapper.querySelector(".pages-inner") as HTMLElement;
    if (!inner) return;

    // Inject chapter HTML
    inner.innerHTML = html;

    // Fix images: resolve relative URLs to blob URLs from epub
    const images = inner.querySelectorAll("img");
    for (const img of images) {
      const src = img.getAttribute("src");
      if (src && !src.startsWith("http") && !src.startsWith("blob") && !src.startsWith("data")) {
        try {
          const resolved = new URL(src, section.url).href;
          const blob = await state.book.archive?.getBlob(resolved);
          if (blob) img.src = URL.createObjectURL(blob);
        } catch {}
      }
    }

    // Remove any scripts for safety
    inner.querySelectorAll("script").forEach(s => s.remove());

    // Apply styles
    applyCustomPageStyles(inner);

    // Apply scoped CSS from epub
    await injectEpubStyles(inner, section);

    // Images (blob URLs decode async) and web fonts finish loading AFTER the
    // first column measurement, silently changing scrollWidth. Re-measure when
    // they land — recalcCustomPages re-clamps currentPage, so stale counts no
    // longer leave trailing blank pages.
    const remeasure = () => recalcCustomPages();
    inner.querySelectorAll("img").forEach(img => {
      const im = img as HTMLImageElement;
      if (!im.complete) im.addEventListener("load", remeasure, { once: true });
    });
    (document as any).fonts?.ready?.then?.(remeasure);

    // Calculate columns after content renders
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        state.pageMode.currentPage = 0;
        recalcCustomPages();
        requestAnimationFrame(() => {
          const last = Math.max(0, state.pageMode.totalPageCount - 1);
          setCustomPage(initialPage < 0 ? last : Math.min(initialPage, last));
          log?.(`Chapter loaded: ${state.pageMode.totalPageCount} pages`);
        });
      });
    });
  } catch (e) {
    log?.(`Error loading chapter: ${e}`);
  }
}

async function injectEpubStyles(container: HTMLElement, section: any) {
  // Remove existing epub styles
  container.querySelectorAll("link[rel=stylesheet], style").forEach(el => {
    // Keep our own styles
    if ((el as HTMLElement).id === "bw-page-style") return;
    el.remove();
  });

  // Load and inject stylesheet contents
  try {
    const doc = section.document ?? section.contents;
    if (!doc) return;
    const links = doc.querySelectorAll?.("link[rel=stylesheet]") ?? [];
    for (const link of links) {
      const href = link.getAttribute("href");
      if (!href) continue;
      try {
        const resolved = new URL(href, section.url).href;
        const text = await state.book.archive?.getText(resolved);
        if (text) {
          const style = document.createElement("style");
          style.className = "bw-epub-injected-style";
          style.textContent = text;
          container.prepend(style);
        }
      } catch {}
    }
  } catch {}
}

function recalcCustomPages() {
  const wrapper = state.pageMode.container;
  if (!wrapper) return;
  const inner = wrapper.querySelector(".pages-inner") as HTMLElement;
  if (!inner) return;

  const viewWidth = wrapper.clientWidth;
  const { left: ml, right: mr } = state.prefs.margins;
  const contentWidth = viewWidth - ml - mr;

  inner.style.columnWidth = `${contentWidth}px`;
  inner.style.columnGap = `${ml + mr}px`;
  inner.style.width = `${viewWidth}px`;
  inner.style.height = `${wrapper.clientHeight}px`;

  state.pageMode.columnWidth = viewWidth;

  // Wait for layout
  requestAnimationFrame(() => {
    const totalWidth = inner.scrollWidth;
    state.pageMode.totalPageCount = Math.max(1, Math.ceil(totalWidth / viewWidth));
    // If content shrank (image sizing settled, font swap, margin change),
    // pull the current page back into range instead of leaving a blank view.
    if (state.pageMode.currentPage > state.pageMode.totalPageCount - 1) {
      setCustomPage(state.pageMode.totalPageCount - 1);
    } else {
      updateCustomProgress();
    }
  });
}

function setCustomPage(page: number) {
  const pm = state.pageMode;
  pm.currentPage = Math.max(0, Math.min(page, pm.totalPageCount - 1));

  const inner = pm.container?.querySelector(".pages-inner") as HTMLElement;
  if (inner) {
    inner.style.transform = `translateX(-${pm.currentPage * pm.columnWidth}px)`;
  }
  updateCustomProgress();
}

function customPageNext() {
  const pm = state.pageMode;
  if (pm.currentPage < pm.totalPageCount - 1) {
    setCustomPage(pm.currentPage + 1);
  } else {
    // Next chapter
    const spineItems = state.book.spine?.spineItems ?? [];
    if (pm.chapterIndex < spineItems.length - 1) {
      loadChapter(pm.chapterIndex + 1);
    }
  }
  resetUiTimer();
}

function customPagePrev() {
  const pm = state.pageMode;
  if (pm.currentPage > 0) {
    setCustomPage(pm.currentPage - 1);
  } else {
    // Previous chapter — land on its last page (-1 = last, resolved after
    // the chapter's own column measurement, so no rAF race)
    if (pm.chapterIndex > 0) {
      loadChapter(pm.chapterIndex - 1, undefined, -1);
    }
  }
  resetUiTimer();
}

function updateCustomProgress() {
  const { pct, page } = calcProgress("", null);
  updateProgressDisplay(pct, page);
}

function navigateToTocItem(href: string) {
  if (!state.book) return;

  // Find which spine section this href belongs to
  const spineItems = state.book.spine?.spineItems ?? [];
  const cleanHref = href.split("#")[0];

  for (let i = 0; i < spineItems.length; i++) {
    const sectionHref = spineItems[i].href;
    if (sectionHref === cleanHref || sectionHref.endsWith(cleanHref) || cleanHref.endsWith(sectionHref)) {
      if (state.pageMode.active) {
        loadChapter(i);
      } else {
        state.rendition?.display(href);
      }
      return;
    }
  }

  // Fallback: try displaying directly
  if (state.rendition) state.rendition.display(href);
}

// ═══════════════════════════════════════════════════════════════════════════════
// ─── OPTION A: Scrolled Mode (epub.js flow: "scrolled-doc") ─────────────────
// One spine section at a time, native vertical scroll within it, next()/prev()
// cross chapter boundaries deterministically. Unlike flow:"scrolled" +
// manager:"continuous", there are no lazily-loaded placeholder sections with
// guessed heights — so no blank regions and no scroll-position remapping.
// No overlay, no touch hacks. Links just work.
// ═══════════════════════════════════════════════════════════════════════════════

async function initScrolledMode(bookData: Book, log: (msg: string) => void) {
  const container = document.getElementById("epub-viewer")!;
  container.style.cssText = "position:absolute;inset:0;overflow:hidden;";

  try {
    state.rendition = state.book.renderTo(container, {
      width: "100%",
      height: "100%",
      flow: "scrolled-doc",
    });
  } catch (e) { log(`ERROR: ${e}`); return; }

  // Register the theme BEFORE display() so sections are measured with it.
  applyRenditionTheme();

  const onFullscreenResize = () => {
    state.rendition?.resize?.(
      container.offsetWidth || window.innerWidth,
      container.offsetHeight || window.innerHeight
    );
  };
  document.addEventListener("fullscreenchange", onFullscreenResize);

  // Restore saved position. Positions saved from "pages" mode use the
  // "chapter:X:page:Y" format — map those to the spine section; only real
  // CFIs go to display() directly.
  let displayTarget: string | undefined;
  try {
    const saved = await progressApi.get(bookData.id);
    if (saved?.position) {
      if (saved.position.startsWith("epubcfi(")) {
        state.currentCfi = saved.position;
        displayTarget = saved.position;
      } else {
        const m = saved.position.match(/^chapter:(\d+):page:\d+$/);
        const idx = m ? parseInt(m[1], 10) : NaN;
        const section = state.book?.spine?.spineItems?.[idx];
        if (section) displayTarget = section.href;
      }
    }
  } catch {}

  try {
    await Promise.race([
      state.rendition.display(displayTarget),
      new Promise((_, r) => setTimeout(() => r(new Error("display() timeout")), 20000)),
    ]);
    log("SUCCESS");
  } catch (e) { log(`ERROR: ${e}`); return; }

  applyPrefs();
  applyAnnotations();

  // ── Re-apply annotations on every section render ──
  // (Theme is handled by the themes API now — injecting styles here reflowed
  // content after epub.js had measured it, which broke scroll positioning.)
  state.rendition.on("rendered", () => {
    applyAnnotations();
  });

  // ── Tap anywhere (non-link, no selection) toggles the toolbar/controls ──
  // epub.js relays click events from inside its iframes onto the rendition,
  // so no overlay is needed and links keep working.
  state.rendition.on("click", (e: MouseEvent) => {
    try {
      if ((e.target as HTMLElement)?.closest?.("a")) return;
      const sel = state.rendition?.getContents?.()[0]?.window?.getSelection?.()?.toString?.() ?? "";
      if (sel) return;
    } catch {}
    if (state.uiVisible) hideUI(); else showUI();
  });

  // ── Progress tracking ──
  // IMPORTANT: use "relocated", NOT "locationChanged". Both fire from
  // reportLocation(), but "locationChanged" has a flat payload where `start`
  // is a CFI *string* — reading `location.start.cfi` off it yields undefined,
  // which is why progress was stuck and saves never fired (currentCfi was
  // always ""). "relocated" carries the full location object.
  let saveDebounce: ReturnType<typeof setTimeout> | null = null;
  state.rendition.on("relocated", (location: any) => {
    const cfi = location?.start?.cfi
      ?? (typeof location?.start === "string" ? location.start : "");
    state.currentCfi = cfi;
    state.lastLocationEvent = location;
    const { pct, page } = calcProgress(cfi, location);
    updateProgressDisplay(pct, page);
    if (saveDebounce) clearTimeout(saveDebounce);
    saveDebounce = setTimeout(() => saveProgress(bookData.id), 800);
  });

  // ── Text selection → highlight picker ──
  state.rendition.on("selected", (cfiRange: string, contents: any) => {
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

  // ── Prev/Next buttons navigate chapters in scroll mode ──
  document.getElementById("epub-prev-btn")?.addEventListener("click", () => {
    state.rendition?.prev(); resetUiTimer();
  });
  document.getElementById("epub-next-btn")?.addEventListener("click", () => {
    state.rendition?.next(); resetUiTimer();
  });

  // Store cleanup handler
  const cleanup = () => {
    document.removeEventListener("fullscreenchange", onFullscreenResize);
  };
  document.addEventListener("page:mounted", cleanup, { once: true });
}

// ═══════════════════════════════════════════════════════════════════════════════
// ─── Init (entry point) ─────────────────────────────────────────────────────
// ═══════════════════════════════════════════════════════════════════════════════

export async function initEpubReader(bookData: Book, onStatus?: (msg: string) => void): Promise<void> {
  const log = (msg: string) => { console.log(`[epub] ${msg}`); onStatus?.(msg); };

  state.sessionStart = new Date();
  state.currentCfi = "";
  state.bookId = bookData.id;
  state.totalPages = 0;
  state.locationsReady = false;
  state.spineWeights = null;
  state.prefs = loadPrefs();
  state.pageMode = { active: false, container: null, currentPage: 0, totalPageCount: 0, chapterIndex: 0, chapterHtml: "", columnWidth: 0 };
  loadAnnotations();

  if (state.book) { try { state.book.destroy(); } catch {} state.book = null; state.rendition = null; }

  const token = localStorage.getItem("bookworm_token") ?? "";
  const fileUrl = `/bookworm/api/reader/${bookData.id}/file?token=${encodeURIComponent(token)}`;
  log("Loading epub…");

  try { state.book = ePub(fileUrl, { openAs: "epub" }); } catch (e) { log(`ERROR: ${e}`); return; }

  try {
    await Promise.race([state.book.ready,
      new Promise((_,r) => setTimeout(() => r(new Error("timeout")), 20000))]);
    log("Book ready");
  } catch (e) { log(`ERROR: ${e}`); return; }

  // Wait for fullscreen to settle
  await new Promise<void>(resolve => {
    if (document.fullscreenElement) { resolve(); return; }
    let done = false;
    const fin = () => { if (!done) { done = true; resolve(); } };
    document.addEventListener("fullscreenchange", fin, { once: true });
    setTimeout(fin, 500);
  });

  log(`Mode: ${state.prefs.readingMode}`);

  // ── Initialize based on reading mode ──
  if (state.prefs.readingMode === "pages") {
    await initCustomPaginated(bookData, log);
  } else {
    await initScrolledMode(bookData, log);
  }

  buildToc();
  generateLocations();

  // ── Settings controls (shared) ──
  document.getElementById("toc-btn")?.addEventListener("click", openToc);
  document.getElementById("toc-close")?.addEventListener("click", closeAllPanels);
  document.getElementById("ann-list-btn")?.addEventListener("click", openAnnList);
  document.getElementById("ann-list-close")?.addEventListener("click", closeAllPanels);
  document.getElementById("settings-btn")?.addEventListener("click", openSettings);
  document.getElementById("reader-overlay")?.addEventListener("click", () => {
    closeAllPanels(); hideAnnotationPicker();
  });

  // ── Reading mode toggle ──
  document.querySelectorAll(".mode-btn").forEach(btn =>
    btn.addEventListener("click", () => {
      const newMode = (btn as HTMLElement).dataset.mode as ReadingMode;
      if (newMode === state.prefs.readingMode) return;
      state.prefs.readingMode = newMode;
      savePrefs();
      // Save progress before switching
      saveProgress(bookData.id).then(() => {
        // Full reload of reader with new mode
        window.location.reload();
      });
    })
  );

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
      try { state.rendition?.annotations.remove(state.pendingCfi, "highlight"); } catch {}
    }
    hideAnnotationPicker();
  });

  document.getElementById("ann-comment-save")?.addEventListener("click", () => {
    const note = (document.getElementById("ann-comment-input") as HTMLTextAreaElement)?.value.trim() ?? "";
    commitAnnotation(note);
  });
  document.getElementById("ann-comment-skip")?.addEventListener("click", () => commitAnnotation(""));

  // ── Progress inputs ──
  const pctInput = document.getElementById("epub-pct-input") as HTMLInputElement;
  pctInput?.addEventListener("focus", () => pctInput.select());
  pctInput?.addEventListener("keydown", e => {
    if (e.key !== "Enter") return;
    pctInput.blur();
    const pct = parseFloat(pctInput.value.replace("%","").trim());
    if (!isNaN(pct) && pct >= 0 && pct <= 100) {
      if (state.pageMode.active) {
        // Jump to approximate chapter in custom mode (length-weighted when
        // locations are ready, equal spine split otherwise)
        const spineItems = state.book.spine?.spineItems ?? [];
        let targetChapter = Math.floor((pct / 100) * spineItems.length);
        const w = state.spineWeights;
        if (w) {
          const targetLoc = (pct / 100) * w.total;
          targetChapter = 0;
          for (let i = 0; i < w.cum.length; i++) if (w.cum[i] <= targetLoc) targetChapter = i;
        }
        loadChapter(Math.min(targetChapter, spineItems.length - 1));
      } else if (state.locationsReady) {
        const cfi = state.book.locations.cfiFromPercentage(pct / 100);
        if (cfi) state.rendition?.display(cfi);
      } else {
        const numSections = (state.book?.spine?.spineItems ?? []).length;
        const targetSection = Math.floor((pct / 100) * numSections);
        const section = state.book?.spine?.spineItems[targetSection];
        if (section) state.rendition?.display(section.href);
      }
    }
  });
  pctInput?.addEventListener("blur", () => {
    const { pct } = calcProgress(state.currentCfi, state.lastLocationEvent);
    pctInput.value = `${pct}%`;
  });

  const pageInput = document.getElementById("epub-page-input") as HTMLInputElement;
  pageInput?.addEventListener("focus", () => pageInput.select());
  pageInput?.addEventListener("keydown", e => {
    if (e.key !== "Enter") return;
    pageInput.blur();
    const page = parseInt(pageInput.value.trim(), 10);
    if (isNaN(page)) return;
    if (state.pageMode.active) {
      // In custom mode, page input navigates within current chapter
      setCustomPage(page - 1);
    } else if (state.locationsReady && state.totalPages > 0) {
      const pct = Math.min(1, Math.max(0, (page - 1) / (state.totalPages - 1)));
      const cfi = state.book.locations.cfiFromPercentage(pct);
      if (cfi) state.rendition?.display(cfi);
    }
  });
  pageInput?.addEventListener("blur", () => {
    const { page } = calcProgress(state.currentCfi, state.lastLocationEvent);
    pageInput.value = page != null ? String(page) : "…";
  });

  // ── Prev/Next for custom paginated ──
  if (state.pageMode.active) {
    document.getElementById("epub-prev-btn")?.addEventListener("click", () => customPagePrev());
    document.getElementById("epub-next-btn")?.addEventListener("click", () => customPageNext());
  }

  // ── Start UI hide timer ──
  showUI();
  syncSettingsUI();

  // ── Auto-save + cleanup ──
  state.saveTimer = setInterval(() => saveProgress(bookData.id), 30_000);
  const masterCleanup = () => {
    if (state.saveTimer) clearInterval(state.saveTimer);
    if (state.uiTimer) clearTimeout(state.uiTimer);
    saveProgress(bookData.id);
    try { state.book?.destroy(); } catch {}
    document.removeEventListener("page:mounted", masterCleanup);
  };
  document.addEventListener("page:mounted", masterCleanup, { once: true });
}

// ─── Save progress ───────────────────────────────────────────────────────────

async function saveProgress(bookId: number): Promise<void> {
  if (!state.currentCfi && !state.pageMode.active) return;
  const now = new Date();
  const { pct } = calcProgress(state.currentCfi, state.lastLocationEvent);
  const position = state.currentCfi || `chapter:${state.pageMode.chapterIndex}:page:${state.pageMode.currentPage}`;
  try {
    await progressApi.update(bookId, position, pct, 0, 0,
      state.sessionStart.toISOString(), now.toISOString());
    state.sessionStart = now;
  } catch {}
}
