const CACHE_NAME = "kindling-v3";
const PREFIX = "/kindling";
const PRECACHE = [
  PREFIX + "/",
  PREFIX + "/static/app.js",
  PREFIX + "/static/style.css",
  PREFIX + "/static/icon-192.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // Don't let a single failed precache block install
      return Promise.allSettled(PRECACHE.map((url) => cache.add(url)));
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);

  // API calls and manifest: always network, never cache
  if (url.pathname.includes("/api/") || url.pathname.endsWith("/manifest.json")) {
    e.respondWith(fetch(e.request));
    return;
  }

  // Everything else: stale-while-revalidate
  e.respondWith(
    caches.open(CACHE_NAME).then((cache) =>
      cache.match(e.request).then((cached) => {
        const fetched = fetch(e.request).then((response) => {
          if (response.ok) cache.put(e.request, response.clone());
          return response;
        }).catch(() => cached);
        return cached || fetched;
      })
    )
  );
});
