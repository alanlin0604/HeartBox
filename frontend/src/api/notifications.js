import api from './axios'
import { getCached, setCache, invalidate } from './cache'

export const getNotifications = (page = 1) => {
  const key = `notifications:${page}`
  const cached = getCached(key)
  if (cached) return Promise.resolve(cached)
  return api.get(`/notifications/?page=${page}`).then(res => {
    setCache(key, res, 30_000)
    return res
  })
}

export const markNotificationsRead = (ids = []) => {
  invalidate('notifications')
  return api.post('/notifications/read/', { ids })
}
