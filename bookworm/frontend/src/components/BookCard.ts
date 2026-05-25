import type { Book } from "../api";
import { navigate } from "../router";

export function renderBookCard(book: Book): string {
  const statusBadge = book.shelf_status
    ? `<span class="badge badge-${book.shelf_status}">${book.shelf_status}</span>`
    : "";

  const typeBadge = `<span class="badge badge-${book.file_type}">${book.file_type.toUpperCase()}</span>`;

  const progress =
    book.shelf_status === "reading" && book.progress_percentage != null
      ? `<div class="book-progress-bar">
           <div class="book-progress-fill" style="width:${Math.round(book.progress_percentage)}%"></div>
         </div>`
      : "";

  const cover = book.cover_url
    ? `<img class="book-cover" src="${book.cover_url}" alt="${escapeHtml(book.title)}" loading="lazy" />`
    : `<div class="book-cover-placeholder">📖</div>`;

  return `
    <div class="book-card" data-book-id="${book.id}">
      ${cover}
      <div class="book-info">
        <div class="book-title">${escapeHtml(book.title)}</div>
        <div class="book-author">${escapeHtml(book.author ?? "Unknown")}</div>
        <div style="display:flex;gap:0.35rem;flex-wrap:wrap;margin-top:0.25rem;">
          ${statusBadge}
          ${typeBadge}
        </div>
        ${progress}
      </div>
    </div>
  `;
}

export function attachBookCardListeners(): void {
  document.querySelectorAll(".book-card[data-book-id]").forEach((el) => {
    el.addEventListener("click", () => {
      const id = (el as HTMLElement).dataset.bookId!;
      navigate(`/reader/${id}`);
    });
  });
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
