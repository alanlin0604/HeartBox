// Global font-scale (5-step). Mounts once on app boot, writes the chosen
// multiplier onto <html> as both an inline font-size AND a CSS custom
// property (--app-font-scale) so callers can `calc()` against it.
//
// Strategy: all Tailwind sizing utilities (text-*, p-*, gap-*, w-1/2 of a
// rem-based container, etc.) are rem-based, so changing the root font-
// size proportionally scales typography AND spacing — keeping layouts
// visually consistent at every step. RWD breakpoints in Tailwind are px-
// based (sm:, md:, lg:) so they don't shift, which means a phone stays
// on its mobile layout even at XL.
//
// Range chosen 0.875–1.25 (14px–20px). Going below 14px hurts a11y;
// going above 20px starts to break tight nav/header pixels even with
// Tailwind's flex-wrap.

import { createContext, useContext, useEffect, useState, useMemo, useCallback } from 'react'

const STORAGE_KEY = 'heartbox_font_scale'
const DEFAULT_SCALE = 1

export const FONT_SCALE_OPTIONS = [
  { key: 'xs', scale: 0.875,  labelKey: 'settings.fontXSmall'  },  // 14px
  { key: 's',  scale: 0.9375, labelKey: 'settings.fontSmall'   },  // 15px
  { key: 'm',  scale: 1,      labelKey: 'settings.fontMedium'  },  // 16px (default)
  { key: 'l',  scale: 1.125,  labelKey: 'settings.fontLarge'   },  // 18px
  { key: 'xl', scale: 1.25,   labelKey: 'settings.fontXLarge'  },  // 20px
]

const VALID_SCALES = FONT_SCALE_OPTIONS.map((o) => o.scale)

function getInitialScale() {
  try {
    const raw = parseFloat(localStorage.getItem(STORAGE_KEY) || '')
    if (VALID_SCALES.includes(raw)) return raw
  } catch { /* private mode / quota */ }
  return DEFAULT_SCALE
}

function applyScale(scale) {
  const root = document.documentElement
  root.style.fontSize = `${scale * 16}px`
  root.style.setProperty('--app-font-scale', String(scale))
  // Tag the body so CSS can opt into scale-aware rules (e.g. tightening
  // padding at xl on small screens) without re-reading the inline style.
  root.setAttribute('data-font-scale', String(scale))
}

const FontScaleContext = createContext(null)

export function FontScaleProvider({ children }) {
  const [scale, setScaleState] = useState(getInitialScale)

  // Apply ASAP on mount, before children render their first paint
  useEffect(() => {
    applyScale(scale)
    try { localStorage.setItem(STORAGE_KEY, String(scale)) } catch {}
  }, [scale])

  const setScale = useCallback((next) => {
    if (!VALID_SCALES.includes(next)) return
    setScaleState(next)
  }, [])

  const value = useMemo(
    () => ({ scale, setScale, options: FONT_SCALE_OPTIONS }),
    [scale, setScale],
  )

  return (
    <FontScaleContext.Provider value={value}>
      {children}
    </FontScaleContext.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export const useFontScale = () => useContext(FontScaleContext)
