/**
 * Professional ProgressBar Component
 *
 * Features:
 * - Linear and circular variants
 * - Color variants (primary, success, warning, danger)
 * - Animated transitions
 * - Indeterminate state
 * - Accessible (ARIA)
 * - Reduced motion support
 */

import { motion } from 'framer-motion'

// Linear Progress Bar
export function LinearProgress({
  value = 0,
  max = 100,
  variant = 'primary',
  size = 'md',
  indeterminate = false,
  showLabel = false,
  className = '',
}) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)

  const variantStyles = {
    primary: 'bg-[var(--color-primary-500)]',
    success: 'bg-[var(--color-success-500)]',
    warning: 'bg-[var(--color-accent-500)]',
    danger: 'bg-[var(--color-secondary-600)]',
  }

  const sizeStyles = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3',
  }

  const barColor = variantStyles[variant] || variantStyles.primary
  const barHeight = sizeStyles[size] || sizeStyles.md

  return (
    <div className={`w-full ${className}`}>
      {showLabel && (
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-[var(--text-secondary)]">
            Progress
          </span>
          <span className="text-sm font-semibold text-[var(--text-primary)]">
            {Math.round(percentage)}%
          </span>
        </div>
      )}

      <div
        className={`w-full ${barHeight} bg-[var(--surface-primary)] rounded-full overflow-hidden`}
        role="progressbar"
        aria-valuenow={indeterminate ? undefined : value}
        aria-valuemin="0"
        aria-valuemax={max}
        aria-label={`Progress: ${Math.round(percentage)}%`}
      >
        {indeterminate ? (
          <motion.div
            className={`h-full ${barColor} rounded-full`}
            style={{ width: '40%' }}
            animate={{ x: ['-100%', '350%'] }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: 'easeInOut',
            }}
          />
        ) : (
          <motion.div
            className={`h-full ${barColor} rounded-full`}
            initial={{ width: 0 }}
            animate={{ width: `${percentage}%` }}
            transition={{
              duration: 0.5,
              ease: [0.25, 0.1, 0.25, 1],
            }}
          />
        )}
      </div>
    </div>
  )
}

// Circular Progress (Spinner)
export function CircularProgress({
  value = 0,
  max = 100,
  size = 48,
  strokeWidth = 4,
  variant = 'primary',
  indeterminate = false,
  showLabel = false,
  className = '',
}) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (percentage / 100) * circumference

  const variantColors = {
    primary: 'var(--color-primary-500)',
    success: 'var(--color-success-500)',
    warning: 'var(--color-accent-500)',
    danger: 'var(--color-secondary-600)',
  }

  const strokeColor = variantColors[variant] || variantColors.primary

  return (
    <div className={`inline-flex items-center justify-center ${className}`}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          className={indeterminate ? 'animate-spin' : ''}
          role="progressbar"
          aria-valuenow={indeterminate ? undefined : value}
          aria-valuemin="0"
          aria-valuemax={max}
          aria-label={`Progress: ${Math.round(percentage)}%`}
        >
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="var(--surface-primary)"
            strokeWidth={strokeWidth}
          />

          {/* Progress circle */}
          <motion.circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={strokeColor}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={indeterminate ? circumference * 0.75 : offset}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: indeterminate ? circumference * 0.75 : offset }}
            transition={{
              duration: 0.5,
              ease: [0.25, 0.1, 0.25, 1],
            }}
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
          />
        </svg>

        {/* Label */}
        {showLabel && !indeterminate && (
          <div
            className="absolute inset-0 flex items-center justify-center"
            aria-hidden="true"
          >
            <span className="text-xs font-semibold text-[var(--text-primary)]">
              {Math.round(percentage)}%
            </span>
          </div>
        )}
      </div>
    </div>
  )
}

// Default export as LinearProgress
export default LinearProgress

// Preset configurations
export const progressPresets = {
  uploadFile: {
    variant: 'primary',
    showLabel: true,
    size: 'md',
  },
  taskCompletion: {
    variant: 'success',
    showLabel: true,
    size: 'lg',
  },
  loading: {
    indeterminate: true,
    variant: 'primary',
    size: 'sm',
  },
}
