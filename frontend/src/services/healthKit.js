/**
 * Health data abstraction layer using @capgo/capacitor-health.
 *
 * Unified API for both:
 *  - iOS: HealthKit
 *  - Android: Health Connect
 *
 * Falls back gracefully when running in a browser (PWA mode).
 */

import { Health } from '@capgo/capacitor-health'
import { Capacitor } from '@capacitor/core'
import { syncHealthData } from '../api/health'

const LAST_SYNC_KEY = 'heartbox_health_last_sync'
const HEALTH_ENABLED_KEY = 'heartbox_health_enabled'
const MIN_SYNC_GAP_MS = 30 * 60 * 1000 // 30 min throttle

// Diagnostic breadcrumb: persists across native crash so we can see where the
// last Health.* call died. Read on app boot via getLastHealthBreadcrumb().
const BREADCRUMB_KEY = 'heartbox_health_breadcrumb'
export function _crumb(stage, payload) { return crumb(stage, payload) }
function crumb(stage, payload) {
  try {
    const entry = { stage, payload, ts: new Date().toISOString() }
    const existing = JSON.parse(localStorage.getItem(BREADCRUMB_KEY) || '[]')
    existing.push(entry)
    // Keep only last 30 entries
    while (existing.length > 30) existing.shift()
    localStorage.setItem(BREADCRUMB_KEY, JSON.stringify(existing))
  } catch { /* ignore */ }
}
export function getLastHealthBreadcrumbs() {
  try { return JSON.parse(localStorage.getItem(BREADCRUMB_KEY) || '[]') }
  catch { return [] }
}
export function clearHealthBreadcrumbs() {
  try { localStorage.removeItem(BREADCRUMB_KEY) } catch { /* ignore */ }
}

let inFlight = null

let platform = 'web'
let isAvailable = false

/**
 * Initialize health service and check availability.
 * Call this once on app startup.
 */
export async function initHealthService() {
  crumb('init:start')
  try {
    platform = Capacitor.getPlatform()
    crumb('init:platform', platform)

    if (platform === 'web') {
      isAvailable = false
      crumb('init:web-skip')
      return
    }

    crumb('init:before-isAvailable')
    const result = await Health.isAvailable()
    crumb('init:isAvailable-returned', result)
    isAvailable = result.available
  } catch (error) {
    crumb('init:error', String(error?.message || error))
    isAvailable = false
  }
}

/** Check if native health integration is available. */
export function isHealthAvailable() {
  return isAvailable && platform !== 'web'
}

/** Get current platform: 'ios' | 'android' | 'web' */
export function getPlatform() {
  return platform
}

/**
 * Request permissions to read health data.
 * Returns true if granted, false otherwise.
 */
export async function requestPermissions() {
  crumb('reqPerms:start', { isAvailable })
  if (!isAvailable) {
    crumb('reqPerms:not-available')
    return false
  }

  // Re-probe right before the heavy call — Health.isAvailable is cheap and
  // catches the case where HC was uninstalled or its provider isn't ready.
  try {
    crumb('reqPerms:before-reprobe')
    const probe = await Health.isAvailable()
    crumb('reqPerms:reprobe-returned', probe)
    if (!probe?.available) {
      isAvailable = false
      return false
    }
  } catch (e) {
    crumb('reqPerms:reprobe-error', String(e?.message || e))
    return false
  }

  // Timeout-wrap the native call. Even with the HealthPlugin.kt patch (see
  // patches/@capgo+capacitor-health+8.4.5.patch) catching coroutine
  // exceptions, some firmware quirks can still leave the bridge in a state
  // where the call never resolves at all (e.g. the permission UI is
  // dismissed by a system overlay). Without a timeout the UI hangs forever.
  const REQ_AUTH_TIMEOUT_MS = 60_000

  try {
    crumb('reqPerms:before-requestAuthorization')
    const result = await Promise.race([
      Health.requestAuthorization({
        read: [
          'steps',
          'heartRate',
          'heartRateVariability',
          'calories',
          'sleep',
        ],
      }),
      new Promise((_, reject) =>
        setTimeout(() => reject(new Error('TIMEOUT: requestAuthorization did not return within 60s')), REQ_AUTH_TIMEOUT_MS),
      ),
    ])
    crumb('reqPerms:requestAuthorization-returned', result)
    if (result.readAuthorized.length > 0) return true

    // Data-based fallback for the HC permission IPC race condition.
    // The plugin's stage-tagged retry loop (4 back-offs, ~3.9s) should normally
    // catch the propagation lag, but on slower Samsung firmware the HC service
    // can still take longer than that to commit the grant set. Ground truth is
    // "can we actually read data?" — try a 1-day Steps read with a tight
    // timeout. If samples come back (even empty array), the permission IS
    // granted, the plugin's getGrantedPermissions just hasn't synced yet, and
    // we should not block the user with a misleading failure toast.
    crumb('reqPerms:fallback-probe-readSamples')
    try {
      const probeEnd = new Date()
      const probeStart = new Date(probeEnd.getTime() - 24 * 60 * 60 * 1000)
      const probe = await Promise.race([
        Health.readSamples({
          dataType: 'steps',
          startDate: probeStart.toISOString(),
          endDate: probeEnd.toISOString(),
          limit: 1,
        }),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('TIMEOUT: probe readSamples > 5s')), 5_000),
        ),
      ])
      // Reaching here means HC accepted the read — permission IS granted
      // regardless of what readAuthorized said. samples may legitimately be
      // empty (user just has no steps recorded), so don't gate on length.
      crumb('reqPerms:fallback-probe-succeeded', { sampleCount: (probe?.samples || []).length })
      return true
    } catch (probeErr) {
      crumb('reqPerms:fallback-probe-failed', String(probeErr?.message || probeErr))
      // Permission really not granted — let the caller surface the failure.
      return false
    }
  } catch (error) {
    // The patch tags the stage in the message ("STAGE_xxx: ExceptionClass: detail").
    // We surface that via the breadcrumb so a future Settings → Health diagnostic
    // page (or Sentry) can read it without needing a debug build.
    crumb('reqPerms:requestAuthorization-error', String(error?.message || error))
    return false
  }
}

