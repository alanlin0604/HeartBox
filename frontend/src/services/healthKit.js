/**
 * Health data abstraction layer for Capacitor native health plugins.
 *
 * Supports:
 *  - iOS: HealthKit (via capacitor-apple-health)
 *  - Android: Health Connect (via capacitor-health-connect)
 *
 * Falls back gracefully when running in a browser (PWA mode).
 */

let healthPlugin = null
let platform = 'web'

/**
 * Detect platform and load the appropriate health plugin.
 * Call this once on app startup.
 */
export async function initHealthService() {
  try {
    const { Capacitor } = await import('@capacitor/core')
    platform = Capacitor.getPlatform()

    if (platform === 'ios') {
      const mod = await import('capacitor-apple-health')
      healthPlugin = mod.AppleHealth
    } else if (platform === 'android') {
      const mod = await import('capacitor-health-connect')
      healthPlugin = mod.HealthConnect
    }
  } catch {
    // Running in browser — health features unavailable
    platform = 'web'
    healthPlugin = null
  }
}

/** Check if native health integration is available. */
export function isHealthAvailable() {
  return healthPlugin !== null && platform !== 'web'
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
  if (!healthPlugin) return false

  try {
    if (platform === 'ios') {
      const result = await healthPlugin.requestAuthorization({
        read: [
          'steps', 'heartRate', 'heartRateVariability',
          'activeEnergyBurned', 'appleExerciseTime',
          'sleepAnalysis',
        ],
      })
      return result.granted !== false
    }

    if (platform === 'android') {
      const result = await healthPlugin.requestHealthPermissions({
        read: [
          'Steps', 'HeartRate', 'HeartRateVariabilityRmssd',
          'ActiveCaloriesBurned', 'ExerciseSession',
          'SleepSession',
        ],
      })
      return result.granted !== false
    }
  } catch {
    return false
  }
  return false
}

/**
 * Check if permissions have already been granted.
 */
export async function checkPermissions() {
  if (!healthPlugin) return false

  try {
    if (platform === 'ios') {
      const result = await healthPlugin.isAvailable()
      return result?.available === true
    }
    if (platform === 'android') {
      const result = await healthPlugin.checkHealthPermissions({
        read: ['Steps', 'HeartRate', 'SleepSession'],
      })
      return result.granted !== false
    }
  } catch {
    return false
  }
  return false
}

/**
 * Read health data for a given date range.
 * Returns normalized data regardless of platform.
 */
