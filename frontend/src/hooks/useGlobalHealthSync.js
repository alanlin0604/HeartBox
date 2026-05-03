// Global health-data sync lifecycle hook.
//
// Mount this once at the top of the authenticated tree (Layout) and it will:
//   1. Trigger a sync on cold start (post-auth).
//   2. Trigger a sync whenever the Capacitor app comes back to the foreground.
//
// Both are throttled to 30 min by performHealthSync(), so navigating between
// pages or briefly switching apps won't hammer the backend. This is the
// pragmatic stand-in for true Android WorkManager background sync, which
// would require a custom Capacitor plugin (separate undertaking).
import { useEffect } from 'react'
import { App } from '@capacitor/app'
import { performHealthSync } from '../services/healthKit'

export default function useGlobalHealthSync() {
  useEffect(() => {
    // Cold-start sync. Fire-and-forget; performHealthSync handles all the
    // skip/throttle/permission cases internally.
    performHealthSync()

    let removeListener = () => {}
    App.addListener('appStateChange', ({ isActive }) => {
      if (isActive) performHealthSync()
    })
      .then((handle) => { removeListener = () => handle.remove() })
      .catch(() => {}) // No-op on web (App plugin still works but state changes never fire)

    return () => removeListener()
  }, [])
}
