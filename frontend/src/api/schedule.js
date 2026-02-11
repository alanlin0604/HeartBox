import api from './axios'
import { getCached, setCache, invalidate } from './cache'

export const getMySchedule = () => {
  const cached = getCached('schedule')
  if (cached) return Promise.resolve(cached)
  return api.get('/schedule/').then(res => {
    setCache('schedule', res, 30_000)
    return res
  })
}

export const createTimeSlot = (data) => {
  invalidate('schedule')
  return api.post('/schedule/', data)
}

export const deleteTimeSlot = (id) => {
  invalidate('schedule')
  return api.delete('/schedule/', { data: { id } })
}

export const getAvailableSlots = (counselorId, date) =>
  api.get(`/counselors/${counselorId}/available/?date=${date}`)

export const getBookings = () => {
  const cached = getCached('bookings')
  if (cached) return Promise.resolve(cached)
  return api.get('/bookings/').then(res => {
    setCache('bookings', res, 20_000)
    return res
  })
}

export const createBooking = (data) => {
  invalidate('bookings')
  return api.post('/bookings/create/', data)
}

export const bookingAction = (id, action) => {
  invalidate('bookings')
  return api.post(`/bookings/${id}/action/`, { action })
}
