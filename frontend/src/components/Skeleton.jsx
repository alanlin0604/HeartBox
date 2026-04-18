/**
 * Modern Skeleton Loading Component with Shimmer Effect
 * Follows HeartBox Design System
 *
 * Features:
 * - Smooth shimmer animation (better than pulse)
 * - Respects prefers-reduced-motion
 * - Proper aspect ratios to prevent CLS
 */

function BaseSkeleton({ className = '', shimmer = true }) {
  return (
    <div
      className={`rounded-lg bg-white/10 overflow-hidden relative ${className}`}
      role="status"
      aria-label="Loading..."
    >
      {shimmer && (
        <div className="skeleton-shimmer absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/5 to-transparent" />
      )}
    </div>
  )
}

export function PageSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-live="polite">
      <BaseSkeleton className="h-10 w-64" />
      <BaseSkeleton className="h-24 w-full" />
      <BaseSkeleton className="h-24 w-full" />
      <BaseSkeleton className="h-24 w-full" />
    </div>
  )
}

export function CardSkeleton() {
  return (
    <div className="glass-card p-4 space-y-3" aria-busy="true">
      <BaseSkeleton className="h-4 w-40" />
      <BaseSkeleton className="h-3 w-full" />
      <BaseSkeleton className="h-3 w-5/6" />
      <BaseSkeleton className="h-3 w-3/5" />
    </div>
  )
}

export function LineSkeleton({ width = '100%', height = '1rem' }) {
  return <BaseSkeleton className="h-[var(--h)]" style={{ '--h': height, width }} />
}

export function CircleSkeleton({ size = '3rem' }) {
  return <BaseSkeleton className="rounded-full w-[var(--s)] h-[var(--s)]" style={{ '--s': size }} />
}

// Add shimmer animation styles (will be injected once)
if (typeof document !== 'undefined' && !document.querySelector('style[data-skeleton-shimmer]')) {
  const style = document.createElement('style')
  style.setAttribute('data-skeleton-shimmer', 'true')
  style.textContent = `
    @keyframes skeleton-shimmer {
      0% {
        transform: translateX(-100%);
      }
      100% {
        transform: translateX(100%);
      }
    }

    .skeleton-shimmer {
      animation: skeleton-shimmer 2s infinite;
    }

    @media (prefers-reduced-motion: reduce) {
      .skeleton-shimmer {
        animation: none;
        opacity: 0.5;
      }
    }
  `
  document.head.appendChild(style)
}
