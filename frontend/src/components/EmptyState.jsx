/**
 * Modern EmptyState Component
 * Follows HeartBox Design System - Warm, Guiding, Accessible
 *
 * Features:
 * - Warm gradient background
 * - Clear visual hierarchy
 * - Prominent CTA
 * - Custom icons support
 * - Subtle animation
 */

import { memo } from 'react'
import { motion } from 'framer-motion'
import Button from './ui/Button'

// Default Plus Icon
const PlusIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="48"
    height="48"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <circle cx="12" cy="12" r="10" />
    <path d="M8 12h8" />
    <path d="M12 8v8" />
  </svg>
)

export default memo(function EmptyState({
  title,
  description,
  actionText,
  onAction,
  icon: CustomIcon,
  variant = 'default'
}) {
  // Variant styles for different contexts
  const variants = {
    default: {
      iconBg: 'bg-gradient-to-br from-purple-500/20 to-pink-500/20',
      iconColor: 'text-purple-400',
      titleColor: 'text-[var(--text-primary)]',
      descColor: 'text-[var(--text-secondary)]'
    },
    calm: {
      iconBg: 'bg-gradient-to-br from-blue-500/20 to-cyan-500/20',
      iconColor: 'text-blue-400',
      titleColor: 'text-[var(--text-primary)]',
      descColor: 'text-[var(--text-secondary)]'
    },
    warm: {
      iconBg: 'bg-gradient-to-br from-amber-500/20 to-orange-500/20',
      iconColor: 'text-amber-400',
      titleColor: 'text-[var(--text-primary)]',
      descColor: 'text-[var(--text-secondary)]'
    }
  }

  const style = variants[variant] || variants.default

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
      className="glass-card p-10 sm:p-12 text-center"
      role="status"
      aria-live="polite"
    >
      {/* Icon Container */}
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: 0.1, duration: 0.5, ease: [0.34, 1.56, 0.64, 1] }}
        className={`
          mx-auto w-28 h-28 sm:w-32 sm:h-32 rounded-2xl
          ${style.iconBg}
          flex items-center justify-center
          shadow-lg
          mb-6
        `}
      >
        <div className={style.iconColor}>
          {CustomIcon ? <CustomIcon /> : <PlusIcon />}
        </div>
      </motion.div>

      {/* Text Content */}
      <div className="space-y-3 mb-6">
        <h3 className={`text-xl sm:text-2xl font-semibold ${style.titleColor}`}>
          {title}
        </h3>
        {description && (
          <p className={`text-sm sm:text-base ${style.descColor} max-w-md mx-auto leading-relaxed`}>
            {description}
          </p>
        )}
      </div>

      {/* CTA Button */}
      {actionText && onAction && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.3 }}
        >
          <Button
            onClick={onAction}
            variant="primary"
            size="lg"
            className="min-w-[180px]"
          >
            {actionText}
          </Button>
        </motion.div>
      )}
    </motion.div>
  )
})
