import api from './axios'

export const tagAPI = {
  // Get all user tags
  async list() {
    const res = await api.get('/tags/')
    return res.data
  },

  // Create a new tag
  async create(data) {
    const res = await api.post('/tags/', data)
    return res.data
  },

  // Update a tag
  async update(id, data) {
    const res = await api.patch(`/tags/${id}/`, data)
    return res.data
  },

  // Delete a tag
  async delete(id) {
    await api.delete(`/tags/${id}/`)
  },

  // Get tag cloud with usage counts
  async cloud() {
    const res = await api.get('/tags/cloud/')
    return res.data
  },

  // Autocomplete tags (query param: q)
  async autocomplete(query = '') {
    const res = await api.get('/tags/autocomplete/', {
      params: { q: query },
    })
    return res.data
  },
}