/**
 * Check if permissions have already been granted.
 */
export async function checkPermissions() {
  if (!isAvailable) return false

  try {
    const result = await Health.checkAuthorization({
      read: ['steps', 'heartRate', 'sleep'],
    })

    return result.readAuthorized.length > 0
  } catch {
    return false
  }
}

/**
 * Read health data for a given date range.
 * Returns normalized data regardless of platform.
 */
export async function readHealthData(startDate, endDate) {
  if (!isAvailable) return { metrics: [], sleep: [] }

  const start = startDate.toISOString()
  const end = endDate.toISOString()
  const metrics = []
  const sleep = []

  const source = platform === 'ios' ? 'apple_health' : 'health_connect'

  try {
    // Read Steps
    const stepsResult = await Health.readSamples({
      dataType: 'steps',
      startDate: start,
      endDate: end,
      limit: 1000,
    }).catch(() => ({ samples: [] }))

    for (const sample of stepsResult.samples || []) {
      metrics.push({
        date: sample.startDate.split('T')[0],
        metric_type: 'steps',
        value: sample.value,
        source,
      })
    }

    // Read Heart Rate
    const hrResult = await Health.readSamples({
      dataType: 'heartRate',
      startDate: start,
      endDate: end,
      limit: 1000,
    }).catch(() => ({ samples: [] }))

    // Group heart rate by date and average
    const hrByDate = {}
    for (const sample of hrResult.samples || []) {
      const date = sample.startDate.split('T')[0]
      if (!hrByDate[date]) hrByDate[date] = []
      hrByDate[date].push(sample.value)
    }
    for (const [date, values] of Object.entries(hrByDate)) {
      metrics.push({
        date,
        metric_type: 'heart_rate',
        value: Math.round(values.reduce((a, b) => a + b, 0) / values.length),
        source,
      })
    }

    // Read HRV
    const hrvResult = await Health.readSamples({
      dataType: 'heartRateVariability',
      startDate: start,
      endDate: end,
      limit: 1000,
    }).catch(() => ({ samples: [] }))

    // Group HRV by date and average
    const hrvByDate = {}
    for (const sample of hrvResult.samples || []) {
      const date = sample.startDate.split('T')[0]
      if (!hrvByDate[date]) hrvByDate[date] = []
      hrvByDate[date].push(sample.value)
    }
    for (const [date, values] of Object.entries(hrvByDate)) {
      metrics.push({
        date,
        metric_type: 'hrv',
        value: Math.round(values.reduce((a, b) => a + b, 0) / values.length),
        source,
      })
    }

    // Read Active Calories
    const calResult = await Health.readSamples({
      dataType: 'calories',
      startDate: start,
      endDate: end,
      limit: 1000,
    }).catch(() => ({ samples: [] }))

    for (const sample of calResult.samples || []) {
      metrics.push({
        date: sample.startDate.split('T')[0],
        metric_type: 'active_calories',
        value: sample.value,
        source,
      })
    }

    // Read Exercise/Workouts (Android: use workouts API)
    if (platform === 'android') {
      try {
        // Android Health Connect uses workouts instead of exerciseTime
        const workoutsResult = await Health.readWorkouts({
          startDate: start,
          endDate: end,
          limit: 1000,
        }).catch(() => ({ workouts: [] }))

        // Group workouts by date and calculate total exercise time
        const exerciseByDate = {}
        for (const workout of workoutsResult.workouts || []) {
          const date = workout.startDate.split('T')[0]
          const duration = Math.round(
            (new Date(workout.endDate) - new Date(workout.startDate)) / 60000
          )

          if (!exerciseByDate[date]) exerciseByDate[date] = 0
          exerciseByDate[date] += duration
        }

        // Convert to metrics
        for (const [date, totalMinutes] of Object.entries(exerciseByDate)) {
          metrics.push({
            date,
            metric_type: 'exercise_time',
            value: totalMinutes,
            source,
          })
        }
      } catch (err) {
        if (import.meta.env.DEV) {
          console.warn('Failed to read workouts:', err)
        }
      }
    } else if (platform === 'ios') {
      // iOS: try to read exerciseTime directly (if available)
      try {
        const exerciseResult = await Health.readSamples({
          dataType: 'exerciseTime',
          startDate: start,
          endDate: end,
          limit: 1000,
        }).catch(() => ({ samples: [] }))

        for (const sample of exerciseResult.samples || []) {
          metrics.push({
            date: sample.startDate.split('T')[0],
            metric_type: 'exercise_time',
            value: sample.value,
            source,
          })
        }
      } catch (err) {
        if (import.meta.env.DEV) {
          console.warn('Failed to read exercise time:', err)
        }
      }
    }

    // Read Sleep
    const sleepResult = await Health.readSamples({
      dataType: 'sleep',
      startDate: start,
      endDate: end,
      limit: 1000,
    }).catch(() => ({ samples: [] }))

    const sleepByDate = groupSleepByDate(sleepResult.samples || [], source)
    sleep.push(...sleepByDate)

  } catch (err) {
    if (import.meta.env.DEV) {
      console.warn('Failed to read health data:', err)
    }
  }

  // Deduplicate metrics by date+type (keep latest)
  const uniqueMetrics = deduplicateMetrics(metrics)

  return { metrics: uniqueMetrics, sleep }
}

