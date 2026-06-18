import { getUsername, getUserInitial, clearToken } from "../auth";
import { navigate } from "../router";

export function renderNav(): string {
  const username = getUsername() ?? "user";
  const initial = getUserInitial();

  return `
    <nav class="nav-bar">
      <a href="#/home" class="nav-logo">
        <span class="nav-logo-emoji">&#127866;</span>
        <span class="nav-logo-text">Taplord</span>
      </a>
      <div class="nav-links">
        <a href="#/home" class="nav-link" data-page="home">
          <span class="nav-icon">&#127968;</span>
          <span class="nav-label">Home</span>
        </a>
        <a href="#/leaderboard" class="nav-link" data-page="leaderboard">
          <span class="nav-icon">&#127942;</span>
          <span class="nav-label">Board</span>
        </a>
        <a href="#/history" class="nav-link" data-page="history">
          <span class="nav-icon">&#128197;</span>
          <span class="nav-label">History</span>
        </a>
        <a href="#/settings" class="nav-link" data-page="settings">
          <span class="nav-icon">&#9881;&#65039;</span>
          <span class="nav-label">Settings</span>
        </a>
      </div>
      <div class="nav-user">
        <div class="nav-avatar" title="${username}">${initial}</div>
        <button class="nav-logout-btn" id="nav-logout" title="Log out">&#10140;</button>
      </div>
    </nav>
  `;
}

export function initNav(currentPage: string): void {
  // Highlight active link
  document.querySelectorAll(".nav-link").forEach((link) => {
    const page = link.getAttribute("data-page");
    if (page === currentPage) {
      link.classList.add("active");
    }
  });

  // Logout handler
  document.getElementById("nav-logout")?.addEventListener("click", () => {
    clearToken();
    navigate("/login");
  });
}
