import * as Sentry from '@sentry/react'

/**
 * Standardized API error handler
 * Provides consistent error messages and logging across the application
 *
 * @param {Error} error - The error object from axios or fetch
 * @param {Function} t - Translation function from useLang hook
 * @param {Object} toast - Toast object from useToast hook
 * @param {Object} options - Additional options
 * @param {boolean} options.silent - If true, don't show toast (default: false)
 * @param {string} options.fallbackMessage - Custom fallback message
 * @returns {string} The error message that was shown/would be shown
 */
export function handleApiError(error, t, toast, options = {}) {
  const { silent = false, fallbackMessage } = options

  // Network error (no response from server)
  if (!error.response) {
    const message = t?.('errors.network') || 'Network error. Please check your connection.'
    if (!silent && toast) {
      toast.error(message)
    }
    logError(error, 'network')
    return message
  }

  const { status, data } = error.response

  // Build error message based on status code
  let message

  // Try to get error message from response data
  if (data?.detail) {
    message = data.detail
  } else if (data?.message) {
    message = data.message
  } else if (data?.error) {
    message = data.error
  } else {
    // Fallback to standard status code messages
    message = getStatusMessage(status, t) || fallbackMessage || t?.('errors.unknown') || 'An error occurred'
  }

  // Show toast notification
  if (!silent && toast) {
    toast.error(message)
  }

  // Log to Sentry for server errors (500+)
  if (status >= 500) {
    Sentry.captureException(error, {
      level: 'error',
      tags: {
        status_code: status,
        endpoint: error.config?.url,
      },
      extra: {
        response_data: data,
      },
    })
  }

  // Log to console in development
  logError(error, status, message)

  return message
}

/**
 * Get standard error message for HTTP status code
 */
function getStatusMessage(status, t) {
  const statusMap = {
    400: t?.('errors.badRequest') || 'Invalid request',
    401: t?.('errors.unauthorized') || 'Please log in to continue',
    403: t?.('errors.forbidden') || 'Access denied',
    404: t?.('errors.notFound') || 'Resource not found',
    409: t?.('errors.conflict') || 'Conflict - resource already exists',
    422: t?.('errors.validationError') || 'Validation error',
    429: t?.('errors.tooManyRequests') || 'Too many requests - please try again later',
    500: t?.('errors.serverError') || 'Server error - we\'re working on it',
    502: t?.('errors.badGateway') || 'Service temporarily unavailable',
    503: t?.('errors.serviceUnavailable') || 'Service temporarily unavailable',
    504: t?.('errors.gatewayTimeout') || 'Request timeout - please try again',
  }

  return statusMap[status]
}

/**
 * Log error to console in development mode
 */
function logError(error, status, message) {
  if (import.meta.env.DEV) {
    console.group(`🚨 API Error [${status}]`)
    console.error('Message:', message)
    console.error('Error:', error)
    if (error.config) {
      console.error('Request:', {
        method: error.config.method?.toUpperCase(),
        url: error.config.url,
        data: error.config.data,
      })
    }
    if (error.response) {
      console.error('Response:', error.response.data)
    }
    console.groupEnd()
  }
}

/**
 * Extract validation errors from response data
 * Useful for form validation errors
 *
 * @param {Object} data - Response data object
 * @returns {Object} Field-specific error messages
 */
export function extractValidationErrors(data) {
  const errors = {}

  if (data && typeof data === 'object') {
    // Django REST Framework format: { field_name: ["error message"] }
    Object.keys(data).forEach(field => {
      if (Array.isArray(data[field]) && data[field].length > 0) {
        errors[field] = data[field][0]
      } else if (typeof data[field] === 'string') {
        errors[field] = data[field]
      }
    })
  }

  return errors
}

export default handleApiError
