/**
 * Modern Input Component
 * Follows HeartBox Design System
 */

import { forwardRef, useState } from 'react'

const Input = forwardRef(function Input({
  label,
  error,
  helperText,
  leftIcon,
  rightIcon,
  fullWidth = true,
  className = '',
  id,
  required = false,
  ...props
}, ref) {
  const [isFocused, setIsFocused] = useState(false)
  const inputId = id || `input-${Math.random().toString(36).substr(2, 9)}`

  const baseStyles = `
    bg-[var(--input-bg)]
    border rounded-lg
    text-[var(--text-primary)]
    px-4 py-3
    text-base font-normal
    outline-none
    transition-all duration-150
    placeholder:text-[var(--text-muted)]
  `

  const stateStyles = error
    ? 'border-[var(--color-secondary-600)] focus:border-[var(--color-secondary-600)] focus:shadow-[0_0_0_3px_rgba(244,63,94,0.1)]'
    : isFocused
    ? 'border-[var(--color-primary-400)] shadow-[0_0_0_3px_rgba(167,139,250,0.1)]'
    : 'border-[var(--input-border)] hover:border-[var(--border-primary)]'

  const widthClass = fullWidth ? 'w-full' : ''
  const paddingLeft = leftIcon ? 'pl-11' : ''
  const paddingRight = rightIcon ? 'pr-11' : ''

  return (
    <div className={`${fullWidth ? 'w-full' : ''} ${className}`}>
      {label && (
        <label
          htmlFor={inputId}
          className="block text-sm font-medium text-[var(--text-secondary)] mb-2"
        >
          {label}
          {required && <span className="text-[var(--color-secondary-600)] ml-1">*</span>}
        </label>
      )}

      <div className="relative">
        {leftIcon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]">
            {leftIcon}
          </div>
        )}

        <input
          ref={ref}
          id={inputId}
          className={`
            ${baseStyles}
            ${stateStyles}
            ${widthClass}
            ${paddingLeft}
            ${paddingRight}
          `.trim().replace(/\s+/g, ' ')}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          aria-invalid={error ? 'true' : 'false'}
          aria-describedby={
            error ? `${inputId}-error` : helperText ? `${inputId}-helper` : undefined
          }
          {...props}
        />

        {rightIcon && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]">
            {rightIcon}
          </div>
        )}
      </div>

      {error && (
        <p
          id={`${inputId}-error`}
          className="mt-1.5 text-sm text-[var(--color-secondary-600)] flex items-center gap-1"
          role="alert"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          {error}
        </p>
      )}

      {!error && helperText && (
        <p
          id={`${inputId}-helper`}
          className="mt-1.5 text-sm text-[var(--text-tertiary)]"
        >
          {helperText}
        </p>
      )}
    </div>
  )
})

export default Input
