import api from './axios'
import { getCached, setCache } from './cache'

/** Batch sync health metrics + sleep data to backend. */
export const syncHealthData = (data) =>
  api.post('/health/sync/', data)

/** Get health metrics list, filterable by type and date range. */
export const getHealthMetrics = (type, from, to) => {
  const params = new URLSearchParams()
  if (type) params.set('type', type)
  if (from) params.set('from', from)
  if (to) params.set('to', to)
  return api.get(`/health/metrics/?${params}`)
}

/** Get health summary with trends and mood correlation. */
export const getHealthSummary = (days = 30) => {
  const key = `health-summary:${days}`
  const cached = getCached(key)
  if (cached) return Promise.resolve(cached)
  return api.get(`/health/summary/?days=${days}`).then(res => {
    setCache(key, res, 60_000)
    return res
  })
}
