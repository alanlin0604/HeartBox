import { forwardRef } from 'react'

/**
 * Badge Component
 *
 * 徽章組件，用於顯示狀態、標籤、計數等
 *
 * @param {string} variant - 樣式變體：'default', 'primary', 'success', 'warning', 'danger', 'outline'
 * @param {string} size - 尺寸：'sm', 'md', 'lg'
 * @param {boolean} dot - 是否顯示為圓點
 * @param {boolean} pill - 是否使用完全圓角（藥丸形狀）
 * @param {React.ReactNode} children - 內容
 * @param {string} className - 額外的 CSS 類別
 */
const Badge = forwardRef(({
  variant = 'default',
  size = 'md',
  dot = false,
  pill = false,
  children,
  className = '',
  ...props
}, ref) => {
  // 基礎樣式
  const baseStyles = 'inline-flex items-center justify-center font-medium transition-all'

  // 尺寸樣式
  const sizeStyles = {
    sm: dot ? 'w-1.5 h-1.5' : 'text-xs px-2 py-0.5 min-w-[1.25rem]',
    md: dot ? 'w-2 h-2' : 'text-sm px-2.5 py-0.5 min-w-[1.5rem]',
    lg: dot ? 'w-2.5 h-2.5' : 'text-base px-3 py-1 min-w-[2rem]',
  }

  // 變體樣式
  const variantStyles = {
    default: 'bg-[var(--color-slate-100)] text-[var(--color-slate-700)] dark:bg-[var(--color-slate-800)] dark:text-[var(--color-slate-300)]',
    primary: 'bg-[var(--color-primary-500)]/15 text-[var(--color-primary-600)] dark:bg-[var(--color-primary-500)]/20 dark:text-[var(--color-primary-400)] border border-[var(--color-primary-500)]/20',
    success: 'bg-[var(--color-success-500)]/15 text-[var(--color-success-700)] dark:bg-[var(--color-success-500)]/20 dark:text-[var(--color-success-400)] border border-[var(--color-success-500)]/20',
    warning: 'bg-[var(--color-accent-500)]/15 text-[var(--color-accent-700)] dark:bg-[var(--color-accent-500)]/20 dark:text-[var(--color-accent-300)] border border-[var(--color-accent-500)]/20',
    danger: 'bg-[var(--color-secondary-500)]/15 text-[var(--color-secondary-700)] dark:bg-[var(--color-secondary-500)]/20 dark:text-[var(--color-secondary-400)] border border-[var(--color-secondary-500)]/20',
    outline: 'bg-transparent text-[var(--text-primary)] border border-[var(--border-primary)]',
  }

  // 圓角樣式
  const radiusStyle = dot ? 'rounded-full' : pill ? 'rounded-full' : 'rounded-md'

  const combinedClassName = `
    ${baseStyles}
    ${sizeStyles[size] || sizeStyles.md}
    ${variantStyles[variant] || variantStyles.default}
    ${radiusStyle}
    ${className}
  `.trim().replace(/\s+/g, ' ')

  return (
    <span
      ref={ref}
      className={combinedClassName}
      {...props}
    >
      {!dot && children}
    </span>
  )
})

Badge.displayName = 'Badge'

export default Badge
