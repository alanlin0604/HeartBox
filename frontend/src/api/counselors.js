import api from './axios'
import { getCached, setCache, invalidate } from './cache'

export const getCounselors = () => {
  const cached = getCached('counselors')
  if (cached) return Promise.resolve(cached)
  return api.get('/counselors/').then(res => {
    setCache('counselors', res, 60_000)
    return res
  })
}

export const applyCounselor = (data) => {
  invalidate('counselors')
  return api.post('/counselors/apply/', data)
}

export const getMyCounselorProfile = () => {
  const cached = getCached('myProfile')
  if (cached) return Promise.resolve(cached)
  return api.get('/counselors/me/').then(res => {
    setCache('myProfile', res, 60_000)
    return res
  })
}

export const updateMyCounselorProfile = (data) => {
  invalidate('myProfile')
  return api.patch('/counselors/me/', data)
}

export const getConversations = () => {
  const cached = getCached('conversations')
  if (cached) return Promise.resolve(cached)
  return api.get('/conversations/').then(res => {
    setCache('conversations', res, 15_000)
    return res
  })
}

export const createConversation = (counselorId) =>
  api.post('/conversations/create/', { counselor_id: counselorId })

export const getMessages = (convId) => api.get(`/conversations/${convId}/messages/`)

export const sendMessage = (convId, content) =>
  api.post(`/conversations/${convId}/messages/`, { content })
