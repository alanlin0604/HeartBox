import api from './axios'

export const getSleep = (date) => api.get('/sleep/', { params: { date } })

export const saveSleep = (data) => api.post('/sleep/', data)
