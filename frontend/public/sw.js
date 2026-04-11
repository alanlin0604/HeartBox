const CACHE_NAME = 'heartbox-cache-v6'
const APP_SHELL = ['/', '/index.html', '/manifest.json', '/offline.html']

// Critical assets to precache (will be populated during build)
const CRITICAL_ASSETS = [
  // Build process should inject actual asset paths here via workbox or custom script
  // For now, we'll cache them on first request via runtime caching below
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      // Cache APP_SHELL immediately
      return cache.addAll(APP_SHELL).catch((err) => {
        console.warn('Failed to cache some APP_SHELL resources:', err)
      })
    })
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))),
    ),
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return
  const url = event.request.url
  if (url.includes('/api/') || url.includes('/ws/') || url.includes('/media/')) return

  // Navigation requests: network-first to ensure fresh content
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const copy = response.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy))
          return response
        })
        .catch(() => caches.match(event.request).then((c) => c || caches.match('/offline.html'))),
    )
    return
  }

  // Static assets: stale-while-revalidate for better perceived performance
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const fetchPromise = fetch(event.request)
        .then((response) => {
          if (!response || response.status !== 200 || response.type === 'opaque') {
            return response
          }
          const copy = response.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy))
          return response
        })
        .catch(() => undefined)

      // Return cached version immediately if available, but update cache in background
      return cached || fetchPromise
    }),
  )
})

// ===== Push Notifications =====
self.addEventListener('push', (event) => {
  const data = event.data?.json() || {}
  const title = data.title || 'HeartBox'
  const options = {
    body: data.body || '',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-192x192.png',
    tag: data.tag || 'default',
    data: { url: data.url || '/' },
  }
  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = event.notification.data?.url || '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      const existing = clients.find((c) => c.url.includes(url))
      if (existing) return existing.focus()
      return self.clients.openWindow(url)
    })
  )
})
