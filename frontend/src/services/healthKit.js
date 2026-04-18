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

let platform = 'web'
let isAvailable = false

/**
 * Initialize health service and check availability.
 * Call this once on app startup.
 */
export async function initHealthService() {
  try {
    // Get platform (android, ios, or web)
    platform = Capacitor.getPlatform()
    if (import.meta.env.DEV) {
      console.log('[HealthKit] Platform detected:', platform)
    }

    if (platform === 'web') {
      isAvailable = false
      if (import.meta.env.DEV) {
        console.log('[HealthKit] Running in web mode, health features disabled')
      }
      return
    }

    // Check if health plugin is available
    const result = await Health.isAvailable()
    isAvailable = result.available

    if (import.meta.env.DEV) {
      console.log('[HealthKit] Health plugin availability:', result)
      console.log('[HealthKit] isAvailable:', isAvailable)
    }
  } catch (error) {
    // Health plugin not available
    if (import.meta.env.DEV) {
      console.error('[HealthKit] Failed to initialize:', error)
    }
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
  if (!isAvailable) return false

  try {
    const result = await Health.requestAuthorization({
      read: [
        'steps',
        'heartRate',
        'heartRateVariability',
        'calories',
        // Note: 'exerciseTime' not supported on Android Health Connect
        // Use 'workouts' API separately if needed
        'sleep',
      ],
    })

    if (import.meta.env.DEV) {
      console.log('[HealthKit] Authorization result:', result)
    }

    // Check if we got at least some read permissions
    return result.readAuthorized.length > 0
  } catch (error) {
    if (import.meta.env.DEV) {
      console.error('[HealthKit] Authorization failed:', error)
    }
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

    // Note: Exercise Time (exerciseTime) not supported on Android Health Connect
    // TODO: Use workouts API or alternative method to get exercise data

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

/** Remove duplicate metrics, keeping latest per date+type. */
function deduplicateMetrics(metrics) {
  const map = new Map()
  for (const m of metrics) {
    const key = `${m.date}:${m.metric_type}`
    map.set(key, m)
  }
  return Array.from(map.values())
}
