import { books as booksApi, type Book, ApiError } from "../api";
import { renderBookCard, attachBookCardListeners } from "../components/BookCard";
import { showToast } from "./toast";

type Shelf = "reading" | "backlog" | "read";

let currentShelf: Shelf = "reading";
let allBooks: Book[] = [];

export function renderLibrary(): string {
  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Library</h1>
        <p class="page-subtitle">Your personal collection</p>
      </div>
      <div style="display:flex;gap:0.75rem;align-items:center">
        <button class="btn btn-primary" id="upload-btn">+ Upload Book</button>
        <input type="file" id="upload-input" accept=".epub,.pdf" style="display:none" />
      </div>
    </div>

    <div class="tabs">
      <button class="tab active" data-shelf="reading">Reading</button>
      <button class="tab" data-shelf="backlog">Backlog</button>
      <button class="tab" data-shelf="read">Read</button>
    </div>

    <div id="upload-progress" style="display:none;margin-bottom:1rem">
      <div style="display:flex;align-items:center;gap:0.75rem;color:var(--muted);font-size:0.875rem">
        <div class="spinner" style="width:20px;height:20px;margin:0"></div>
        Uploading and extracting metadata…
      </div>
    </div>

    <div id="books-container">
      <div class="loading-center"><div class="spinner"></div></div>
    </div>
  `;
}

document.addEventListener("page:mounted", (e: Event) => {
  const route = (e as CustomEvent).detail;
  if (route?.name !== "library") return;
  bootLibrary();
});

async function bootLibrary(): Promise<void> {
  await loadBooks();
  setupTabs();
  setupUpload();
}

async function loadBooks(): Promise<void> {
  try {
    allBooks = await booksApi.list();
    renderShelf(currentShelf);
  } catch (err) {
    const container = document.getElementById("books-container")!;
    container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><h3>Could not load books</h3><p>${err instanceof ApiError ? err.message : "Unknown error"}</p></div>`;
  }
}

function renderShelf(shelf: Shelf): void {
  currentShelf = shelf;
  const container = document.getElementById("books-container");
  if (!container) return;

  const filtered = allBooks.filter((b) => b.shelf_status === shelf);

  if (filtered.length === 0) {
    const labels: Record<Shelf, string> = {
      reading: "You're not currently reading anything",
      backlog: "Your backlog is empty",
      read: "No finished books yet",
    };
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📚</div>
        <h3>${labels[shelf]}</h3>
        <p>Upload a book to get started.</p>
      </div>`;
    return;
  }

  container.innerHTML = `<div class="books-grid">${filtered.map(renderBookCard).join("")}</div>`;
  attachBookCardListeners();
}

function setupTabs(): void {
  document.querySelectorAll("[data-shelf]").forEach((el) => {
    el.addEventListener("click", () => {
      document.querySelectorAll("[data-shelf]").forEach((t) => t.classList.remove("active"));
      el.classList.add("active");
      renderShelf((el as HTMLElement).dataset.shelf as Shelf);
    });
  });
}

function setupUpload(): void {
  const btn = document.getElementById("upload-btn")!;
  const input = document.getElementById("upload-input") as HTMLInputElement;
  const progressEl = document.getElementById("upload-progress")!;

  btn.addEventListener("click", () => input.click());

  input.addEventListener("change", async () => {
    const file = input.files?.[0];
    if (!file) return;

    progressEl.style.display = "";
    btn.setAttribute("disabled", "true");

    try {
      const book = await booksApi.upload(file);
      allBooks.push(book);
      currentShelf = book.shelf_status as Shelf ?? "backlog";

      // Highlight correct tab
      document.querySelectorAll("[data-shelf]").forEach((t) => {
        t.classList.toggle("active", (t as HTMLElement).dataset.shelf === currentShelf);
      });
      renderShelf(currentShelf);
      showToast(`"${book.title}" added to your library`, "success");
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : "Upload failed", "error");
    } finally {
      progressEl.style.display = "none";
      btn.removeAttribute("disabled");
      input.value = "";
    }
  });
}
