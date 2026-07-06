import "./styles/main.css";
import { initRouter, onRoute, navigate } from "./router";
import { isAuthenticated } from "./auth";
import { renderNav } from "./components/Nav";
import { renderLogin } from "./pages/Login";
import { renderLibrary } from "./pages/Library";
import { renderReader } from "./pages/Reader";
import { renderSearch } from "./pages/Search";
import { renderAnalytics } from "./pages/Analytics";
import { renderSettings } from "./pages/Settings";
import { renderSocial } from "./pages/Social";
import { applyAppTheme } from "./theme";

// Apply saved theme immediately (before render to avoid flash)
applyAppTheme();

const app = document.getElementById("app")!;

function setContent(html: string): void {
  app.innerHTML = html;
}

onRoute((route) => {
  // Clear app
  app.innerHTML = "";

  if (route.name === "login") {
    setContent(renderLogin());
    return;
  }

  // Authenticated routes get nav + page
  const wrapper = document.createElement("div");
  wrapper.className = "app-wrapper";
  wrapper.innerHTML = renderNav();
  const main = document.createElement("main");
  main.className = "page-content";

  switch (route.name) {
    case "library":
      main.innerHTML = renderLibrary();
      break;
    case "reader":
      main.innerHTML = renderReader(route.id);
      break;
    case "search":
      main.innerHTML = renderSearch();
      break;
    case "social":
      main.innerHTML = renderSocial();
      break;
    case "analytics":
      main.innerHTML = renderAnalytics();
      break;
    case "settings":
      main.innerHTML = renderSettings();
      break;
    default:
      navigate("/library");
      return;
  }

  wrapper.appendChild(main);
  app.appendChild(wrapper);

  // Boot page JS after DOM insertion
  const event = new CustomEvent("page:mounted", { detail: route });
  document.dispatchEvent(event);
});

initRouter();

// Register service worker
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/bookworm/sw.js").catch(() => {});
  });
}

// PWA install prompt
let deferredInstallPrompt: any = null;

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredInstallPrompt = e;
  showInstallBanner();
});

function showInstallBanner() {
  if (document.getElementById("pwa-install-banner")) return;
  const banner = document.createElement("div");
  banner.id = "pwa-install-banner";
  banner.innerHTML = `
    <span>Install Bookworm as an app</span>
    <button id="pwa-install-btn">Install</button>
    <button id="pwa-install-dismiss">✕</button>
  `;
  document.body.appendChild(banner);

  document.getElementById("pwa-install-btn")?.addEventListener("click", async () => {
    if (!deferredInstallPrompt) return;
    deferredInstallPrompt.prompt();
    await deferredInstallPrompt.userChoice;
    deferredInstallPrompt = null;
    banner.remove();
  });

  document.getElementById("pwa-install-dismiss")?.addEventListener("click", () => {
    banner.remove();
  });
}

window.addEventListener("appinstalled", () => {
  document.getElementById("pwa-install-banner")?.remove();
  deferredInstallPrompt = null;
});
