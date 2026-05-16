// Validate environment variables BEFORE any other imports
import config from './config/env'

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ThemeProvider } from './context/ThemeContext'
import { LanguageProvider } from './context/LanguageContext'
import { ToastProvider } from './context/ToastContext'
import { initHealthService } from './services/healthKit'
import './index.css'
import App from './App.jsx'

// Sentry is ~150 KB minified — only download + init when DSN is configured
// and we're in prod. Dynamic import keeps it out of the critical bundle.
const SENTRY_DSN = config.sentryDsn
if (SENTRY_DSN && import.meta.env.PROD) {
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
      replaysSessionSampleRate: 0.1,
      replaysOnErrorSampleRate: 1.0,
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
          <AuthProvider>
            <ToastProvider>
              <App />
            </ToastProvider>
          </AuthProvider>
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
        // Auto-update: when new SW is found, activate it and reload
        reg.addEventListener('updatefound', () => {
          const newSW = reg.installing
          if (newSW) {
            newSW.addEventListener('statechange', () => {
              if (newSW.state === 'activated' && navigator.serviceWorker.controller) {
                window.location.reload()
              }
            })
          }
        })
      })
      .catch(() => {})
  })
}