export async function readHealthData(startDate, endDate) {
  if (!healthPlugin) return { metrics: [], sleep: [] }

  const start = startDate.toISOString()
  const end = endDate.toISOString()
  const metrics = []
  const sleep = []

  try {
    if (platform === 'ios') {
      // Steps
      const steps = await healthPlugin.queryQuantitySamples({
        sampleType: 'steps',
        startDate: start,
        endDate: end,
        aggregation: 'day',
      }).catch(() => ({ data: [] }))

      for (const s of steps.data || []) {
        metrics.push({
          date: s.startDate?.split('T')[0] || s.date,
          metric_type: 'steps',
          value: s.value || s.quantity,
          source: 'apple_health',
        })
      }

      // Heart Rate
      const hr = await healthPlugin.queryQuantitySamples({
        sampleType: 'heartRate',
        startDate: start,
        endDate: end,
        aggregation: 'day',
      }).catch(() => ({ data: [] }))

      for (const h of hr.data || []) {
        metrics.push({
          date: h.startDate?.split('T')[0] || h.date,
          metric_type: 'heart_rate',
          value: h.value || h.quantity,
          source: 'apple_health',
        })
      }

      // HRV
      const hrv = await healthPlugin.queryQuantitySamples({
        sampleType: 'heartRateVariability',
        startDate: start,
        endDate: end,
        aggregation: 'day',
      }).catch(() => ({ data: [] }))

      for (const h of hrv.data || []) {
        metrics.push({
          date: h.startDate?.split('T')[0] || h.date,
          metric_type: 'hrv',
          value: h.value || h.quantity,
          source: 'apple_health',
        })
      }

      // Active Calories
      const cal = await healthPlugin.queryQuantitySamples({
        sampleType: 'activeEnergyBurned',
        startDate: start,
        endDate: end,
        aggregation: 'day',
      }).catch(() => ({ data: [] }))

      for (const c of cal.data || []) {
        metrics.push({
          date: c.startDate?.split('T')[0] || c.date,
          metric_type: 'active_calories',
          value: c.value || c.quantity,
          source: 'apple_health',
        })
      }

      // Exercise Minutes
      const ex = await healthPlugin.queryQuantitySamples({
        sampleType: 'appleExerciseTime',
        startDate: start,
        endDate: end,
        aggregation: 'day',
      }).catch(() => ({ data: [] }))

      for (const e of ex.data || []) {
        metrics.push({
          date: e.startDate?.split('T')[0] || e.date,
          metric_type: 'exercise_minutes',
          value: e.value || e.quantity,
          source: 'apple_health',
        })
      }

      // Sleep
      const sleepData = await healthPlugin.queryCategorySamples({
        sampleType: 'sleepAnalysis',
        startDate: start,
        endDate: end,
      }).catch(() => ({ data: [] }))

      const sleepByDate = groupSleepByDate(sleepData.data || [])
      sleep.push(...sleepByDate)

    } else if (platform === 'android') {
      // Steps
      const steps = await healthPlugin.readRecords({
        type: 'Steps',
        timeRangeFilter: { startTime: start, endTime: end },
      }).catch(() => ({ records: [] }))

      for (const s of steps.records || []) {
        metrics.push({
          date: (s.startTime || s.time)?.split('T')[0],
          metric_type: 'steps',
          value: s.count || s.value,
          source: 'health_connect',
        })
      }

      // Heart Rate
      const hr = await healthPlugin.readRecords({
        type: 'HeartRate',
        timeRangeFilter: { startTime: start, endTime: end },
      }).catch(() => ({ records: [] }))

      // Group HR by date and average
      const hrByDate = {}
      for (const h of hr.records || []) {
        const date = (h.time || h.startTime)?.split('T')[0]
        if (!hrByDate[date]) hrByDate[date] = []
        hrByDate[date].push(h.bpm || h.value)
      }
      for (const [date, values] of Object.entries(hrByDate)) {
        metrics.push({
          date,
          metric_type: 'heart_rate',
          value: Math.round(values.reduce((a, b) => a + b, 0) / values.length),
          source: 'health_connect',
        })
      }

      // Active Calories
      const cal = await healthPlugin.readRecords({
        type: 'ActiveCaloriesBurned',
        timeRangeFilter: { startTime: start, endTime: end },
      }).catch(() => ({ records: [] }))

      for (const c of cal.records || []) {
        metrics.push({
          date: (c.startTime || c.time)?.split('T')[0],
          metric_type: 'active_calories',
          value: c.energy?.inKilocalories || c.value,
          source: 'health_connect',
        })
      }

      // Sleep
      const sleepData = await healthPlugin.readRecords({
        type: 'SleepSession',
        timeRangeFilter: { startTime: start, endTime: end },
      }).catch(() => ({ records: [] }))

      for (const s of sleepData.records || []) {
        const bedtime = s.startTime
        const wakeTime = s.endTime
        const durationMs = new Date(wakeTime) - new Date(bedtime)
        const hours = Math.round((durationMs / 3600000) * 10) / 10

        sleep.push({
          date: bedtime?.split('T')[0],
          sleep_hours: hours,
          sleep_quality: estimateSleepQuality(hours),
          bedtime,
          wake_time: wakeTime,
          source: 'health_connect',
        })
      }
    }
  } catch (err) {
    console.warn('Failed to read health data:', err)
  }

  // Deduplicate metrics by date+type (keep latest)
  const uniqueMetrics = deduplicateMetrics(metrics)

  return { metrics: uniqueMetrics, sleep }
}

/** Group iOS sleep samples into daily sleep records. */
function groupSleepByDate(samples) {
  const byDate = {}
  for (const s of samples) {
    const date = (s.startDate || s.start)?.split('T')[0]
    if (!date) continue
    if (!byDate[date]) {
      byDate[date] = {
        date,
        bedtime: s.startDate || s.start,
        wake_time: s.endDate || s.end,
        deep_sleep_minutes: 0,
        light_sleep_minutes: 0,
        rem_sleep_minutes: 0,
        source: 'apple_health',
      }
    }
    const entry = byDate[date]
    const durationMin = Math.round(
      (new Date(s.endDate || s.end) - new Date(s.startDate || s.start)) / 60000,
    )

    // Apple sleep value: 0=InBed, 1=Asleep, 2=Awake, 3=Core, 4=Deep, 5=REM
    const val = s.value ?? s.category
    if (val === 4) entry.deep_sleep_minutes += durationMin
    else if (val === 5) entry.rem_sleep_minutes += durationMin
    else if (val === 1 || val === 3) entry.light_sleep_minutes += durationMin

    // Extend bedtime/wake_time bounds
    if (s.startDate < entry.bedtime) entry.bedtime = s.startDate
    if ((s.endDate || s.end) > entry.wake_time) entry.wake_time = s.endDate || s.end
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
