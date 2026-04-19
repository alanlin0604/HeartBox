import api from './axios'

export const reviewAPI = {
  // Get notes from previous years on this day
  async getOnThisDay(date = null) {
    const params = date ? { date } : {}
    const res = await api.get('/reviews/on-this-day/', { params })
    return res.data
  },

  // Get monthly review
  async getMonthlyReview(year, month) {
    const res = await api.get('/reviews/monthly/', {
      params: { year, month },
    })
    return res.data
  },

  // Get yearly review
  async getYearlyReview(year) {
    const params = year ? { year } : {}
    const res = await api.get('/reviews/yearly/', { params })
    return res.data
  },
}
