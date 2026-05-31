/**
 * Visual grouping for chart-heavy pages.
 *
 * Before: pages like /dashboard were a 3000px vertical scroll of glass
 * cards with no obvious grouping — users couldn't tell which charts
 * were related and the page felt scattered. Now each themed group is
 * wrapped in a <DashboardSection> with a slim uppercase header so the
 * five buckets (overview / patterns / body & mind / health snapshot
 * / history) read as distinct chapters.
 *
 * The `id` is used by the page's sticky anchor bar so anchor jumps
 * work; `scroll-mt-24` clears the top nav. Section content uses the
 * caller's normal `space-y-*` rhythm — this component only renders
 * the header and the outer <section> wrapper.
 */
export default function DashboardSection({ id, title, subtitle, icon, children, className = '' }) {
  return (
    <section id={id} className={`scroll-mt-24 ${className}`}>
      <header className="mb-3 flex items-center gap-2">
        {icon && (
          <img src={icon} alt="" aria-hidden="true" className="w-5 h-5 object-contain opacity-70" />
        )}
        <h2 className="text-xs font-semibold uppercase tracking-[0.18em] opacity-60">
          {title}
        </h2>
        {subtitle && (
          <span className="text-xs opacity-50 normal-case tracking-normal">
            · {subtitle}
          </span>
        )}
      </header>
      <div className="space-y-4">
        {children}
      </div>
    </section>
  )
}
