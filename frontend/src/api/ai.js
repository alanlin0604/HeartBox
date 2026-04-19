import api from './axios'

export const aiAPI = {
  // Get AI-powered suggestions (writing prompts, insights, reflection questions)
  async getSuggestions() {
    const res = await api.get('/ai/suggestions/')
    return res.data
  },

  // Get mood and stress predictions
  async getPredictions() {
    const res = await api.get('/ai/predictions/')
    return res.data
  },
}
