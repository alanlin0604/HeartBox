import api from './axios'

export const reminderAPI = {
  // Get reminder settings
  async getSettings() {
    const res = await api.get('/reminders/settings/')
    return res.data
  },

  // Update reminder settings
  async updateSettings(data) {
    const res = await api.patch('/reminders/settings/', data)
    return res.data
  },

  // Get journal streak
  async getStreak() {
    const res = await api.get('/streaks/')
    return res.data
  },
}
