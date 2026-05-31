import { useState, useEffect } from 'react'

/**
 * Sticky pill bar of in-page anchor jumps for long chart pages.
 *
 * Uses native URL anchors (no router state, no scroll listener) for
 * the click handler — simpler than tabs, every section stays in the
 * DOM so users can still scroll-skim and screenshot the full report
 * for their therapist. The active highlight is computed with a single
 * IntersectionObserver shared across all section ids passed in
 * `sections`, so we don't need to re-implement scroll-spy by hand.
 *
 * On mobile the bar overflows horizontally with snap-scroll. Background
 * is intentionally opaque so charts scrolling underneath don't bleed
 * through the active pill.
 */
export default function SectionAnchorBar({ sections }) {
  const [activeId, setActiveId] = useState(sections[0]?.id)

  useEffect(() => {
    const ids = sections.map(s => s.id)
    const elements = ids.map(id => document.getElementById(id)).filter(Boolean)
    if (elements.length === 0) return

    const observer = new IntersectionObserver(
      (entries) => {
        // Pick the most visible section currently intersecting the viewport.
        const visible = entries
          .filter(e => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)
        if (visible.length > 0) {
          setActiveId(visible[0].target.id)
        }
      },
      // Top-third trigger zone so the active pill flips as a section's
      // header crosses the top of the viewport, not when it leaves.
      { rootMargin: '-20% 0px -60% 0px', threshold: [0, 0.1, 0.5, 1] },
    )

    elements.forEach(el => observer.observe(el))
    return () => observer.disconnect()
  }, [sections])

  return (
    <nav
      aria-label="Sections"
      className="sticky top-[calc(env(safe-area-inset-top)+4.5rem)] z-30 -mx-4 px-4 py-2 backdrop-blur-md bg-[var(--bg-primary)]/85 border-b border-[var(--card-border)]/40"
    >
      <ul className="flex gap-1.5 overflow-x-auto snap-x scrollbar-thin">
        {sections.map(s => (
          <li key={s.id} className="snap-start flex-shrink-0">
            <a
              href={`#${s.id}`}
              className={`block px-3 py-1.5 rounded-full text-xs font-medium transition-colors whitespace-nowrap ${
                activeId === s.id
                  ? 'bg-orange-500/20 text-orange-500 border border-orange-500/30'
                  : 'opacity-60 hover:opacity-100 border border-transparent'
              }`}
            >
              {s.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  )
}
