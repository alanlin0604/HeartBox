/**
 * Extract a user-friendly error message from an API error response.
 */
export function getApiErrorMessage(err, fallback = '操作失敗') {
  if (!err?.response?.data) return err?.message || fallback
  const data = err.response.data
  if (typeof data === 'string') return data
  if (data.detail) return data.detail
  if (data.error) return data.error
  // Flatten field errors
  const messages = Object.values(data).flat()
  if (messages.length > 0) return messages.join(', ')
  return fallback
}
