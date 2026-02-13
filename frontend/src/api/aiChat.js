import api from './axios'
import { getCached, setCache, invalidate } from './cache'

const CACHE_KEY = 'ai-chat-sessions'
const CACHE_TTL = 15_000 // 15 seconds

export function getAIChatSessions() {
  const cached = getCached(CACHE_KEY)
  if (cached) return Promise.resolve({ data: cached })
  return api.get('/ai-chat/sessions/').then((res) => {
    setCache(CACHE_KEY, res.data, CACHE_TTL)
    return res
  })
}

export function createAIChatSession() {
  invalidate(CACHE_KEY)
  return api.post('/ai-chat/sessions/')
}

export function getAIChatSession(sessionId) {
  return api.get(`/ai-chat/sessions/${sessionId}/`)
}

export function deleteAIChatSession(sessionId) {
  invalidate(CACHE_KEY)
  return api.delete(`/ai-chat/sessions/${sessionId}/`)
}

export function updateAIChatSession(sessionId, data) {
  invalidate(CACHE_KEY)
  return api.patch(`/ai-chat/sessions/${sessionId}/`, data)
}

export function sendAIChatMessage(sessionId, content) {
  return api.post(`/ai-chat/sessions/${sessionId}/messages/`, { content })
}
