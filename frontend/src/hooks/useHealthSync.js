import { useState, useEffect, useCallback, useRef } from 'react'
import {
  initHealthService, isHealthAvailable, requestPermissions,
  checkPermissions, readHealthData, getPlatform, _crumb as crumb,
} from '../services/healthKit'
import { syncHealthData } from '../api/health'

const SYNC_INTERVAL = 30 * 60 * 1000 // 30 minutes
const LAST_SYNC_KEY = 'heartbox_health_last_sync'
const HEALTH_ENABLED_KEY = 'heartbox_health_enabled'

export default function useHealthSync() {
  const [available, setAvailable] = useState(false)
  const [enabled, setEnabled] = useState(() =>
    localStorage.getItem(HEALTH_ENABLED_KEY) === 'true',
  )
  const [syncing, setSyncing] = useState(false)
  const [lastSync, setLastSync] = useState(() =>
    localStorage.getItem(LAST_SYNC_KEY) || null,
  )
  const [platform, setPlatform] = useState('web')
  const intervalRef = useRef(null)

  // Init health service on mount
  useEffect(() => {
    initHealthService().then(() => {
      setAvailable(isHealthAvailable())
      setPlatform(getPlatform())
    })
  }, [])

  // Perform a single sync
  const doSync = useCallback(async () => {
    if (!isHealthAvailable() || syncing) return false
    setSyncing(true)

    try {
      const hasPerms = await checkPermissions()
      if (!hasPerms) {
        setSyncing(false)
        return false
      }

      // Read last 7 days of data
      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 7)

      const data = await readHealthData(start, end)

      if (data.metrics.length > 0 || data.sleep.length > 0) {
        await syncHealthData(data)
      }

      const now = new Date().toISOString()
      localStorage.setItem(LAST_SYNC_KEY, now)
      setLastSync(now)
      return true
    } catch (err) {
      console.warn('Health sync failed:', err)
      return false
    } finally {
      setSyncing(false)
    }
  }, [syncing])

  // Connect: request permissions and start syncing.
  // Breadcrumbs (crumb()) are kept on the hot path so future debugging can
  // re-enable the diagnostic panel by setting `localStorage.heartbox_health_debug = '1'`.
  // The interactive alert() probes used during the paused HC crash hunt are
  // gone — see docs/health-connect-debug-progress.md for the recipe to bring
  // them back if needed.
  const connect = useCallback(async () => {
    crumb('hook:connect:start', { available, platform, isAvailFn: isHealthAvailable() })
    if (!isHealthAvailable()) {
      crumb('hook:connect:not-available-early-return')
      return false
    }

    crumb('hook:connect:before-requestPermissions')
    const granted = await requestPermissions()
    crumb('hook:connect:requestPermissions-returned', granted)
    if (!granted) return false

    localStorage.setItem(HEALTH_ENABLED_KEY, 'true')
    setEnabled(true)

    crumb('hook:connect:before-doSync')
    await doSync()
    crumb('hook:connect:after-doSync')
    return true
  }, [doSync, available, platform])

  // Disconnect: stop syncing
  const disconnect = useCallback(() => {
    localStorage.removeItem(HEALTH_ENABLED_KEY)
    localStorage.removeItem(LAST_SYNC_KEY)
    setEnabled(false)
    setLastSync(null)
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  }, [])

  // Auto-sync on interval when enabled
  useEffect(() => {
    if (enabled && available) {
      // Sync on mount if stale
      const last = localStorage.getItem(LAST_SYNC_KEY)
      if (!last || Date.now() - new Date(last).getTime() > SYNC_INTERVAL) {
        doSync()
      }

      intervalRef.current = setInterval(doSync, SYNC_INTERVAL)
      return () => clearInterval(intervalRef.current)
    }
  }, [enabled, available, doSync])

  return {
    available,
    enabled,
    syncing,
    lastSync,
    platform,
    connect,
    disconnect,
    syncNow: doSync,
  }
}