/** Group sleep samples into daily sleep records. */
function groupSleepByDate(samples, source) {
  const byDate = {}

  for (const s of samples) {
    const date = s.startDate.split('T')[0]

    if (!byDate[date]) {
      byDate[date] = {
        date,
        bedtime: s.startDate,
        wake_time: s.endDate,
        deep_sleep_minutes: 0,
        light_sleep_minutes: 0,
        rem_sleep_minutes: 0,
        source,
      }
    }

    const entry = byDate[date]
    const durationMin = Math.round(
      (new Date(s.endDate) - new Date(s.startDate)) / 60000,
    )

    // Map sleep states to sleep stages
    const sleepState = s.sleepState
    if (sleepState === 'deep') {
      entry.deep_sleep_minutes += durationMin
    } else if (sleepState === 'rem') {
      entry.rem_sleep_minutes += durationMin
    } else if (sleepState === 'asleep' || sleepState === 'light') {
      entry.light_sleep_minutes += durationMin
    }

    // Extend bedtime/wake_time bounds
    if (s.startDate < entry.bedtime) entry.bedtime = s.startDate
    if (s.endDate > entry.wake_time) entry.wake_time = s.endDate
  }

  return Object.values(byDate).map((entry) => {
    const hours = Math.round(
      (new Date(entry.wake_time) - new Date(entry.bedtime)) / 3600000 * 10,
    ) / 10
    return {
      ...entry,
      sleep_hours: hours,
      sleep_quality: estimateSleepQuality(hours, entry.deep_sleep_minutes),
    }
  })
}

/** Estimate sleep quality (1-5) from hours and deep sleep. */
function estimateSleepQuality(hours, deepMinutes) {
  let score = 3
  if (hours >= 7 && hours <= 9) score += 1
  else if (hours < 5 || hours > 10) score -= 1
  if (deepMinutes && deepMinutes >= 60) score += 1
  return Math.max(1, Math.min(5, score))
}

/**
 * Run a single end-to-end sync (read last 7 days → POST to backend).
 * Safe to call from anywhere; deduplicates concurrent calls and throttles
 * to MIN_SYNC_GAP_MS unless { force: true }.
 *
 * Returns one of: 'ok' | 'skipped-disabled' | 'skipped-throttle' |
 * 'skipped-no-perms' | 'skipped-unavailable' | 'error'
 */
export async function performHealthSync({ force = false } = {}) {
  if (!isHealthAvailable()) return 'skipped-unavailable'
  if (localStorage.getItem(HEALTH_ENABLED_KEY) !== 'true') return 'skipped-disabled'

  if (!force) {
    const last = localStorage.getItem(LAST_SYNC_KEY)
    if (last && Date.now() - new Date(last).getTime() < MIN_SYNC_GAP_MS) {
      return 'skipped-throttle'
    }
  }

  if (inFlight) return inFlight

  inFlight = (async () => {
    try {
      const hasPerms = await checkPermissions()
      if (!hasPerms) return 'skipped-no-perms'

      const end = new Date()
      const start = new Date()
      start.setDate(start.getDate() - 7)
      const data = await readHealthData(start, end)

      if (data.metrics.length > 0 || data.sleep.length > 0) {
        await syncHealthData(data)
      }
      localStorage.setItem(LAST_SYNC_KEY, new Date().toISOString())
      return 'ok'
    } catch (err) {
      if (import.meta.env.DEV) console.warn('[HealthKit] sync failed:', err)
      return 'error'
    } finally {
      inFlight = null
    }
  })()

  return inFlight
}

/** Remove duplicate metrics, keeping latest per date+type. */
function deduplicateMetrics(metrics) {
  const map = new Map()
  for (const m of metrics) {
    const key = `${m.date}:${m.metric_type}`
    map.set(key, m)
  }
  return Array.from(map.values())
}
