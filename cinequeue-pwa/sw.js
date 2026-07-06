const CACHE_VERSION = "cinequeue-v8"; // bump each deploy
const PRECACHE = [
  "/cinequeue/",
  "/cinequeue/static/app.js",
  "/cinequeue/static/style.css",
  "/cinequeue/static/icon-192.png",
  "/cinequeue/static/icon-512.png",
  "/cinequeue/static/icon-192-maskable.png",
  "/cinequeue/static/icon-512-maskable.png",
  "/cinequeue/manifest.json",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(PRECACHE))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k !== CACHE_VERSION)
          .map((k) => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Never cache API traffic so bugs stay visible in the Network tab
self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  // API calls always go to network
  if (url.pathname.startsWith("/cinequeue/api/")) {
    return; // fall through to default browser fetch (network)
  }

  // Everything else: cache-first
  e.respondWith(
    caches.match(e.request).then((cached) => cached || fetch(e.request))
  );
});
