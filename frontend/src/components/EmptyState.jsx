import { memo } from 'react'

export default memo(function EmptyState({ title, description, actionText, onAction }) {
  return (
    <div className="glass-card p-8 text-center space-y-3" role="status">
      <div
        className="mx-auto w-24 h-24 rounded-full flex items-center justify-center"
        style={{ background: 'var(--surface-elevated)' }}
        aria-hidden="true"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="44"
          height="44"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ color: 'var(--color-primary)' }}
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M8 12h8" />
          <path d="M12 8v8" />
        </svg>
      </div>
      <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
        {title}
      </h3>
      <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
        {description}
      </p>
      {actionText && onAction && (
        <button type="button" onClick={onAction} className="btn-primary text-sm">
          {actionText}
        </button>
      )}
    </div>
  )
})
