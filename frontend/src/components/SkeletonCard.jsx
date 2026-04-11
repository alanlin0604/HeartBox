/**
 * Reusable skeleton loading placeholder.
 * @param {number} lines - Number of text lines to show (default 3)
 * @param {boolean} showAvatar - Whether to show avatar circle
 */
export default function SkeletonCard({ lines = 3, showAvatar = false }) {
  return (
    <div className="glass-card p-4 animate-pulse space-y-3" role="status" aria-label="載入中">
      {showAvatar && (
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full" style={{ background: 'var(--surface-elevated)' }} />
          <div className="h-4 rounded w-24" style={{ background: 'var(--surface-elevated)' }} />
        </div>
      )}
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className="h-3 rounded"
          style={{
            width: `${85 - i * 15}%`,
            background: 'var(--surface-elevated)'
          }}
        />
      ))}
      <span className="sr-only">載入中...</span>
    </div>
  )
}
