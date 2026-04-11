/**
 * Modern Glass Card Component
 * Follows HeartBox Design System - Glassmorphism
 */

import { forwardRef } from 'react'

const Card = forwardRef(function Card({
  variant = 'default',
  padding = 'md',
  hover = false,
  children,
  className = '',
  ...props
}, ref) {
  const baseStyles = `
    backdrop-blur-xl
    border rounded-2xl
    transition-all duration-300
  `

  const variants = {
    default: `
      bg-[var(--glass-bg)]
      border-[var(--glass-border)]
      shadow-[var(--glass-shadow)]
    `,
    elevated: `
      bg-[var(--glass-bg-hover)]
      border-[var(--glass-border-hover)]
      shadow-[var(--glass-shadow-lg)]
    `,
    solid: `
      bg-[var(--surface-elevated)]
      border-[var(--border-primary)]
      shadow-md
    `
  }

  const paddings = {
    none: '',
    sm: 'p-3',
    md: 'p-4 sm:p-6',
    lg: 'p-6 sm:p-8'
  }

  const hoverStyles = hover ? `
    hover:bg-[var(--glass-bg-hover)]
    hover:border-[var(--glass-border-hover)]
    hover:shadow-[var(--glass-shadow-lg)]
    hover:-translate-y-1
    cursor-pointer
  ` : ''

  return (
    <div
      ref={ref}
      className={`
        ${baseStyles}
        ${variants[variant]}
        ${paddings[padding]}
        ${hoverStyles}
        ${className}
      `.trim().replace(/\s+/g, ' ')}
      {...props}
    >
      {children}
    </div>
  )
})

export default Card
