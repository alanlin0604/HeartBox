/**
 * Modern Button Component
 * Follows HeartBox Design System
 */

import { forwardRef } from 'react'

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
  ...props
}, ref) {
  const baseStyles = `
    inline-flex items-center justify-center gap-2
    font-semibold rounded-lg transition-all cursor-pointer
    disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none
    focus-visible:outline-2 focus-visible:outline-offset-2
  `

  const variants = {
    primary: `
      bg-gradient-to-br from-[var(--color-primary-500)] to-[var(--color-primary-400)]
      text-white border-none shadow-sm
      hover:from-[var(--color-primary-400)] hover:to-[#E879F9]
      hover:shadow-md hover:-translate-y-0.5
      active:scale-98 active:shadow-sm
      focus-visible:outline-[var(--color-primary-400)]
    `,
    secondary: `
      bg-[var(--surface-primary)] text-[var(--text-primary)]
      border border-[var(--border-primary)]
      hover:bg-[var(--surface-elevated)] hover:-translate-y-0.5
      active:scale-98
      focus-visible:outline-[var(--color-primary-400)]
    `,
    danger: `
      bg-gradient-to-br from-[var(--color-secondary-600)] to-[var(--color-secondary-700)]
      text-white border-none shadow-sm
      hover:opacity-90 hover:shadow-md hover:-translate-y-0.5
      active:scale-98 active:shadow-sm
      focus-visible:outline-[var(--color-secondary-600)]
    `,
    ghost: `
      bg-transparent text-[var(--text-primary)]
      border border-transparent
      hover:bg-[var(--surface-primary)]
      active:scale-98
      focus-visible:outline-[var(--color-primary-400)]
    `,
    outline: `
      bg-transparent text-[var(--color-primary-500)]
      border border-[var(--color-primary-500)]
      hover:bg-[var(--color-primary-500)] hover:text-white
      active:scale-98
      focus-visible:outline-[var(--color-primary-400)]
    `
  }

  const sizes = {
    sm: 'px-3 py-1.5 text-xs min-h-[36px]',
    md: 'px-6 py-3 text-sm min-h-[44px]',
    lg: 'px-8 py-4 text-base min-h-[52px]'
  }

  const widthClass = fullWidth ? 'w-full' : ''

  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={`
        ${baseStyles}
        ${variants[variant]}
        ${sizes[size]}
        ${widthClass}
        ${className}
      `.trim().replace(/\s+/g, ' ')}
      {...props}
    >
      {loading ? (
        <>
          <span className="btn-spinner" aria-hidden="true" />
          <span>Loading...</span>
        </>
      ) : (
        <>
          {leftIcon && <span className="shrink-0">{leftIcon}</span>}
          {children}
          {rightIcon && <span className="shrink-0">{rightIcon}</span>}
        </>
      )}
    </button>
  )
})

export default Button
