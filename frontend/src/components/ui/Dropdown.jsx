import { useState, useRef, useEffect } from 'react'

/**
 * Dropdown Component
 *
 * 下拉選單組件
 *
 * @param {React.ReactNode} trigger - 觸發元素
 * @param {Array} items - 選單項目 [{ label, onClick, icon?, disabled?, divider? }]
 * @param {string} position - 位置：'bottom-left', 'bottom-right', 'top-left', 'top-right'
 * @param {string} className - 額外的 CSS 類別
 */
export default function Dropdown({
  trigger,
  items = [],
  position = 'bottom-left',
  className = '',
}) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)

  // 點擊外部關閉
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false)
      }
    }

    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
      document.addEventListener('keydown', handleEscape)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [isOpen])

  const handleToggle = () => {
    setIsOpen(!isOpen)
  }

  const handleItemClick = (item) => {
    if (item.disabled) return
    if (item.onClick) {
      item.onClick()
    }
    setIsOpen(false)
  }

  // 位置樣式
  const positionStyles = {
    'bottom-left': 'top-full left-0 mt-2',
    'bottom-right': 'top-full right-0 mt-2',
    'top-left': 'bottom-full left-0 mb-2',
    'top-right': 'bottom-full right-0 mb-2',
  }

  return (
    <div ref={dropdownRef} className={`relative inline-block ${className}`.trim()}>
      {/* Trigger */}
      <div onClick={handleToggle} className="cursor-pointer">
        {trigger}
      </div>

      {/* Dropdown Menu */}
      {isOpen && (
        <div
          role="menu"
          className={`
            absolute z-[var(--z-dropdown)]
            min-w-[12rem] max-w-xs
            bg-[var(--popup-bg)] border border-[var(--border-primary)]
            rounded-xl shadow-lg backdrop-blur-md
            py-2
            animate-scale-in
            ${positionStyles[position] || positionStyles['bottom-left']}
          `.trim().replace(/\s+/g, ' ')}
        >
          {items.map((item, index) => {
            // 分隔線
            if (item.divider) {
              return (
                <div
                  key={`divider-${index}`}
                  className="h-px bg-[var(--border-primary)] my-2"
                  role="separator"
                />
              )
            }

            return (
              <button
                key={index}
                onClick={() => handleItemClick(item)}
                disabled={item.disabled}
                role="menuitem"
                className={`
                  w-full px-4 py-2.5
                  flex items-center gap-3
                  text-left text-sm
                  transition-colors
                  ${item.disabled
                    ? 'opacity-50 cursor-not-allowed'
                    : 'hover:bg-[var(--surface-primary)] cursor-pointer'
                  }
                `.trim().replace(/\s+/g, ' ')}
              >
                {item.icon && (
                  <span className="flex-shrink-0 w-4 h-4">
                    {item.icon}
                  </span>
                )}
                <span className="flex-1">{item.label}</span>
                {item.badge && (
                  <span className="flex-shrink-0 text-xs opacity-60">
                    {item.badge}
                  </span>
                )}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
