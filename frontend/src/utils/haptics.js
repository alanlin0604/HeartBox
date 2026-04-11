/**
 * Haptic Feedback Utility
 * Provides cross-platform haptic feedback for iOS, Android, and Web
 * Follows Apple HIG and Material Design haptic guidelines
 */

import { Capacitor } from '@capacitor/core'

/**
 * Haptic impact styles following iOS HIG
 * - light: For subtle feedback (toggle, picker)
 * - medium: For moderate feedback (button tap, selection)
 * - heavy: For strong feedback (confirmation, important action)
 */
export const HapticImpactStyle = {
  LIGHT: 'light',
  MEDIUM: 'medium',
  HEAVY: 'heavy',
}

/**
 * Haptic notification types following iOS HIG
 * - success: Positive confirmation (saved, completed)
 * - warning: Caution (validation error, potential issue)
 * - error: Negative outcome (failed action, error state)
 */
export const HapticNotificationType = {
  SUCCESS: 'success',
  WARNING: 'warning',
  ERROR: 'error',
}

// Check if haptics are supported
const isHapticsSupported = () => {
  if (Capacitor.isNativePlatform()) {
    return true
  }
  // Web Vibration API (Android Chrome, some browsers)
  return 'vibrate' in navigator
}

/**
 * Trigger impact haptic feedback
 * @param {string} style - 'light' | 'medium' | 'heavy'
 */
export const impactHaptic = async (style = HapticImpactStyle.MEDIUM) => {
  if (!isHapticsSupported()) return

  try {
    if (Capacitor.isNativePlatform()) {
      const { Haptics, ImpactStyle } = await import('@capacitor/haptics')
      await Haptics.impact({ style: ImpactStyle[style.toUpperCase()] })
    } else {
      // Web fallback - vibration patterns
      const patterns = {
        light: [10],
        medium: [15],
        heavy: [25],
      }
      navigator.vibrate?.(patterns[style] || patterns.medium)
    }
  } catch (error) {
    // Silently fail - haptics are non-critical
    console.debug('Haptic feedback not available:', error)
  }
}

/**
 * Trigger notification haptic feedback
 * @param {string} type - 'success' | 'warning' | 'error'
 */
export const notificationHaptic = async (type = HapticNotificationType.SUCCESS) => {
  if (!isHapticsSupported()) return

  try {
    if (Capacitor.isNativePlatform()) {
      const { Haptics, NotificationType } = await import('@capacitor/haptics')
      await Haptics.notification({ type: NotificationType[type.toUpperCase()] })
    } else {
      // Web fallback - distinctive vibration patterns
      const patterns = {
        success: [10, 50, 10],
        warning: [15, 100, 15],
        error: [25, 50, 25, 50, 25],
      }
      navigator.vibrate?.(patterns[type] || patterns.success)
    }
  } catch (error) {
    console.debug('Haptic feedback not available:', error)
  }
}

/**
 * Trigger selection changed haptic (for pickers, sliders)
 */
export const selectionHaptic = async () => {
  if (!isHapticsSupported()) return

  try {
    if (Capacitor.isNativePlatform()) {
      const { Haptics } = await import('@capacitor/haptics')
      await Haptics.selectionChanged()
    } else {
      navigator.vibrate?.([5])
    }
  } catch (error) {
    console.debug('Haptic feedback not available:', error)
  }
}

/**
 * Trigger vibrate with custom pattern (milliseconds)
 * @param {number | number[]} pattern - Single duration or array [vibrate, pause, vibrate, ...]
 */
export const vibratePattern = async (pattern) => {
  if (!isHapticsSupported()) return

  try {
    if (Capacitor.isNativePlatform()) {
      const { Haptics } = await import('@capacitor/haptics')
      // Use medium impact for custom patterns on native
      await Haptics.impact({ style: 'MEDIUM' })
    } else {
      navigator.vibrate?.(pattern)
    }
  } catch (error) {
    console.debug('Haptic feedback not available:', error)
  }
}

/**
 * Convenience methods for common interactions
 */
export const haptics = {
  // Button taps
  buttonTap: () => impactHaptic(HapticImpactStyle.LIGHT),

  // Toggle switches
  toggle: () => selectionHaptic(),

  // Success feedback (save, submit, complete)
  success: () => notificationHaptic(HapticNotificationType.SUCCESS),

  // Error feedback (validation fail, network error)
  error: () => notificationHaptic(HapticNotificationType.ERROR),

  // Warning feedback (caution, reversible mistake)
  warning: () => notificationHaptic(HapticNotificationType.WARNING),

  // Delete/destructive action
  delete: () => impactHaptic(HapticImpactStyle.HEAVY),

  // Picker/slider selection change
  selection: () => selectionHaptic(),

  // Heavy impact (important confirmation)
  impact: () => impactHaptic(HapticImpactStyle.HEAVY),
}

export default haptics
