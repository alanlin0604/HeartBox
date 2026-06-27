// Validate environment variables BEFORE any other imports
import config from './config/env'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import { LanguageProvider } from './context/LanguageContext'
import { FontScaleProvider } from './context/FontScaleContext'
import { ToastProvider } from './context/ToastContext'
import { CrisisBannerProvider } from './context/CrisisBannerContext'
import { initHealthService } from './services/healthKit'
import './index.css'
import App from './App.jsx'

// Sentry is ~150 KB minified — only download + init when DSN is configured
// and we're in prod. Dynamic import keeps it out of the critical bundle.
const SENTRY_DSN = config.sentryDsn
if (SENTRY_DSN && import.meta.env.PROD) {
  // PII scrubbing: HeartBox URLs encode user-owned IDs (note, chat session,
  // message, post, share token). Strip ID segments AND any query string
  // before the event ships to Sentry so a leaked Sentry token doesn't
  // become a cross-user content index. Layers over maskAllText +
  // blockAllMedia + replaysSessionSampleRate=0 (only errors recorded).
  const scrubUrl = (u) => {
    if (!u || typeof u !== 'string') return u
    try {
      const url = new URL(u, window.location.origin)
      url.search = ''
      url.pathname = url.pathname
        .replace(/\/notes\/\d+/g, '/notes/:id')
        .replace(/\/ai-chat\/sessions\/\d+/g, '/ai-chat/sessions/:id')
        .replace(/\/messages\/\d+/g, '/messages/:id')
        .replace(/\/community\/posts\/\d+/g, '/community/posts/:id')
        .replace(/\/share\/[^/?#]+/g, '/share/:token')
      return url.toString()
    } catch {
      return u.split('?')[0]
    }
  }

  import('@sentry/react').then((Sentry) => {
    Sentry.init({
      dsn: SENTRY_DSN,
      environment: import.meta.env.MODE,
      integrations: [
        Sentry.browserTracingIntegration(),
        Sentry.replayIntegration({
          maskAllText: true,
          blockAllMedia: true,
        }),
      ],
      tracesSampleRate: 0.1,
      // Drop background session recording entirely — for a mental-health
      // app even masked DOM + breadcrumb timing leaks emotional state.
      // Errors still record full context via replaysOnErrorSampleRate.
      replaysSessionSampleRate: 0,
      replaysOnErrorSampleRate: 1.0,
      beforeSend(event) {
        if (event.request?.url) event.request.url = scrubUrl(event.request.url)
        if (event.transaction) event.transaction = scrubUrl(event.transaction)
        return event
      },
      beforeBreadcrumb(crumb) {
        if (crumb?.data?.url) crumb.data.url = scrubUrl(crumb.data.url)
        return crumb
      },
    })
  }).catch(() => { /* Sentry load failure must not break the app */ })
}

// Initialize Capacitor health service (no-op on web)
initHealthService()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <LanguageProvider>
        <ThemeProvider>
          <FontScaleProvider>
            <AuthProvider>
              <ToastProvider>
                <CrisisBannerProvider>
                  <App />
                </CrisisBannerProvider>
              </ToastProvider>
            </AuthProvider>
          </FontScaleProvider>
        </ThemeProvider>
      </LanguageProvider>
    </BrowserRouter>
  </StrictMode>,
)

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker
      .register('/sw.js', { updateViaCache: 'none' })
      .then((reg) => {
        // Defer reload until the user is between actions. Earlier impl
        // reloaded the moment a new SW activated, which clobbered any
        // in-flight click (most visibly: first login attempt after a
        // deploy reloaded the page mid-submit and "ate" the click).
        // Now: wait for the tab to lose then regain visibility, AND
        // make sure no editable input is focused before reloading.
        let activated = false
        reg.addEventListener('updatefound', () => {
          const newSW = reg.installing
          if (!newSW) return
          newSW.addEventListener('statechange', () => {
            if (newSW.state === 'activated' && navigator.serviceWorker.controller) {
              activated = true
            }
          })
        })
        let wentHidden = false
        document.addEventListener('visibilitychange', () => {
          if (document.visibilityState === 'hidden') {
            wentHidden = true
            return
          }
          if (!activated || !wentHidden) return
          const el = document.activeElement
          if (el && el.matches && el.matches('input, textarea, select, [contenteditable="true"]')) {
            return  // user is editing; try again next focus
          }
          activated = false
          wentHidden = false
          window.location.reload()
        })
      })
      .catch(() => {})
  })
}
