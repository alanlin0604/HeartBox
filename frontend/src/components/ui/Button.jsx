/**
 * Modern Button Component with Framer Motion animations
 * Follows HeartBox Design System with WCAG 2.1 AA compliance
 *
 * Features:
 * - Touch-friendly (min 44px height)
 * - Loading states with spinner
 * - Accessible focus states
 * - Reduced motion support
 */

import { forwardRef } from 'react'
import { motion } from 'framer-motion'

// Spinner Component
const Spinner = ({ size = 'md' }) => {
  const sizeMap = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-5 h-5'
  }

  return (
    <svg
      className={`animate-spin ${sizeMap[size]}`}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="4"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}

const Button = forwardRef(function Button({
  variant = 'primary',
  size = 'md',
  children,
  loading = false,
  disabled = false,
  fullWidth = false,
  leftIcon,
  rightIcon,
  className = '',
  type = 'button',
  ...props
}, ref) {
  const baseStyles = `
    inline-flex items-center justify-center gap-2
    font-semibold rounded-lg transition-all
    disabled:cursor-not-allowed
    focus-visible:outline-2 focus-visible:outline-offset-2
    touch-manipulation
  `

  const variants = {
    primary: `
      bg-gradient-to-br from-[var(--color-primary-500)] to-[var(--color-primary-400)]
      text-white border-none shadow-sm
      hover:from-[var(--color-primary-400)] hover:to-[var(--color-secondary-400)]
      hover:shadow-md hover:-translate-y-0.5
      active:scale-98 active:shadow-sm
      focus-visible:outline-[var(--color-primary-400)]
      disabled:opacity-60 disabled:from-[var(--color-primary-500)] disabled:to-[var(--color-primary-400)]
      disabled:hover:shadow-sm disabled:hover:translate-y-0
    `,
    secondary: `
      bg-[var(--surface-primary)] text-[var(--text-primary)]
      border border-[var(--border-primary)]
      hover:bg-[var(--surface-elevated)] hover:-translate-y-0.5
      active:scale-98
      focus-visible:outline-[var(--color-primary-400)]
      disabled:opacity-50 disabled:hover:bg-[var(--surface-primary)] disabled:hover:translate-y-0
    `,
    danger: `
      bg-gradient-to-br from-[var(--color-secondary-600)] to-[var(--color-secondary-700)]
      text-white border-none shadow-sm
      hover:opacity-90 hover:shadow-md hover:-translate-y-0.5
      active:scale-98 active:shadow-sm
      focus-visible:outline-[var(--color-secondary-600)]
      disabled:opacity-60 disabled:hover:opacity-60 disabled:hover:translate-y-0
    `,
    ghost: `
      bg-transparent text-[var(--text-primary)]
      border border-transparent
      hover:bg-[var(--surface-primary)]
      active:scale-98
      focus-visible:outline-[var(--color-primary-400)]
      disabled:opacity-50 disabled:hover:bg-transparent
    `,
    outline: `
      bg-transparent text-[var(--color-primary-500)]
      border border-[var(--color-primary-500)]
      hover:bg-[var(--color-primary-500)] hover:text-white
      active:scale-98
      focus-visible:outline-[var(--color-primary-400)]
      disabled:opacity-50 disabled:hover:bg-transparent disabled:hover:text-[var(--color-primary-500)]
    `
  }

  const sizes = {
    sm: 'px-3 py-1.5 text-xs min-h-[36px]',
    md: 'px-6 py-3 text-sm min-h-[44px]',
    lg: 'px-8 py-4 text-base min-h-[52px]'
  }

  const widthClass = fullWidth ? 'w-full' : ''
  const cursorClass = disabled || loading ? 'cursor-not-allowed' : 'cursor-pointer'

  // Framer Motion 動畫配置 (支援 reduced-motion)
  const animationConfig = {
    whileHover: disabled || loading ? {} : {
      scale: 1.02,
      y: -2,
    },
    whileTap: disabled || loading ? {} : {
      scale: 0.98,
    },
    transition: {
      type: 'spring',
      stiffness: 400,
      damping: 17,
      duration: 0.15,
    },
  }

  return (
    <motion.button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading}
      aria-disabled={disabled || loading}
      className={`
        ${baseStyles}
        ${variants[variant]}
        ${sizes[size]}
        ${widthClass}
        ${cursorClass}
        ${className}
      `.trim().replace(/\s+/g, ' ')}
      {...animationConfig}
      {...props}
    >
      {loading ? (
        <>
          <Spinner size={size} />
          <span>{typeof children === 'string' ? children : 'Loading...'}</span>
        </>
      ) : (
        <>
          {leftIcon && <span className="shrink-0" aria-hidden="true">{leftIcon}</span>}
          {children}
          {rightIcon && <span className="shrink-0" aria-hidden="true">{rightIcon}</span>}
        </>
      )}
    </motion.button>
  )
})

export default Button
