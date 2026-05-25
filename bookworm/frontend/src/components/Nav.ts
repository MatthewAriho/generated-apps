import { clearToken, getUsername } from "../auth";
import { navigate } from "../router";

export function renderNav(): string {
  const username = getUsername() ?? "User";
  const initial = username.charAt(0).toUpperCase();
  const currentHash = window.location.hash.replace(/^#\/?/, "");

  const links = [
    { path: "library",   label: "Library"   },
    { path: "search",    label: "Search"    },
    { path: "analytics", label: "Analytics" },
    { path: "settings",  label: "Settings"  },
  ];

  const linkHtml = links
    .map(({ path, label }) => {
      const active = currentHash === path || (currentHash === "" && path === "library") ? " active" : "";
      return `<button class="nav-link${active}" data-nav="${path}">${label}</button>`;
    })
    .join("");

  return `
    <nav class="nav">
      <div class="nav-logo">
        <span>📚</span> Bookworm
      </div>
      <div class="nav-links">
        ${linkHtml}
      </div>
      <div class="nav-user">
        <div class="nav-avatar">${initial}</div>
        <span>${username}</span>
        <button class="btn-logout" id="nav-logout">Logout</button>
      </div>
    </nav>
  `;
}

// Boot nav event listeners after DOM mount
document.addEventListener("page:mounted", () => {
  document.querySelectorAll("[data-nav]").forEach((el) => {
    el.addEventListener("click", () => {
      const path = (el as HTMLElement).dataset.nav!;
      navigate(`/${path}`);
    });
  });

  document.getElementById("nav-logout")?.addEventListener("click", () => {
    clearToken();
    navigate("/login");
  });
});
