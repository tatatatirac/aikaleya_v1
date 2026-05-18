const KALEYA_SW_VERSION = 'kaleya-pwa-2026-05-18-03';
const APP_SHELL = [
  '/logo.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(KALEYA_SW_VERSION).then(cache => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(key => key !== KALEYA_SW_VERSION).map(key => caches.delete(key))
    ))
  );
  self.clients.claim();
});

self.addEventListener('message', event => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;

  // Dynamic per-tenant manifest — always go to network so the logo stays fresh.
  if (url.pathname === '/manifest.webmanifest') {
    event.respondWith(fetch(request, { cache: 'no-store' }).catch(() => new Response('{}', { headers: { 'Content-Type': 'application/manifest+json' } })));
    return;
  }
  // Tenant-uploaded logos under /media/ — network-first, never long-cache.
  if (url.pathname.startsWith('/media/')) {
    event.respondWith(fetch(request).catch(() => caches.match(request)));
    return;
  }

  const isHtmlRequest =
    request.mode === 'navigate' ||
    url.pathname === '/' ||
    url.pathname.endsWith('.html');

  if (isHtmlRequest) {
    event.respondWith(
      fetch(request, { cache: 'no-store' })
        .catch(() => caches.match('/index.html'))
    );
    return;
  }

  event.respondWith(
    fetch(request)
      .then(response => {
        const copy = response.clone();
        if (response.ok) {
          caches.open(KALEYA_SW_VERSION).then(cache => cache.put(request, copy));
        }
        return response;
      })
      .catch(() => caches.match(request))
  );
});
