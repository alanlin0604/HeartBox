import api from './axios'
import { getCached, setCache } from './cache'

export const getSleep = (date) => api.get('/sleep/', { params: { date } })

export const saveSleep = (data) => api.post('/sleep/', data)

/**
 * Get comprehensive sleep analysis with statistics, patterns, and issues.
 * @param {number} days - Number of days to analyze (default: 30)
 */
export const getSleepAnalysis = async (days = 30) => {
  const key = `sleep-analysis:${days}`
  const cached = getCached(key)
  if (cached) return cached
  const res = await api.get(`/sleep/analysis/?days=${days}`)
  setCache(key, res, 300_000) // Cache for 5 minutes
  return res
}

/**
 * Get sleep calendar data for a date range.
 * @param {string} startDate - Start date (YYYY-MM-DD)
 * @param {string} endDate - End date (YYYY-MM-DD)
 */
export const getSleepCalendar = async (startDate, endDate) => {
  const params = new URLSearchParams()
  if (startDate) params.set('start_date', startDate)
  if (endDate) params.set('end_date', endDate)
  return api.get(`/sleep/calendar/?${params}`)
}

/**
 * Get sleep trends over time (duration, quality, phases).
 * @param {number} days - Number of days for trend analysis (default: 90)
 */
export const getSleepTrends = async (days = 90) => {
  const key = `sleep-trends:${days}`
  const cached = getCached(key)
  if (cached) return cached
  const res = await api.get(`/sleep/trends/?days=${days}`)
  setCache(key, res, 300_000)
  return res
}

/**
 * Get personalized sleep insights and recommendations.
 */
export const getSleepInsights = async () => {
  const key = 'sleep-insights'
  const cached = getCached(key)
  if (cached) return cached
  const res = await api.get('/sleep/insights/')
  setCache(key, res, 600_000) // Cache for 10 minutes
  return res
}

export const sleepAPI = {
  getAnalysis: getSleepAnalysis,
  getCalendar: getSleepCalendar,
  getTrends: getSleepTrends,
  getInsights: getSleepInsights
}
