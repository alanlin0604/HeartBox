import api from './axios'

export const getWellnessSessions = () =>
  api.get('/wellness-sessions/')

export const createWellnessSession = (data) =>
  api.post('/wellness-sessions/', data)
