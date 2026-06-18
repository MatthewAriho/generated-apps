import "./styles/main.css";
import { initRouter, onRoute, navigate } from "./router";
import { isAuthenticated } from "./auth";
import { renderNav, initNav } from "./components/Nav";
import { renderLogin, initLogin } from "./pages/Login";
import { renderHome, initHome, destroyHome } from "./pages/Home";
import { renderEvent, initEvent } from "./pages/Event";
import { renderLeaderboard, initLeaderboard } from "./pages/Leaderboard";
import { renderHistory, initHistory } from "./pages/History";
import { renderSettings, initSettings } from "./pages/Settings";

const app = document.getElementById("app")!;

onRoute((route) => {
  // Cleanup previous page state
  destroyHome();

  // Clear app
  app.innerHTML = "";

  if (route.name === "login") {
    app.innerHTML = renderLogin();
    initLogin();
    return;
  }

  // Authenticated routes get nav + page
  const wrapper = document.createElement("div");
  wrapper.className = "app-wrapper";
  wrapper.innerHTML = renderNav();
  const main = document.createElement("main");
  main.className = "page-content";

  let currentPage = route.name;

  switch (route.name) {
    case "home":
      main.innerHTML = renderHome();
      break;
    case "event":
      main.innerHTML = renderEvent();
      break;
    case "leaderboard":
      main.innerHTML = renderLeaderboard();
      break;
    case "history":
      main.innerHTML = renderHistory();
      break;
    case "settings":
      main.innerHTML = renderSettings();
      break;
    default:
      navigate("/home");
      return;
  }

  wrapper.appendChild(main);
  app.appendChild(wrapper);

  // Init nav highlighting
  initNav(currentPage);

  // Init page-specific JS after DOM insertion
  switch (route.name) {
    case "home":
      initHome();
      break;
    case "event":
      initEvent(route.id);
      break;
    case "leaderboard":
      initLeaderboard();
      break;
    case "history":
      initHistory();
      break;
    case "settings":
      initSettings();
      break;
  }
});

initRouter();

// Register service worker
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
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
    <span>&#127866; Install Taplord as an app</span>
    <button id="pwa-install-btn">Install</button>
    <button id="pwa-install-dismiss">&times;</button>
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
