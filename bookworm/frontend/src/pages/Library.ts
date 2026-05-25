import { books as booksApi, type Book, ApiError } from "../api";
import { renderBookCard, attachBookCardListeners } from "../components/BookCard";
import { showToast } from "./toast";

type Shelf = "all" | "reading" | "backlog" | "read";
type SortBy = "recent" | "title" | "author" | "progress";

let currentShelf: Shelf = "all";
let currentSort: SortBy = "recent";
let searchQuery = "";
let allBooks: Book[] = [];

export function renderLibrary(): string {
  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Library</h1>
        <p class="page-subtitle">Your personal collection</p>
      </div>
      <div style="display:flex;gap:0.75rem;align-items:center">
        <button class="btn btn-primary" id="upload-btn">+ Upload</button>
        <input type="file" id="upload-input" accept=".epub,.pdf" style="display:none" multiple />
      </div>
    </div>

    <div class="library-toolbar">
      <input class="input library-search" id="library-search" type="search" placeholder="Search title, author…" />
      <select class="input library-sort" id="library-sort">
        <option value="recent">Recently added</option>
        <option value="title">Title A-Z</option>
        <option value="author">Author A-Z</option>
        <option value="progress">Progress</option>
      </select>
    </div>

    <div class="tabs">
      <button class="tab active" data-shelf="all">All</button>
      <button class="tab" data-shelf="reading">Reading</button>
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

    <!-- Book detail/edit modal -->
    <div class="book-modal-overlay" id="book-modal-overlay">
      <div class="book-modal" id="book-modal"></div>
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
  setupSearch();
  setupSort();
}

