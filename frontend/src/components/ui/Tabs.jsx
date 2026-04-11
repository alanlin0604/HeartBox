import { useState } from 'react'

/**
 * Tabs Component
 *
 * 標籤頁組件
 *
 * @param {Array} tabs - 標籤頁配置 [{ id, label, icon?, content, disabled? }]
 * @param {string} defaultTab - 預設啟用的標籤頁 ID
 * @param {Function} onChange - 切換回調函數 (tabId) => void
 * @param {string} variant - 樣式變體：'line', 'pills', 'enclosed'
 * @param {string} className - 額外的 CSS 類別
 */
export default function Tabs({
  tabs = [],
  defaultTab,
  onChange,
  variant = 'line',
  className = '',
}) {
  const [activeTab, setActiveTab] = useState(defaultTab || tabs[0]?.id)

  const handleTabChange = (tabId) => {
    if (tabs.find(t => t.id === tabId)?.disabled) return
    setActiveTab(tabId)
    if (onChange) {
      onChange(tabId)
    }
  }

  // 變體樣式
  const variantStyles = {
    line: {
      container: 'border-b border-[var(--border-primary)]',
      tab: 'px-4 py-2.5 -mb-px text-sm font-medium transition-all',
      active: 'text-[var(--color-primary-500)] border-b-2 border-[var(--color-primary-500)]',
      inactive: 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] border-b-2 border-transparent',
    },
    pills: {
      container: 'gap-2 p-1 bg-[var(--surface-secondary)] rounded-xl',
      tab: 'px-4 py-2 text-sm font-medium rounded-lg transition-all',
      active: 'bg-[var(--color-primary-500)] text-white shadow-sm',
      inactive: 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-primary)]',
    },
    enclosed: {
      container: 'gap-1',
      tab: 'px-4 py-2.5 text-sm font-medium rounded-t-lg border border-b-0 transition-all',
      active: 'bg-[var(--surface-primary)] border-[var(--border-primary)] border-b-[var(--surface-primary)]',
      inactive: 'bg-transparent border-transparent text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:border-[var(--border-primary)]',
    },
  }

  const styles = variantStyles[variant] || variantStyles.line

  const activeContent = tabs.find(tab => tab.id === activeTab)?.content

  return (
    <div className={className}>
      {/* Tab Headers */}
      <div
        role="tablist"
        className={`flex ${styles.container}`.trim().replace(/\s+/g, ' ')}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            aria-controls={`tabpanel-${tab.id}`}
            disabled={tab.disabled}
            onClick={() => handleTabChange(tab.id)}
            className={`
              ${styles.tab}
              ${activeTab === tab.id ? styles.active : styles.inactive}
              ${tab.disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
            `.trim().replace(/\s+/g, ' ')}
          >
            {tab.icon && (
              <span className="inline-flex items-center gap-2">
                {tab.icon}
                {tab.label}
              </span>
            )}
            {!tab.icon && tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div
        role="tabpanel"
        id={`tabpanel-${activeTab}`}
        aria-labelledby={`tab-${activeTab}`}
        className="mt-4"
      >
        {activeContent}
      </div>
    </div>
  )
}
