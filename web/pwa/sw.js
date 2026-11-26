/**
 * ZONATA Progressive Web App Service Worker (ADR 0054, Rule 84).
 * Implements Cache-First for static assets, Network-First for API with offline cache,
 * and Web Push notification handling.
 */

const CACHE_NAME = 'zonata-pwa-v1';
const STATIC_ASSETS = [
  '/mobile',
  '/manifest.json',
  '/static/css/mobile.css',
  '/static/js/mobile.js',
  '/offline.html'
];

// Install Event: Pre-cache core shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate Event: Cleanup stale caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event: Network-first for dynamic API, cache-first for static shell
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Read-only offline caching for approvals
  if (url.pathname.startsWith('/api/mobile/approvals')) {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const cloned = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, cloned));
          return response;
        })
        .catch(() => {
          return caches.match(event.request).then((cached) => {
            if (cached) return cached;
            return new Response(JSON.stringify({ error: "OFFLINE_MODE", offline: true, items: [] }), {
              headers: { 'Content-Type': 'application/json' }
            });
          });
        })
    );
    return;
  }

  // Static assets cache-first
  event.respondWith(
    caches.match(event.request).then((response) => {
      return response || fetch(event.request);
    })
  );
});

// Push Notification Event (VAPID)
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : { title: 'ZONATA Alert', body: 'New urgent approval pending.' };
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: '/icons/icon-192x192.png',
      badge: '/icons/badge.png',
      data: data.url || '/mobile/approvals'
    })
  );
});
