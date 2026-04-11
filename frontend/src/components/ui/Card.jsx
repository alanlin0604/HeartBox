/**
 * Modern Glass Card Component with Framer Motion animations
 * Follows HeartBox Design System - Glassmorphism
 */

import { forwardRef } from 'react'
import { motion } from 'framer-motion'

const Card = forwardRef(function Card({
  variant = 'default',
  padding = 'md',
  hover = false,
  animate = true,
  staggerDelay = 0,
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

  // Framer Motion 動畫配置
  const animationConfig = animate ? {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    transition: {
      duration: 0.5,
      delay: staggerDelay,
      ease: [0.25, 0.1, 0.25, 1],
    },
    whileHover: hover ? {
      y: -4,
      transition: { duration: 0.2 },
    } : {},
  } : {}

  return (
    <motion.div
      ref={ref}
      className={`
        ${baseStyles}
        ${variants[variant]}
        ${paddings[padding]}
        ${hoverStyles}
        ${className}
      `.trim().replace(/\s+/g, ' ')}
      {...animationConfig}
      {...props}
    >
      {children}
    </motion.div>
  )
})

export default Card
