import { useState, useRef, useEffect } from 'react'

/**
 * Tooltip Component
 *
 * 提示框組件，滑鼠懸停時顯示提示信息
 *
 * @param {React.ReactNode} children - 觸發元素
 * @param {string} content - 提示內容
 * @param {string} position - 位置：'top', 'bottom', 'left', 'right'
 * @param {number} delay - 延遲顯示時間（毫秒）
 * @param {string} className - 額外的 CSS 類別
 */
export default function Tooltip({
  children,
  content,
  position = 'top',
  delay = 200,
  className = '',
}) {
  const [isVisible, setIsVisible] = useState(false)
  const [coords, setCoords] = useState({ top: 0, left: 0 })
  const triggerRef = useRef(null)
  const tooltipRef = useRef(null)
  const timeoutRef = useRef(null)

  useEffect(() => {
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [])

  const handleMouseEnter = () => {
    timeoutRef.current = setTimeout(() => {
      setIsVisible(true)
      updatePosition()
    }, delay)
  }

  const handleMouseLeave = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    setIsVisible(false)
  }

  const updatePosition = () => {
    if (!triggerRef.current || !tooltipRef.current) return

    const triggerRect = triggerRef.current.getBoundingClientRect()
    const tooltipRect = tooltipRef.current.getBoundingClientRect()

    let top = 0
    let left = 0

    switch (position) {
      case 'top':
        top = triggerRect.top - tooltipRect.height - 8
        left = triggerRect.left + (triggerRect.width - tooltipRect.width) / 2
        break
      case 'bottom':
        top = triggerRect.bottom + 8
        left = triggerRect.left + (triggerRect.width - tooltipRect.width) / 2
        break
      case 'left':
        top = triggerRect.top + (triggerRect.height - tooltipRect.height) / 2
        left = triggerRect.left - tooltipRect.width - 8
        break
      case 'right':
        top = triggerRect.top + (triggerRect.height - tooltipRect.height) / 2
        left = triggerRect.right + 8
        break
      default:
        break
    }

    setCoords({ top, left })
  }

  // 位置箭頭樣式
  const getArrowStyle = () => {
    const arrowBase = 'absolute w-2 h-2 bg-[var(--tooltip-bg)] border-[var(--tooltip-border)] transform rotate-45'
    switch (position) {
      case 'top':
        return `${arrowBase} bottom-[-4px] left-1/2 -translate-x-1/2 border-b border-r`
      case 'bottom':
        return `${arrowBase} top-[-4px] left-1/2 -translate-x-1/2 border-t border-l`
      case 'left':
        return `${arrowBase} right-[-4px] top-1/2 -translate-y-1/2 border-r border-t`
      case 'right':
        return `${arrowBase} left-[-4px] top-1/2 -translate-y-1/2 border-l border-b`
      default:
        return arrowBase
    }
  }

  if (!content) return <>{children}</>

  return (
    <>
      <span
        ref={triggerRef}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onFocus={handleMouseEnter}
        onBlur={handleMouseLeave}
        className="inline-block"
      >
        {children}
      </span>

      {isVisible && (
        <div
          ref={tooltipRef}
          role="tooltip"
          className={`
            fixed z-[var(--z-tooltip)] pointer-events-none
            px-3 py-2 rounded-lg text-sm
            bg-[var(--tooltip-bg)] border border-[var(--tooltip-border)]
            shadow-lg backdrop-blur-md
            transition-opacity duration-200
            ${className}
          `.trim().replace(/\s+/g, ' ')}
          style={{
            top: `${coords.top}px`,
            left: `${coords.left}px`,
            opacity: coords.top === 0 ? 0 : 1,
          }}
        >
          <div className={getArrowStyle()} />
          {content}
        </div>
      )}
    </>
  )
}
