import "../styles/reader.css";
import { books as booksApi, type Book } from "../api";
import { navigate } from "../router";
import { renderEpubReader, initEpubReader } from "../components/ReaderEpub";
import { renderPdfReader, initPdfReader } from "../components/ReaderPdf";

export function renderReader(bookId: string): string {
  return `
    <div class="reader-page" id="reader-page" data-book-id="${bookId}">
      <div class="reader-toolbar" id="reader-toolbar">
        <button class="btn btn-ghost btn-sm" id="reader-back">← Library</button>
        <div class="reader-title" id="reader-title">Loading…</div>
        <div class="reader-progress-bar">
          <div class="reader-progress-fill" id="reader-progress-fill" style="width:0%"></div>
        </div>
        <div class="reader-progress-text" id="reader-progress-text">0%</div>
      </div>
      <div class="reader-loading" id="reader-body">
        <div class="spinner"></div>
        <span id="reader-loading-msg">Fetching book info…</span>
        <div id="reader-debug-log" style="
          margin-top:1rem;
          width:90vw;
          max-height:40vh;
          overflow-y:auto;
          background:#111;
          color:#0f0;
          font-family:monospace;
          font-size:11px;
          padding:0.5rem;
          border-radius:6px;
          text-align:left;
          display:none;
        "></div>
      </div>
    </div>
  `;
}

const DEBUG_LOG_ENABLED = false;

function appendDebugLog(msg: string) {
  if (!DEBUG_LOG_ENABLED) return;
  const log = document.getElementById("reader-debug-log");
  if (!log) return;
  log.style.display = "block";
  const line = document.createElement("div");
  line.textContent = `${new Date().toISOString().slice(11,23)} ${msg}`;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

document.addEventListener("page:mounted", async (e: Event) => {
  const route = (e as CustomEvent).detail;
  if (route?.name !== "reader") return;

  const id = Number(route.id);
  if (!id) { navigate("/library"); return; }

  // Full-screen reading mode: hide nav bar (PWA manifest handles true fullscreen)
  document.body.classList.add("reading-mode");

  function exitReading() {
    document.body.classList.remove("reading-mode");
    navigate("/library");
  }

  document.getElementById("reader-back")?.addEventListener("click", exitReading);

  const setLoadingMsg = (msg: string) => {
    const el = document.getElementById("reader-loading-msg");
    if (el) el.textContent = msg;
    appendDebugLog(msg);
    console.log(`[reader] ${msg}`);
  };

  let book: Book;
  try {
    setLoadingMsg("Fetching book info…");
    book = await booksApi.get(id);
    setLoadingMsg(`Got book: "${book.title}" type=${book.file_type}`);
  } catch (e) {
    setLoadingMsg(`ERROR fetching book: ${e}`);
    const body = document.getElementById("reader-body")!;
    body.innerHTML = `
      <div class="reader-error">
        <h3>Book not found</h3>
        <p>This book may have been deleted.</p>
        <button class="btn btn-secondary" onclick="location.hash='/library'">Back to Library</button>
      </div>`;
    return;
  }

  const titleEl = document.getElementById("reader-title");
  if (titleEl) titleEl.textContent = book.title;

  const readerPage = document.getElementById("reader-page")!;

  if (book.file_type === "epub") {
    setLoadingMsg("Mounting epub UI…");
    const div = document.createElement("div");
    div.innerHTML = renderEpubReader(book);
    const loadingDiv = readerPage.querySelector(".reader-loading");
    // Move debug log into new container before removing loading div
    const debugLog = document.getElementById("reader-debug-log");
    if (loadingDiv && debugLog) {
      // Keep debug log visible by moving it to page level
      debugLog.style.position = "fixed";
      debugLog.style.bottom = "60px";
      debugLog.style.left = "5vw";
      debugLog.style.zIndex = "999";
      readerPage.appendChild(debugLog);
      readerPage.removeChild(loadingDiv);
    } else if (loadingDiv) {
      readerPage.removeChild(loadingDiv);
    }
    while (div.firstChild) readerPage.appendChild(div.firstChild);
    setLoadingMsg("Starting epub init…");
    await initEpubReader(book, setLoadingMsg);
    // Hide debug log after success
    const dl = document.getElementById("reader-debug-log");
    if (dl) setTimeout(() => { dl.style.display = "none"; }, 5000);
  } else {
    setLoadingMsg("Mounting PDF UI…");
    const div = document.createElement("div");
    div.innerHTML = renderPdfReader(book);
    const loadingDiv = readerPage.querySelector(".reader-loading");
    if (loadingDiv) readerPage.removeChild(loadingDiv);
    while (div.firstChild) readerPage.appendChild(div.firstChild);
    await initPdfReader(book, setLoadingMsg);
  }

  try {
    if (!book.shelf_status || book.shelf_status === "backlog") {
      await booksApi.updateShelf(id, "reading");
    }
  } catch {}
});
