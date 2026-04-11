function BaseSkeleton({ className = '' }) {
  return (
    <div
      className={`animate-pulse rounded-lg ${className}`}
      style={{ background: 'var(--surface-elevated)' }}
    />
  )
}

export function PageSkeleton() {
  return (
    <div className="space-y-4" role="status" aria-label="載入中">
      <BaseSkeleton className="h-10 w-64" />
      <BaseSkeleton className="h-24 w-full" />
      <BaseSkeleton className="h-24 w-full" />
      <BaseSkeleton className="h-24 w-full" />
      <span className="sr-only">載入中...</span>
    </div>
  )
}

export function CardSkeleton() {
  return (
    <div className="glass-card p-4 space-y-3" role="status" aria-label="載入中">
      <BaseSkeleton className="h-4 w-40" />
      <BaseSkeleton className="h-3 w-full" />
      <BaseSkeleton className="h-3 w-5/6" />
      <BaseSkeleton className="h-3 w-3/5" />
      <span className="sr-only">載入中...</span>
    </div>
  )
}
