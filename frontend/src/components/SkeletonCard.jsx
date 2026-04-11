/**
 * Reusable skeleton loading placeholder.
 * @param {number} lines - Number of text lines to show (default 3)
 * @param {boolean} showAvatar - Whether to show avatar circle
 */
export default function SkeletonCard({ lines = 3, showAvatar = false }) {
  return (
    <div className="glass-card p-4 animate-pulse space-y-3">
      {showAvatar && (
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-purple-500/10" />
          <div className="h-4 bg-purple-500/10 rounded w-24" />
        </div>
      )}
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className="h-3 bg-purple-500/10 rounded"
          style={{ width: `${85 - i * 15}%` }}
        />
      ))}
    </div>
  )
}
