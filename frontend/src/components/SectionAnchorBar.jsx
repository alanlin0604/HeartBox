import { useState, useEffect } from 'react'

/**
 * Sticky pill bar of in-page anchor jumps for long chart pages.
 *
 * Each `sections` entry: `{ id, label, icon? }`. Icons are 18px SVGs
 * from /public/icons; they sit left of the label and fade with the
 * inactive opacity so they don't dominate the bar visually.
 *
 * Active highlight uses a soft gradient pill + bottom underline so the
 * current section is unmistakable on both light + dark themes — the
 * older flat-bg version washed out against the page's glass cards.
 *
 * IntersectionObserver picks the section whose header is closest to
 * the top third of the viewport, so the active pill flips as you scroll
 * (not when a section leaves). On mobile the pill row scrolls
 * horizontally with snap stops.
 */
export default function SectionAnchorBar({ sections }) {
  const [activeId, setActiveId] = useState(sections[0]?.id)

  useEffect(() => {
    const ids = sections.map(s => s.id)
    const elements = ids.map(id => document.getElementById(id)).filter(Boolean)
    if (elements.length === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter(e => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)
        if (visible.length > 0) {
          setActiveId(visible[0].target.id)
        }
      },
      { rootMargin: '-20% 0px -60% 0px', threshold: [0, 0.1, 0.5, 1] },
    )

    elements.forEach(el => observer.observe(el))
    return () => observer.disconnect()
  }, [sections])

  return (
    <nav
      aria-label="Sections"
      className="sticky top-[calc(env(safe-area-inset-top)+4.5rem)] z-30 -mx-4 px-4 py-2.5 backdrop-blur-xl bg-[var(--bg-primary)]/80 border-b border-orange-500/10 shadow-[0_2px_12px_-4px_rgba(0,0,0,0.08)]"
    >
      <ul className="flex gap-1 overflow-x-auto snap-x snap-mandatory scrollbar-thin">
        {sections.map(s => {
          const active = activeId === s.id
          return (
            <li key={s.id} className="snap-start flex-shrink-0">
              <a
                href={`#${s.id}`}
                className={`group relative flex items-center gap-1.5 px-3.5 py-2 rounded-full text-xs font-medium whitespace-nowrap transition-all duration-200 ${
                  active
                    ? 'bg-gradient-to-r from-orange-500/20 to-rose-500/15 text-orange-500 ring-1 ring-orange-500/40 shadow-[0_2px_8px_-2px_rgba(249,115,22,0.3)]'
                    : 'opacity-55 hover:opacity-100 hover:bg-white/5'
                }`}
              >
                {s.icon && (
                  <img
                    src={s.icon}
                    alt=""
                    aria-hidden="true"
                    className={`w-4 h-4 object-contain transition-opacity ${active ? 'opacity-100' : 'opacity-70'}`}
                  />
                )}
                <span>{s.label}</span>
              </a>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
