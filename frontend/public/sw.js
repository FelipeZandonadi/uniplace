const CACHE = 'uniplace-shell-v2';
self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE);
    const response = await fetch('/index.html');
    if (!response.ok) throw new Error('App shell unavailable');
    const html = await response.clone().text();
    const assets = [...html.matchAll(/(?:src|href)="(\/assets\/[^"?#]+)"/g)].map(match => match[1]);
    await cache.put('/index.html', response);
    await cache.addAll(['/', '/icon.svg', '/manifest.webmanifest', ...assets]);
    await self.skipWaiting();
  })());
});
self.addEventListener('activate', event => { event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key)))).then(() => self.clients.claim())); });
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || ['/api', '/mock-sso', '/media'].some(path => url.pathname === path || url.pathname.startsWith(path + '/'))) return;
  if (event.request.mode === 'navigate') { event.respondWith(fetch(event.request).catch(() => caches.match('/index.html'))); return; }
  event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request)));
});
