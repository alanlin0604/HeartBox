// Lazy-load Google Identity Services (~96 KB) only when an auth page mounts.
// Replaces the eager <script> tag that previously sat in index.html and shipped
// to every visitor — the script is needed by LoginPage and RegisterPage only.

const SRC = 'https://accounts.google.com/gsi/client'
let promise = null

export function loadGsiClient() {
  if (window.google?.accounts?.id) return Promise.resolve()
  if (promise) return promise

  promise = new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[src="${SRC}"]`)
    if (existing) {
      existing.addEventListener('load', () => resolve(), { once: true })
      existing.addEventListener('error', reject, { once: true })
      return
    }
    const script = document.createElement('script')
    script.src = SRC
    script.async = true
    script.defer = true
    script.addEventListener('load', () => resolve(), { once: true })
    script.addEventListener('error', (e) => {
      promise = null // allow retry on next page mount
      reject(e)
    }, { once: true })
    document.head.appendChild(script)
  })

  return promise
}
