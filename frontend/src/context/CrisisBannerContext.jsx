/**
 * Crisis-banner state.
 *
 * Any API call that returns `{crisis_detected: true, hotlines: {...}}` will
 * pass through the axios response interceptor (see api/axios.js) and dispatch
 * `show(hotlines)` here. The banner stays visible until the user dismisses it.
 * We persist the dismissal for 24 h so the user doesn't get badgered after
 * acknowledging it, but a NEW detection always re-surfaces it regardless.
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'

const CrisisBannerContext = createContext(null)
const DISMISS_KEY = 'crisis_banner_dismissed_until'

export function CrisisBannerProvider({ children }) {
  const [hotlines, setHotlines] = useState(null)
  const lastShownAt = useRef(0)

  const show = useCallback((data) => {
    // A fresh server-side detection bypasses local dismissal — if the user
    // typed another crisis-flagged note we always want to surface help.
    try { localStorage.removeItem(DISMISS_KEY) } catch { /* noop */ }
    lastShownAt.current = Date.now()
    setHotlines(data || null)
  }, [])

  const dismiss = useCallback(() => {
    try {
      const until = Date.now() + 24 * 60 * 60 * 1000
      localStorage.setItem(DISMISS_KEY, String(until))
    } catch { /* noop */ }
    setHotlines(null)
  }, [])

  // Expose `show` to the axios interceptor (non-React code).
  useEffect(() => {
    setExternalShow(show)
    return () => setExternalShow(null)
  }, [show])

  const value = useMemo(() => ({ hotlines, show, dismiss }), [hotlines, show, dismiss])
  return <CrisisBannerContext.Provider value={value}>{children}</CrisisBannerContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useCrisisBanner() {
  return useContext(CrisisBannerContext)
}

// Module-level reference set by the provider on mount, so non-React code
// (axios interceptors) can dispatch into the same store without needing
// access to React context. The provider sets this in a useEffect below.
let externalShow = null
// eslint-disable-next-line react-refresh/only-export-components
export function dispatchCrisisShow(hotlines) {
  if (typeof externalShow === 'function') externalShow(hotlines)
}
// eslint-disable-next-line react-refresh/only-export-components
export function setExternalShow(fn) {
  externalShow = fn
}
