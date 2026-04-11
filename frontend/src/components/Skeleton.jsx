function BaseSkeleton({ className = '' }) {
  return <div className={`animate-pulse rounded-lg bg-white/10 ${className}`} />
}

export function PageSkeleton() {
  return (
    <div className="space-y-4">
      <BaseSkeleton className="h-10 w-64" />
      <BaseSkeleton className="h-24 w-full" />
      <BaseSkeleton className="h-24 w-full" />
      <BaseSkeleton className="h-24 w-full" />
    </div>
  )
}

export function CardSkeleton() {
  return (
    <div className="glass-card p-4 space-y-3">
      <BaseSkeleton className="h-4 w-40" />
      <BaseSkeleton className="h-3 w-full" />
      <BaseSkeleton className="h-3 w-5/6" />
      <BaseSkeleton className="h-3 w-3/5" />
    </div>
  )
}
