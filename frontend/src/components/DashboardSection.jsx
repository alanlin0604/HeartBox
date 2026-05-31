/**
 * Visual grouping for chart-heavy pages.
 *
 * Before: pages like /dashboard were a 3000px vertical scroll of glass
 * cards with no obvious grouping — users couldn't tell which charts
 * were related and the page felt scattered. Now each themed group is
 * wrapped in a <DashboardSection> with a hero header so the five
 * buckets read as distinct chapters.
 *
 * Header redesigned 2026-06-01 from a tiny uppercase tracked-out
 * caption to a proper section heading: 24px title + 14px subtitle +
 * matching icon + 3px orange accent bar to the left. The previous
 * caption blended with chart card titles below it; users couldn't
 * tell where one section started and the next ended.
 *
 * `scroll-mt-24` clears the sticky nav + anchor bar so anchor jumps
 * land with the header in view rather than tucked behind the nav.
 */
export default function DashboardSection({ id, title, subtitle, icon, children, className = '' }) {
  return (
    <section id={id} className={`scroll-mt-32 ${className}`}>
      <header className="mb-5 flex items-center gap-3 pl-3 border-l-[3px] border-orange-500/70 rounded-l-sm">
        {icon && (
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-orange-500/15 to-rose-500/10 ring-1 ring-orange-500/20 flex items-center justify-center flex-shrink-0">
            <img src={icon} alt="" aria-hidden="true" className="w-5 h-5 object-contain" />
          </div>
        )}
        <div className="flex-1 min-w-0">
          <h2 className="text-xl font-bold text-[var(--text-primary)] leading-tight">
            {title}
          </h2>
          {subtitle && (
            <p className="text-sm text-[var(--text-tertiary)] mt-0.5 leading-snug">
              {subtitle}
            </p>
          )}
        </div>
      </header>
      <div className="space-y-4">
        {children}
      </div>
    </section>
  )
}
