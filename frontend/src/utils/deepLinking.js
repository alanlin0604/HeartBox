/**
 * Deep Linking Utilities
 * Supports app deep links, universal links (iOS), and app links (Android)
 */

import { Capacitor } from '@capacitor/core'

/**
 * Deep link URL schemes
 */
export const DeepLinkScheme = {
  APP: 'heartbox://',
  HTTPS: 'https://heartbox.tw/',
}

/**
 * Generate a deep link URL for a specific route
 * @param {string} path - Route path (e.g., '/notes/123')
 * @param {Object} params - Query parameters
 * @returns {string} Deep link URL
 *
 * @example
 * createDeepLink('/notes/123') → 'heartbox://notes/123'
 * createDeepLink('/dashboard', { tab: 'health' }) → 'heartbox://dashboard?tab=health'
 */
export function createDeepLink(path, params = {}) {
  const cleanPath = path.startsWith('/') ? path.slice(1) : path
  const queryString = new URLSearchParams(params).toString()
  const query = queryString ? `?${queryString}` : ''

  return `${DeepLinkScheme.APP}${cleanPath}${query}`
}

/**
 * Generate a universal link (HTTPS URL that can open the app or web)
 * @param {string} path - Route path
 * @param {Object} params - Query parameters
 * @returns {string} Universal link URL
 */
export function createUniversalLink(path, params = {}) {
  const cleanPath = path.startsWith('/') ? path.slice(1) : path
  const queryString = new URLSearchParams(params).toString()
  const query = queryString ? `?${queryString}` : ''

  return `${DeepLinkScheme.HTTPS}${cleanPath}${query}`
}

/**
 * Parse a deep link URL into route and params
 * @param {string} url - Deep link URL
 * @returns {{ path: string, params: Object }}
 *
 * @example
 * parseDeepLink('heartbox://notes/123?edit=true')
 * → { path: '/notes/123', params: { edit: 'true' } }
 */
export function parseDeepLink(url) {
  try {
    // Remove scheme
    let cleanUrl = url.replace(/^heartbox:\/\//, '').replace(/^https:\/\/heartbox\.tw\//, '')

    // Split path and query
    const [path, queryString] = cleanUrl.split('?')
    const params = {}

    if (queryString) {
      const searchParams = new URLSearchParams(queryString)
      for (const [key, value] of searchParams) {
        params[key] = value
      }
    }

    return {
      path: `/${path}`,
      params,
    }
  } catch (error) {
    console.error('Failed to parse deep link:', url, error)
    return { path: '/', params: {} }
  }
}

/**
 * Initialize deep link listener
 * @param {Function} callback - Callback when deep link is opened: ({ path, params }) => void
 * @returns {Function} Cleanup function to remove listener
 *
 * @example
 * const cleanup = initDeepLinkListener(({ path, params }) => {
 *   navigate(path, { state: params })
 * })
 */
export async function initDeepLinkListener(callback) {
  if (!Capacitor.isNativePlatform()) {
    // Web: use URL parameters
    const urlParams = new URLSearchParams(window.location.search)
    const deepLink = urlParams.get('link')
    if (deepLink) {
      const parsed = parseDeepLink(deepLink)
      callback(parsed)
    }
    return () => {} // No cleanup needed
  }

  try {
    const { App } = await import('@capacitor/app')

    // Handle initial URL (app opened via deep link)
    const initialUrl = await App.getLaunchUrl()
    if (initialUrl?.url) {
      const parsed = parseDeepLink(initialUrl.url)
      callback(parsed)
    }

    // Listen for future deep links (app already open)
    const listener = await App.addListener('appUrlOpen', (data) => {
      const parsed = parseDeepLink(data.url)
      callback(parsed)
    })

    // Return cleanup function
    return () => {
      listener.remove()
    }
  } catch (error) {
    console.error('Failed to initialize deep link listener:', error)
    return () => {}
  }
}

/**
 * Share content with deep link support
 * @param {Object} options
 * @param {string} options.title - Share title
 * @param {string} options.text - Share text
 * @param {string} options.path - App route path
 * @param {Object} options.params - Query parameters
 *
 * @example
 * shareDeepLink({
 *   title: 'Check out this note',
 *   text: 'I found this interesting',
 *   path: '/notes/123'
 * })
 */
export async function shareDeepLink({ title, text, path, params = {} }) {
  const url = createUniversalLink(path, params)

  try {
    if (Capacitor.isNativePlatform()) {
      const { Share } = await import('@capacitor/share')
      await Share.share({
        title,
        text,
        url,
        dialogTitle: title,
      })
    } else if (navigator.share) {
      // Web Share API
      await navigator.share({ title, text, url })
    } else {
      // Fallback: copy to clipboard
      await navigator.clipboard.writeText(url)
      return { copied: true, url }
    }
  } catch (error) {
    console.error('Failed to share deep link:', error)
    throw error
  }
}

/**
 * Common deep link routes for the app
 */
export const DeepLinkRoutes = {
  HOME: '/',
  DASHBOARD: '/dashboard',
  NOTES: '/notes',
  NOTE_DETAIL: (id) => `/notes/${id}`,
  SETTINGS: '/settings',
  SETTINGS_TAB: (tab) => `/settings?tab=${tab}`,
  AI_CHAT: '/ai-chat',
  ASSESSMENTS: '/assessments',
  BREATHE: '/breathe',
  ACHIEVEMENTS: '/achievements',
}

export default {
  createDeepLink,
  createUniversalLink,
  parseDeepLink,
  initDeepLinkListener,
  shareDeepLink,
  DeepLinkRoutes,
}
