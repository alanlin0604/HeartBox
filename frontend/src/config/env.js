/**
 * Environment variable validation and configuration
 * This file validates required environment variables at startup
 * to prevent runtime errors from missing configuration.
 */

const requiredEnvVars = [
  'VITE_API_URL',
]

const optionalEnvVars = [
  'VITE_GOOGLE_CLIENT_ID',
  'VITE_VAPID_PUBLIC_KEY',
  'VITE_SENTRY_DSN',
]

// Validate required environment variables
requiredEnvVars.forEach(key => {
  if (!import.meta.env[key]) {
    throw new Error(
      `❌ Missing required environment variable: ${key}\n` +
      `Please check your .env file and ensure all required variables are set.\n` +
      `See .env.example for reference.`
    )
  }
})

// Warn about missing optional environment variables in development
if (import.meta.env.DEV) {
  optionalEnvVars.forEach(key => {
    if (!import.meta.env[key]) {
      console.warn(`⚠️ Optional environment variable not set: ${key}`)
    }
  })
}

// Export validated configuration
export const config = {
  apiUrl: import.meta.env.VITE_API_URL,
  googleClientId: import.meta.env.VITE_GOOGLE_CLIENT_ID || '',
  vapidPublicKey: import.meta.env.VITE_VAPID_PUBLIC_KEY || '',
  sentryDsn: import.meta.env.VITE_SENTRY_DSN || '',
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
  mode: import.meta.env.MODE,
}

// Log configuration in development (without sensitive data)
if (import.meta.env.DEV) {
  console.log('📋 App Configuration:', {
    apiUrl: config.apiUrl,
    mode: config.mode,
    hasGoogleAuth: !!config.googleClientId,
    hasPushNotifications: !!config.vapidPublicKey,
    hasSentry: !!config.sentryDsn,
  })
}

export default config
