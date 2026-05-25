import type { Book } from "../api";
import { progress as progressApi, reader as readerApi } from "../api";
import { getToken } from "../auth";

interface PdfState {
  pdfDoc: any;
  currentPage: number;
  totalPages: number;
  scale: number;
  sessionStart: Date;
  saveTimer: ReturnType<typeof setInterval> | null;
}

const state: PdfState = {
  pdfDoc: null,
  currentPage: 1,
  totalPages: 0,
  scale: 1.4,
  sessionStart: new Date(),
  saveTimer: null,
};

export function renderPdfReader(_bookData: Book): string {
  return `
    <div class="pdf-container" id="pdf-container"></div>
    <div class="reader-controls">
      <button class="btn btn-ghost btn-sm" id="pdf-prev-btn">← Prev</button>
      <div class="reader-page-info" id="pdf-page-info">— / —</div>
      <button class="btn btn-ghost btn-sm" id="pdf-next-btn">Next →</button>
      <span class="reader-hint">↑↓ scroll</span>
    </div>
  `;
}

export async function initPdfReader(bookData: Book, onStatus?: (msg: string) => void): Promise<void> {
  const setStatus = onStatus ?? (() => {});
  const fileUrl = readerApi.getFileUrl(bookData.id);
  state.sessionStart = new Date();
  state.currentPage = 1;

  setStatus("Loading PDF.js library…");
  const pdfjsLib = await loadPdfJs();
  pdfjsLib.GlobalWorkerOptions.workerSrc =
    "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

  setStatus("Restoring your position…");
  try {
    const saved = await progressApi.get(bookData.id);
    if (saved.position) {
      state.currentPage = parseInt(saved.position, 10) || 1;
    }
  } catch {}

  setStatus("Opening PDF file…");
  const token = getToken();
  const loadingTask = pdfjsLib.getDocument({
    url: fileUrl,
    httpHeaders: token ? { Authorization: `Bearer ${token}` } : {},
    withCredentials: true,
  });

  state.pdfDoc = await loadingTask.promise;
  state.totalPages = state.pdfDoc.numPages;

  await renderCurrentPage();
  updatePageInfo();

  // Navigation
  document.getElementById("pdf-prev-btn")?.addEventListener("click", () => {
    if (state.currentPage > 1) {
      state.currentPage--;
      renderCurrentPage();
      updatePageInfo();
    }
  });

  document.getElementById("pdf-next-btn")?.addEventListener("click", () => {
    if (state.currentPage < state.totalPages) {
      state.currentPage++;
      renderCurrentPage();
      updatePageInfo();
    }
  });

  const keyHandler = (e: KeyboardEvent) => {
    if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
      if (state.currentPage > 1) { state.currentPage--; renderCurrentPage(); updatePageInfo(); }
    }
    if (e.key === "ArrowRight" || e.key === "ArrowDown") {
      if (state.currentPage < state.totalPages) { state.currentPage++; renderCurrentPage(); updatePageInfo(); }
    }
  };
  document.addEventListener("keydown", keyHandler);

  // Auto-save every 30s
  state.saveTimer = setInterval(() => saveProgress(bookData.id), 30_000);

  const cleanupHandler = () => {
    if (state.saveTimer) clearInterval(state.saveTimer);
    document.removeEventListener("keydown", keyHandler);
    document.removeEventListener("page:mounted", cleanupHandler);
  };
  document.addEventListener("page:mounted", cleanupHandler, { once: true });
}

async function renderCurrentPage(): Promise<void> {
  const container = document.getElementById("pdf-container");
  if (!container || !state.pdfDoc) return;

  // Clear existing
  container.innerHTML = "";

  const page = await state.pdfDoc.getPage(state.currentPage);
  const viewport = page.getViewport({ scale: state.scale });

  const wrapper = document.createElement("div");
  wrapper.className = "pdf-canvas-wrapper";

  const canvas = document.createElement("canvas");
  canvas.className = "pdf-canvas";
  canvas.width = viewport.width;
  canvas.height = viewport.height;
  canvas.style.width = `${viewport.width}px`;

  wrapper.appendChild(canvas);
  container.appendChild(wrapper);

  const ctx = canvas.getContext("2d")!;
  await page.render({ canvasContext: ctx, viewport }).promise;

  // Update progress bar
  const pct = Math.round((state.currentPage / state.totalPages) * 100);
  const fill = document.getElementById("reader-progress-fill");
  if (fill) fill.style.width = `${pct}%`;
  const text = document.getElementById("reader-progress-text");
  if (text) text.textContent = `${pct}%`;
}

function updatePageInfo(): void {
  const info = document.getElementById("pdf-page-info");
  if (info) info.textContent = `${state.currentPage} / ${state.totalPages}`;
}

async function saveProgress(bookId: number): Promise<void> {
  const now = new Date();
  const pct = state.totalPages > 0 ? (state.currentPage / state.totalPages) * 100 : 0;
  try {
    await progressApi.update(
      bookId,
      String(state.currentPage),
      pct,
      0,
      1, // pages_read per interval
      state.sessionStart.toISOString(),
      now.toISOString()
    );
    state.sessionStart = now;
  } catch {}
}

async function loadPdfJs(): Promise<any> {
  if ((window as any).pdfjsLib) return (window as any).pdfjsLib;
  await loadScript(
    "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"
  );
  return (window as any).pdfjsLib;
}

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${src}"]`);
    if (existing) { resolve(); return; }
    const s = document.createElement("script");
    s.src = src;
    s.onload = () => resolve();
    s.onerror = reject;
    document.head.appendChild(s);
  });
}
