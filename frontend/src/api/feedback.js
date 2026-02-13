import api from './axios'

export const submitFeedback = (rating, content) =>
  api.post('/feedback/', { rating, content })
