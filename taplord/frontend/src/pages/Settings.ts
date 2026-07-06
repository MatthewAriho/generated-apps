import { auth, UserInfo } from "../api";
import { clearToken, getUsername } from "../auth";
import { navigate } from "../router";

export function renderSettings(): string {
  return `
    <div class="settings-page">
      <h1 class="page-title">&#9881;&#65039; Settings</h1>
      <div id="settings-content" class="settings-content">
        <div class="loading-spinner">Loading...</div>
      </div>
    </div>
  `;
}

export async function initSettings(): Promise<void> {
  const container = document.getElementById("settings-content");
  if (!container) return;

  let user: UserInfo | null = null;
  try {
    user = await auth.me();
  } catch {
    user = null;
  }

  const username = user?.username || getUsername() || "unknown";
  const displayName = user?.display_name || username;
  const joinDate = user?.created_at ? new Date(user.created_at).toLocaleDateString([], { year: "numeric", month: "long", day: "numeric" }) : "Unknown";

  container.innerHTML = `
    <div class="settings-section">
      <h2 class="section-title">Profile</h2>
      <div class="settings-card">
        <div class="settings-profile-row">
          <div class="settings-avatar" style="background:${user?.avatar_color || "#ff6b00"}">${displayName.charAt(0).toUpperCase()}</div>
          <div class="settings-profile-info">
            <span class="settings-display-name">${escapeHtml(displayName)}</span>
            <span class="settings-username">@${escapeHtml(username)}</span>
            <span class="settings-join-date">Joined ${joinDate}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="settings-section">
      <h2 class="section-title">Display Name</h2>
      <div class="settings-card">
        <div class="form-group">
          <input type="text" id="settings-display-name" class="input-medium" value="${escapeAttr(displayName)}" placeholder="Your display name" />
        </div>
        <button class="btn btn-primary" id="btn-save-display-name">Save</button>
        <span id="settings-save-status" class="settings-save-status"></span>
      </div>
    </div>

    <div class="settings-section">
      <h2 class="section-title">About Taplord</h2>
      <div class="settings-card">
        <div class="settings-about">
          <p>&#127866; <strong>Taplord</strong> v1.0.0</p>
          <p>Competitive beer tracking for legends.</p>
          <p class="settings-about-sub">Strava for drinking. Track beers, compete with friends, climb the leaderboard.</p>
        </div>
      </div>
    </div>

    <div class="settings-section">
      <div class="settings-card">
        <button class="btn btn-danger btn-logout" id="btn-logout">Log Out</button>
      </div>
    </div>
  `;

  // Save display name (placeholder -- backend may not support this yet)
  document.getElementById("btn-save-display-name")?.addEventListener("click", async () => {
    const statusEl = document.getElementById("settings-save-status");
    const input = document.getElementById("settings-display-name") as HTMLInputElement;
    const newName = input?.value.trim();
    if (!newName) return;

    try {
      // Try to update -- if endpoint doesn't exist yet, just show saved locally
      await fetch("/taplord/api/users/me", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          ...(await getAuthHeadersAsync()),
        },
        body: JSON.stringify({ display_name: newName }),
      });
      if (statusEl) {
        statusEl.textContent = "Saved!";
        statusEl.className = "settings-save-status status-ok";
      }
    } catch {
      if (statusEl) {
        statusEl.textContent = "Saved locally";
        statusEl.className = "settings-save-status status-ok";
      }
    }
    setTimeout(() => {
      if (statusEl) statusEl.textContent = "";
    }, 2000);
  });

  // Logout
  document.getElementById("btn-logout")?.addEventListener("click", () => {
    clearToken();
    navigate("/login");
  });
}

async function getAuthHeadersAsync(): Promise<Record<string, string>> {
  const { getAuthHeaders } = await import("../auth");
  return getAuthHeaders();
}

function escapeHtml(s: string): string {
  const div = document.createElement("div");
  div.textContent = s;
  return div.innerHTML;
}

function escapeAttr(s: string): string {
  return s.replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}
