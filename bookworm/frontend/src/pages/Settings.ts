import { auth, ApiError } from "../api";
import { showToast } from "./toast";
import { analytics as analyticsApi } from "../api";
import { getAuthHeaders } from "../auth";
import { APP_THEMES, getAppTheme, setAppTheme, type AppTheme } from "../theme";

export function renderSettings(): string {
  const currentTheme = getAppTheme();
  const themeButtons = APP_THEMES.map((t) => `
    <button class="theme-swatch${t.id === currentTheme ? " active" : ""}" data-app-theme="${t.id}" title="${t.label}">
      <span class="theme-swatch-color" style="background:${t.preview}"></span>
      <span class="theme-swatch-label">${t.label}</span>
    </button>
  `).join("");

  return `
    <div class="page-header">
      <div>
        <h1 class="page-title">Settings</h1>
        <p class="page-subtitle">Account and preferences</p>
      </div>
    </div>

    <!-- Theme -->
    <div class="settings-section">
      <h3>App Theme</h3>
      <div class="theme-grid" id="theme-grid">
        ${themeButtons}
      </div>
    </div>

    <!-- Integrations -->
    <div class="settings-section">
      <h3>Integrations</h3>
      <div id="integrations-info" style="color:var(--muted);font-size:0.875rem">Loading…</div>
    </div>

    <!-- Change password -->
    <div class="settings-section">
      <h3>Change Password</h3>
      <div class="settings-form" id="password-form">
        <div class="input-group">
          <label class="input-label">Current Password</label>
          <input type="password" class="input" id="current-password" placeholder="••••••••" />
        </div>
        <div class="input-group">
          <label class="input-label">New Password</label>
          <input type="password" class="input" id="new-password" placeholder="••••••••" />
        </div>
        <div class="input-group">
          <label class="input-label">Confirm New Password</label>
          <input type="password" class="input" id="confirm-password" placeholder="••••••••" />
        </div>
        <div id="pw-error" class="form-error" style="display:none"></div>
        <button class="btn btn-primary" id="save-password-btn" style="align-self:flex-start">Update Password</button>
      </div>
    </div>

    <!-- Export -->
    <div class="settings-section">
      <h3>Data Export</h3>
      <p style="font-size:0.875rem;color:var(--muted);margin-bottom:1rem">
        Download your reading data as JSON for backup or analysis.
      </p>
      <button class="btn btn-secondary" id="export-btn">Export Reading Data</button>
    </div>

    <!-- Account info -->
    <div class="settings-section">
      <h3>Account</h3>
      <div id="account-info" style="color:var(--muted);font-size:0.875rem">Loading…</div>
    </div>
  `;
}

document.addEventListener("page:mounted", async (e: Event) => {
  const route = (e as CustomEvent).detail;
  if (route?.name !== "settings") return;
  bootSettings();
});

async function bootSettings(): Promise<void> {
  // Theme picker
  document.querySelectorAll("[data-app-theme]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const theme = (btn as HTMLElement).dataset.appTheme as AppTheme;
      setAppTheme(theme);
      document.querySelectorAll("[data-app-theme]").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      showToast(`Theme: ${APP_THEMES.find((t) => t.id === theme)?.label}`, "success");
    });
  });

  // Load integrations status
  try {
    const resp = await fetch("/bookworm/api/settings/integrations", { headers: getAuthHeaders() });
    const data = await resp.json();
    const el = document.getElementById("integrations-info")!;
    const prowlarrStatus = data.prowlarr_configured
      ? `<span style="color:#4caf50">✓ Connected</span> — ${escapeHtml(data.prowlarr_url)}`
      : `<span style="color:#e94560">✗ Not configured</span> — set PROWLARR_URL and PROWLARR_API_KEY in .env`;
    el.innerHTML = `
      <table style="border-collapse:collapse;font-size:0.875rem;width:100%">
        <tr>
          <td style="padding:0.5rem 1rem 0.5rem 0;color:var(--muted);white-space:nowrap">Prowlarr</td>
          <td style="color:var(--text)">${prowlarrStatus}</td>
        </tr>
        <tr>
          <td style="padding:0.5rem 1rem 0.5rem 0;color:var(--muted);white-space:nowrap">Readarr</td>
          <td style="color:var(--text)"><a href="http://${window.location.hostname}:${data.readarr_port}" target="_blank" style="color:var(--accent)">Open Readarr :${data.readarr_port}</a></td>
        </tr>
        <tr>
          <td style="padding:0.5rem 1rem 0.5rem 0;color:var(--muted);white-space:nowrap">qBittorrent</td>
          <td style="color:var(--text)"><a href="http://${window.location.hostname}:8090" target="_blank" style="color:var(--accent)">Open qBittorrent :8090</a></td>
        </tr>
      </table>
      <p style="font-size:0.75rem;color:var(--muted);margin-top:0.75rem">Integration settings are configured via .env on the server.</p>`;
  } catch {
    const el = document.getElementById("integrations-info");
    if (el) el.textContent = "Could not load integration status.";
  }

  // Load account info
  try {
    const user = await auth.me();
    const el = document.getElementById("account-info")!;
    el.innerHTML = `
      <table style="border-collapse:collapse;font-size:0.875rem">
        <tr><td style="padding:0.4rem 1rem 0.4rem 0;color:var(--muted)">Username</td><td style="color:var(--text)">${escapeHtml(user.username)}</td></tr>
        <tr><td style="padding:0.4rem 1rem 0.4rem 0;color:var(--muted)">Member since</td><td style="color:var(--text)">${new Date(user.created_at).toLocaleDateString()}</td></tr>
      </table>`;
  } catch {}

  // Password change
  document.getElementById("save-password-btn")?.addEventListener("click", () => {
    const current = (document.getElementById("current-password") as HTMLInputElement).value;
    const next = (document.getElementById("new-password") as HTMLInputElement).value;
    const confirm = (document.getElementById("confirm-password") as HTMLInputElement).value;
    const errEl = document.getElementById("pw-error")!;

    errEl.style.display = "none";
    if (!current || !next) { errEl.textContent = "All fields are required"; errEl.style.display = ""; return; }
    if (next !== confirm) { errEl.textContent = "Passwords do not match"; errEl.style.display = ""; return; }
    if (next.length < 3) { errEl.textContent = "Password must be at least 3 characters"; errEl.style.display = ""; return; }

    showToast("Password change not yet implemented", "info");
  });

  // Export
  document.getElementById("export-btn")?.addEventListener("click", async () => {
    const btn = document.getElementById("export-btn") as HTMLButtonElement;
    btn.disabled = true;
    btn.textContent = "Exporting…";
    try {
      const [overview, speed, genres, sessions] = await Promise.all([
        analyticsApi.overview(),
        analyticsApi.speed(),
        analyticsApi.genres(),
        analyticsApi.sessions(),
      ]);
      const payload = { exported_at: new Date().toISOString(), overview, speed, genres, sessions };
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `bookworm-export-${new Date().toISOString().split("T")[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      showToast("Export downloaded", "success");
    } catch {
      showToast("Export failed", "error");
    } finally {
      btn.disabled = false;
      btn.textContent = "Export Reading Data";
    }
  });
}

function escapeHtml(str: string): string {
  if (!str) return "";
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
