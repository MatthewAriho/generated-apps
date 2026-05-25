import type { Book } from "../api";
import { navigate } from "../router";

export function renderBookCard(book: Book): string {
  const typeBadge = `<span class="badge badge-${book.file_type}">${book.file_type.toUpperCase()}</span>`;

  const pct = book.progress_percentage ?? 0;
  const progress = pct > 0
    ? `<div class="book-progress-bar">
         <div class="book-progress-fill" style="width:${Math.round(pct)}%"></div>
       </div>
       <div class="book-progress-text">${Math.round(pct)}%</div>`
    : "";

  const cover = book.cover_url
    ? `<img class="book-cover" src="${book.cover_url}" alt="${escapeHtml(book.title)}" loading="lazy" />`
    : `<div class="book-cover-placeholder">📖</div>`;

  // "Read" badge with checkmark for finished books
  const statusIcon = book.shelf_status === "read"
    ? `<span class="book-done-badge">✓</span>`
    : "";

  return `
    <div class="book-card" data-book-id="${book.id}">
      <div class="book-cover-wrap">
        ${cover}
        ${statusIcon}
      </div>
      <div class="book-info">
        <div class="book-title">${escapeHtml(book.title)}</div>
        <div class="book-author">${escapeHtml(book.author ?? "Unknown")}</div>
        <div style="display:flex;gap:0.35rem;flex-wrap:wrap;margin-top:auto;padding-top:0.25rem;">
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
