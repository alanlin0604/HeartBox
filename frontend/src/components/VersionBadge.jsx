/**
 * VersionBadge — fixed-corner build identifier so anyone (including remote
 * testers) can confirm at a glance which build is being served. Pulls the
 * value vite.config injects via the `__CACHE_VERSION__` define, which is
 * `v{UTC-timestamp}-{git-short-sha}` shaped (e.g. `v20260509T1130-6920736`).
 *
 * In dev (no build), the define still resolves to a fresh value each
 * `npm run dev` start, which is enough for "did my edit reload" sanity.
 */
// eslint-disable-next-line no-undef
const VERSION = typeof __CACHE_VERSION__ !== 'undefined' ? __CACHE_VERSION__ : 'dev'

export default function VersionBadge() {
  return (
    <div
      className="fixed bottom-1 right-2 z-[9999] text-[10px] font-mono text-[var(--text-muted)] opacity-40 hover:opacity-90 select-none pointer-events-auto cursor-help"
      title="Build version — paste this in bug reports so we can pin down which deploy you're on."
    >
      {VERSION}
    </div>
  )
}
