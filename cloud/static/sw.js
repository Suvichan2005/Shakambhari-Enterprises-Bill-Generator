const CACHE_NAME = 'shakambhari-bills-v1';
const STATIC_ASSETS = [
    '/',
    '/manifest.json',
    '/static/icon-192.png',
    '/static/icon-512.png',
    '/static/icon-maskable.png'
];

self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            return cache.addAll(STATIC_ASSETS).catch(err => {
                console.warn('Pre-caching assets warning:', err);
            });
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((keys) => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', (event) => {
    const request = event.request;
    const url = new URL(request.url);

    // API calls and form submissions always use network directly
    if (request.method !== 'GET' || url.pathname.startsWith('/api') || url.pathname.startsWith('/generate') || url.pathname.startsWith('/login') || url.pathname.startsWith('/logout')) {
        return;
    }

    // Static assets (images, icons, manifest): Cache first, fallback to network
    if (url.pathname.startsWith('/static/') || url.pathname === '/manifest.json') {
        event.respondWith(
            caches.match(request).then((cachedResponse) => {
                if (cachedResponse) {
                    return cachedResponse;
                }
                return fetch(request).then((networkResponse) => {
                    if (networkResponse && networkResponse.status === 200) {
                        const responseToCache = networkResponse.clone();
                        caches.open(CACHE_NAME).then((cache) => {
                            cache.put(request, responseToCache);
                        });
                    }
                    return networkResponse;
                });
            })
        );
        return;
    }

    // Navigation requests (HTML): Network first, fallback to cache
    event.respondWith(
        fetch(request)
            .then((networkResponse) => {
                return networkResponse;
            })
            .catch(() => {
                return caches.match(request).then((cachedResponse) => {
                    return cachedResponse || caches.match('/');
                });
            })
    );
});