async function loadBooks(): Promise<void> {
  try {
    allBooks = await booksApi.list();
    renderShelf();
  } catch (err) {
    const container = document.getElementById("books-container")!;
    container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⚠️</div><h3>Could not load books</h3><p>${err instanceof ApiError ? err.message : "Unknown error"}</p></div>`;
  }
}

function getFilteredBooks(): Book[] {
  let books = [...allBooks];

  // Shelf filter
  if (currentShelf !== "all") {
    books = books.filter((b) => b.shelf_status === currentShelf);
  }

  // Search filter
  if (searchQuery) {
    const q = searchQuery.toLowerCase();
    books = books.filter(
      (b) =>
        b.title.toLowerCase().includes(q) ||
        (b.author ?? "").toLowerCase().includes(q)
    );
  }

  // Sort
  switch (currentSort) {
    case "title":
      books.sort((a, b) => a.title.localeCompare(b.title));
      break;
    case "author":
      books.sort((a, b) => (a.author ?? "").localeCompare(b.author ?? ""));
      break;
    case "progress":
      books.sort((a, b) => (b.progress_percentage ?? 0) - (a.progress_percentage ?? 0));
      break;
    case "recent":
    default:
      books.sort((a, b) => new Date(b.added_at).getTime() - new Date(a.added_at).getTime());
      break;
  }

  return books;
}

function renderShelf(): void {
  const container = document.getElementById("books-container");
  if (!container) return;

  const filtered = getFilteredBooks();

  if (filtered.length === 0) {
    const msg = searchQuery
      ? `No books matching "${escapeHtml(searchQuery)}"`
      : currentShelf === "all"
      ? "Your library is empty"
      : `No books in "${currentShelf}"`;
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📚</div>
        <h3>${msg}</h3>
        <p>Upload a book to get started.</p>
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="library-count">${filtered.length} book${filtered.length !== 1 ? "s" : ""}</div>
    <div class="books-grid">${filtered.map(renderBookCard).join("")}</div>
  `;
  attachBookCardListeners();
  attachLongPressListeners();
}

function setupTabs(): void {
  document.querySelectorAll("[data-shelf]").forEach((el) => {
    el.addEventListener("click", () => {
      document.querySelectorAll("[data-shelf]").forEach((t) => t.classList.remove("active"));
      el.classList.add("active");
      currentShelf = (el as HTMLElement).dataset.shelf as Shelf;
      renderShelf();
    });
  });
}

function setupSearch(): void {
  const input = document.getElementById("library-search") as HTMLInputElement;
  if (!input) return;
  let debounce: ReturnType<typeof setTimeout> | null = null;
  input.addEventListener("input", () => {
    if (debounce) clearTimeout(debounce);
    debounce = setTimeout(() => {
      searchQuery = input.value.trim();
      renderShelf();
    }, 200);
  });
}

function setupSort(): void {
  const select = document.getElementById("library-sort") as HTMLSelectElement;
  if (!select) return;
  select.value = currentSort;
  select.addEventListener("change", () => {
    currentSort = select.value as SortBy;
    renderShelf();
  });
}

function setupUpload(): void {
  const btn = document.getElementById("upload-btn")!;
  const input = document.getElementById("upload-input") as HTMLInputElement;
  const progressEl = document.getElementById("upload-progress")!;

  btn.addEventListener("click", () => input.click());

  input.addEventListener("change", async () => {
    const files = Array.from(input.files ?? []);
    if (!files.length) return;

    progressEl.style.display = "";
    btn.setAttribute("disabled", "true");

    for (const file of files) {
      try {
        const book = await booksApi.upload(file);
        allBooks.push(book);
        showToast(`"${book.title}" added`, "success");
      } catch (err) {
        showToast(`${file.name}: ${err instanceof ApiError ? err.message : "Upload failed"}`, "error");
      }
    }

    progressEl.style.display = "none";
    btn.removeAttribute("disabled");
    input.value = "";
    renderShelf();
  });
}

// ─── Book detail modal (long-press / context menu) ──────────────────────────

function attachLongPressListeners(): void {
  document.querySelectorAll(".book-card[data-book-id]").forEach((el) => {
    let timer: ReturnType<typeof setTimeout> | null = null;
    el.addEventListener("contextmenu", (e) => {
      e.preventDefault();
      openBookModal(Number((el as HTMLElement).dataset.bookId));
    });
    el.addEventListener("touchstart", () => {
      timer = setTimeout(() => openBookModal(Number((el as HTMLElement).dataset.bookId)), 600);
    }, { passive: true });
    el.addEventListener("touchend", () => { if (timer) clearTimeout(timer); });
    el.addEventListener("touchmove", () => { if (timer) clearTimeout(timer); });
  });
}

function openBookModal(bookId: number): void {
  const book = allBooks.find((b) => b.id === bookId);
  if (!book) return;

  const overlay = document.getElementById("book-modal-overlay")!;
  const modal = document.getElementById("book-modal")!;

  modal.innerHTML = `
    <div class="book-modal-header">
      <h3>Edit Book</h3>
      <button class="book-modal-close" id="book-modal-close">&#10005;</button>
    </div>
    <div class="book-modal-body">
      <div class="input-group">
        <label class="input-label">Title</label>
        <input class="input" id="edit-title" value="${escapeAttr(book.title)}" />
      </div>
      <div class="input-group">
        <label class="input-label">Author</label>
        <input class="input" id="edit-author" value="${escapeAttr(book.author ?? "")}" />
      </div>
      <div class="input-group">
        <label class="input-label">Shelf</label>
        <select class="input" id="edit-shelf">
          <option value="backlog" ${book.shelf_status === "backlog" ? "selected" : ""}>Backlog</option>
          <option value="reading" ${book.shelf_status === "reading" ? "selected" : ""}>Reading</option>
          <option value="read" ${book.shelf_status === "read" ? "selected" : ""}>Read</option>
        </select>
      </div>
      <div style="display:flex;gap:0.75rem;margin-top:0.5rem">
        <button class="btn btn-primary" id="edit-save" style="flex:1">Save</button>
        <button class="btn btn-danger" id="edit-delete">Delete</button>
      </div>
    </div>
  `;

  overlay.classList.add("visible");

  document.getElementById("book-modal-close")!.addEventListener("click", closeBookModal);
  overlay.addEventListener("click", (e) => { if (e.target === overlay) closeBookModal(); });

  document.getElementById("edit-save")!.addEventListener("click", async () => {
    const title = (document.getElementById("edit-title") as HTMLInputElement).value.trim();
    const author = (document.getElementById("edit-author") as HTMLInputElement).value.trim();
    const shelf = (document.getElementById("edit-shelf") as HTMLSelectElement).value;

    try {
      // Update metadata
      const updated = await booksApi.update(bookId, { title: title || undefined, author });
      // Update shelf
      const withShelf = await booksApi.updateShelf(bookId, shelf as any);
      // Update local data
      const idx = allBooks.findIndex((b) => b.id === bookId);
      if (idx >= 0) {
        allBooks[idx] = { ...allBooks[idx], ...updated, ...withShelf };
      }
      showToast("Book updated", "success");
      closeBookModal();
      renderShelf();
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : "Update failed", "error");
    }
  });

  document.getElementById("edit-delete")!.addEventListener("click", async () => {
    if (!confirm(`Delete "${book.title}"? This cannot be undone.`)) return;
    try {
      await booksApi.delete(bookId);
      allBooks = allBooks.filter((b) => b.id !== bookId);
      showToast("Book deleted", "success");
      closeBookModal();
      renderShelf();
    } catch (err) {
      showToast(err instanceof ApiError ? err.message : "Delete failed", "error");
    }
  });
}

function closeBookModal(): void {
  document.getElementById("book-modal-overlay")?.classList.remove("visible");
}

function escapeHtml(str: string): string {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function escapeAttr(str: string): string {
  return str.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
