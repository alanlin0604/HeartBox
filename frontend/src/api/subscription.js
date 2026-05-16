import api from './axios'
import { getCached, setCache, invalidate } from './cache'

// Plans are static — cache for 5 minutes to avoid re-fetching on every
// page visit / pricing modal open.
export const getPlans = () => {
  const key = 'subscriptions:plans'
  const cached = getCached(key)
  if (cached) return Promise.resolve(cached)
  return api.get('/subscriptions/plans/').then((res) => {
    setCache(key, res, 5 * 60_000)
    return res
  })
}

export const getMySubscription = () => api.get('/subscriptions/me/')

export const subscribe = (planId) => {
  invalidate('subscriptions:')
  return api.post('/subscriptions/me/', { plan: planId })
}
