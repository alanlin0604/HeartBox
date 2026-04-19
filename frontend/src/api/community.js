import api from './axios'

/**
 * Community API - Anonymous post sharing and support
 */

/**
 * Get list of public posts with pagination.
 * @param {number} page - Page number (default: 1)
 * @param {number} pageSize - Posts per page (default: 20)
 */
export const getPosts = async (page = 1, pageSize = 20) => {
  const params = new URLSearchParams()
  params.set('page', page)
  params.set('page_size', pageSize)
  return api.get(`/community/posts/?${params}`)
}

/**
 * Create a new anonymous post.
 * @param {string} content - Post content
 * @param {string} category - Optional category
 */
export const createPost = async (content, category = '') => {
  return api.post('/community/posts/', { content, category })
}

/**
 * Get a single post by ID.
 * @param {number} id - Post ID
 */
export const getPost = async (id) => {
  return api.get(`/community/posts/${id}/`)
}

/**
 * Delete own post (soft delete).
 * @param {number} id - Post ID
 */
export const deletePost = async (id) => {
  return api.delete(`/community/posts/${id}/`)
}

/**
 * Give/remove a reaction to a post (toggle).
 * @param {number} postId - Post ID
 * @param {string} reactionType - 'hug', 'support', or 'heart'
 */
export const toggleReaction = async (postId, reactionType) => {
  return api.post(`/community/posts/${postId}/react/`, { reaction_type: reactionType })
}

/**
 * Get current user's own posts.
 */
export const getMyPosts = async () => {
  return api.get('/community/posts/my_posts/')
}

export const communityAPI = {
  getPosts,
  createPost,
  getPost,
  deletePost,
  toggleReaction,
  getMyPosts
}
