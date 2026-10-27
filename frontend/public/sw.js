/* Only public, non-personal assets are cached. Clerk, API, documents, and app HTML never are. */
const CACHE = "civicpro-public-v2";
const PUBLIC_ASSETS = ["/offline.html", "/icons/icon-192.png", "/icons/icon-512.png", "/icons/maskable-512.png", "/icons/apple-touch-icon.png"];
self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(PUBLIC_ASSETS)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith("civicpro-public-") && key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", event => {
  const { request } = event;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin || request.headers.has("Authorization")) return;
  if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/__clerk") || url.pathname.startsWith("/clerk")) return;
  if (request.mode === "navigate") {
    event.respondWith((async () => {
      const offline = async () => {
        const cache = await caches.open(CACHE);
        return await cache.match("/offline.html") || new Response("CIVICPRO is offline. Reconnect and reload to open your workspace.", { status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" } });
      };
      if (!self.navigator.onLine) return offline();
      try {
        // Never fall back to a browser-cached app document whose scripts may be unavailable.
        return await fetch(request, { cache: "no-store" });
      } catch { return offline(); }
    })());
    return;
  }
  if (PUBLIC_ASSETS.includes(url.pathname) && !url.search) {
    event.respondWith(caches.match(request).then(cached => cached || fetch(request)));
  }
});