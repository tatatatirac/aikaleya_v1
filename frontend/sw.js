const KALEYA_SW_VERSION = 'kaleya-pwa-2026-05-08-02';
const APP_SHELL = [
  '/logo.png',
  '/manifest.webmanifest'
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
