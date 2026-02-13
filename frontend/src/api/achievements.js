import api from './axios'
import { getCached, setCache, invalidate } from './cache'

const CACHE_KEY = 'achievements'
const CACHE_TTL = 60_000 // 60 seconds

export function getAchievements() {
  const cached = getCached(CACHE_KEY)
  if (cached) return Promise.resolve({ data: cached })
  return api.get('/achievements/').then((res) => {
    setCache(CACHE_KEY, res.data, CACHE_TTL)
    return res
  })
}

export function checkAchievements() {
  invalidate(CACHE_KEY)
  return api.post('/achievements/check/')
}
