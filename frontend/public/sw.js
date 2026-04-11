const CACHE_NAME = 'heartbox-cache-v7'
const STATIC_CACHE = 'heartbox-static-v7'
const IMAGE_CACHE = 'heartbox-images-v7'
const FONT_CACHE = 'heartbox-fonts-v7'

const APP_SHELL = ['/', '/index.html', '/manifest.json', '/offline.html', '/logo.png']
const MAX_IMAGE_CACHE_SIZE = 50
const MAX_STATIC_CACHE_SIZE = 100

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  const currentCaches = [CACHE_NAME, STATIC_CACHE, IMAGE_CACHE, FONT_CACHE]
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((key) => !currentCaches.includes(key)).map((key) => caches.delete(key))
      )
    )
  )
  self.clients.claim()
})

// Cache size limiter
async function trimCache(cacheName, maxItems) {
  const cache = await caches.open(cacheName)
  const keys = await cache.keys()
  if (keys.length > maxItems) {
    await cache.delete(keys[0])
    await trimCache(cacheName, maxItems)
  }
}

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return
  const url = new URL(event.request.url)

  // Skip API, WebSocket, and media requests
  if (url.pathname.includes('/api/') || url.pathname.includes('/ws/') || url.pathname.includes('/media/')) return

  // Navigation requests: network-first to ensure fresh content
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const copy = response.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy))
          return response
        })
        .catch(() => caches.match(event.request).then((c) => c || caches.match('/offline.html')))
    )
    return
  }

  // Fonts: cache-first with long-term caching
  if (url.pathname.match(/\.(woff2?|ttf|eot)$/)) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached
        return fetch(event.request).then((response) => {
          const copy = response.clone()
          caches.open(FONT_CACHE).then((cache) => cache.put(event.request, copy))
          return response
        })
      })
    )
    return
  }

  // Images: cache-first with size limit
  if (url.pathname.match(/\.(png|jpg|jpeg|svg|webp|gif|ico)$/)) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached
        return fetch(event.request).then((response) => {
          if (response && response.status === 200) {
            const copy = response.clone()
            caches.open(IMAGE_CACHE).then(async (cache) => {
              await cache.put(event.request, copy)
              await trimCache(IMAGE_CACHE, MAX_IMAGE_CACHE_SIZE)
            })
          }
          return response
        })
      })
    )
    return
  }

  // Vendor chunks (immutable): cache-first
  if (url.pathname.includes('vendor-') && url.pathname.endsWith('.js')) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached
        return fetch(event.request).then((response) => {
          const copy = response.clone()
          caches.open(STATIC_CACHE).then((cache) => cache.put(event.request, copy))
          return response
        })
      })
    )
    return
  }

  // Other static assets: stale-while-revalidate
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      const fetchPromise = fetch(event.request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200 && networkResponse.type !== 'opaque') {
            const copy = networkResponse.clone()
            caches.open(STATIC_CACHE).then(async (cache) => {
              await cache.put(event.request, copy)
              await trimCache(STATIC_CACHE, MAX_STATIC_CACHE_SIZE)
            })
          }
          return networkResponse
        })
        .catch(() => cachedResponse)

      return cachedResponse || fetchPromise
    })
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
