const CACHE_VERSION = "clearspend-v1";
const PREFIX = "/clearspend";
const PRECACHE = [
  PREFIX + "/",
  PREFIX + "/static/app.js",
  PREFIX + "/static/style.css",
  PREFIX + "/static/icon-192.png",
  PREFIX + "/static/icon-512.png",
  PREFIX + "/manifest.json",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => Promise.allSettled(PRECACHE.map((u) => cache.add(u))))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (url.pathname.startsWith(PREFIX + "/api/")) return;
  e.respondWith(
    caches.match(e.request).then((cached) => {
      const fetched = fetch(e.request).then((resp) => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE_VERSION).then((c) => c.put(e.request, clone));
        }
        return resp;
      }).catch(() => cached);
      return cached || fetched;
    })
  );
});
