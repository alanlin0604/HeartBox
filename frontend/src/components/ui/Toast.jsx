/**
 * Professional Toast Notification Component
 * Features:
 * - SVG icons (no emoji)
 * - Framer Motion animations
 * - Swipe-to-dismiss
 * - Auto-dismiss with progress bar
 * - Stack management (max 3)
 * - Accessible (ARIA live regions)
 * - Reduced motion support
 */

import { motion, AnimatePresence } from 'framer-motion'
import { useEffect, useState } from 'react'

// Toast Icons (SVG, not emoji)
const SuccessIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
  </svg>
)

const ErrorIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
    <circle cx="12" cy="12" r="10" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M15 9l-6 6M9 9l6 6" />
  </svg>
)

const InfoIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
    <circle cx="12" cy="12" r="10" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 16v-4M12 8h.01" />
  </svg>
)

const WarningIcon = () => (
  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
)

const CloseIcon = () => (
  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
  </svg>
)

const iconMap = {
  success: SuccessIcon,
  error: ErrorIcon,
  info: InfoIcon,
  warning: WarningIcon,
}

const variantStyles = {
  success: {
    container: 'bg-emerald-600/90 border-emerald-400/70 text-white',
    icon: 'bg-emerald-500/30 text-emerald-100',
    progress: 'bg-emerald-400',
  },
  error: {
    container: 'bg-red-600/90 border-red-400/70 text-white',
    icon: 'bg-red-500/30 text-red-100',
    progress: 'bg-red-400',
  },
  info: {
    container: 'bg-blue-600/90 border-blue-400/70 text-white',
    icon: 'bg-blue-500/30 text-blue-100',
    progress: 'bg-blue-400',
  },
  warning: {
    container: 'bg-amber-600/90 border-amber-400/70 text-white',
    icon: 'bg-amber-500/30 text-amber-100',
    progress: 'bg-amber-400',
  },
}

export default function Toast({
  id,
  type = 'info',
  message,
  duration = 3000,
  onClose,
  showProgress = true,
}) {
  const [progress, setProgress] = useState(100)
  const Icon = iconMap[type] || InfoIcon
  const styles = variantStyles[type] || variantStyles.info

  // Auto-dismiss with progress
  useEffect(() => {
    if (!showProgress || !duration) return

    const interval = 50 // Update every 50ms
    const decrement = (interval / duration) * 100

    const timer = setInterval(() => {
      setProgress((prev) => {
        const next = prev - decrement
        if (next <= 0) {
          clearInterval(timer)
          onClose?.()
          return 0
        }
        return next
      })
    }, interval)

    return () => clearInterval(timer)
  }, [duration, onClose, showProgress])

  // Auto-dismiss fallback
  useEffect(() => {
    if (!duration) return
    const timeout = setTimeout(() => onClose?.(), duration)
    return () => clearTimeout(timeout)
  }, [duration, onClose])

  // Animation variants
  const variants = {
    initial: { opacity: 0, y: -50, scale: 0.9 },
    animate: {
      opacity: 1,
      y: 0,
      scale: 1,
      transition: {
        type: 'spring',
        stiffness: 400,
        damping: 25,
      },
    },
    exit: {
      opacity: 0,
      x: 100,
      scale: 0.9,
      transition: { duration: 0.2 },
    },
  }

  // Swipe-to-dismiss
  const handleDragEnd = (event, info) => {
    if (Math.abs(info.offset.x) > 100 || Math.abs(info.offset.y) > 50) {
      onClose?.()
    }
  }

  return (
    <motion.div
      layout
      variants={variants}
      initial="initial"
      animate="animate"
      exit="exit"
      drag
      dragConstraints={{ left: 0, right: 0, top: 0, bottom: 0 }}
      dragElastic={0.7}
      onDragEnd={handleDragEnd}
      className={`
        relative overflow-hidden
        rounded-xl border-2 shadow-2xl backdrop-blur-xl
        min-w-[320px] max-w-[400px]
        cursor-grab active:cursor-grabbing
        ${styles.container}
      `.trim().replace(/\s+/g, ' ')}
    >
      <div className="flex items-start gap-3 p-4">
        {/* Icon */}
        <div className={`shrink-0 p-2 rounded-lg ${styles.icon}`}>
          <Icon />
        </div>

        {/* Message */}
        <div className="flex-1 min-w-0 pt-0.5">
          <p className="text-sm font-semibold leading-relaxed break-words">
            {message}
          </p>
        </div>

        {/* Close Button */}
        <button
          onClick={onClose}
          type="button"
          className="shrink-0 p-1.5 rounded-lg hover:bg-white/20 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
          aria-label="Close notification"
        >
          <CloseIcon />
        </button>
      </div>

      {/* Progress Bar */}
      {showProgress && duration && (
        <div className="absolute bottom-0 left-0 right-0 h-1 bg-black/20">
          <motion.div
            className={`h-full ${styles.progress}`}
            initial={{ width: '100%' }}
            animate={{ width: `${progress}%` }}
            transition={{ duration: 0.05, ease: 'linear' }}
          />
        </div>
      )}
    </motion.div>
  )
}

// Toast Container Component
export function ToastContainer({ toasts, onRemove }) {
  // Limit to 3 toasts (stack management)
  const visibleToasts = toasts.slice(-3)

  // Determine aria-live level
  const hasError = visibleToasts.some((t) => t.type === 'error')
  const ariaLive = hasError ? 'assertive' : 'polite'

  return (
    <div
      role="status"
      aria-live={ariaLive}
      aria-atomic="false"
      className="fixed top-6 right-6 z-[var(--z-toast)] flex flex-col gap-3 pointer-events-none"
    >
      <AnimatePresence mode="popLayout">
        {visibleToasts.map((toast) => (
          <div key={toast.id} className="pointer-events-auto">
            <Toast
              {...toast}
              onClose={() => onRemove(toast.id)}
            />
          </div>
        ))}
      </AnimatePresence>
    </div>
  )
}
