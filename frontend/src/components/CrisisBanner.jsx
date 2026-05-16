/**
 * CrisisBanner — sticky top-of-viewport banner with regional crisis hotlines.
 *
 * Triggered by API responses that include `crisis_detected: true` (note
 * save, community post create, etc.). The banner is intentionally
 * impossible to miss — full-width, high-contrast, persistent until the
 * user explicitly dismisses. Dismissal is local-only and only lasts 24 h
 * because help should be one tap away if the user feels worse later.
 */

import { useCrisisBanner } from '../context/CrisisBannerContext'
import { useLang } from '../context/LanguageContext'

export default function CrisisBanner() {
  const { hotlines, dismiss } = useCrisisBanner() || {}
  const { t, lang } = useLang()

  if (!hotlines) return null

  // Surface the user's locale region first, then the others as secondary.
  const regionOrder = { 'zh-TW': ['tw', 'intl'], en: ['us', 'intl'], ja: ['jp', 'intl'] }
  const order = regionOrder[lang] || ['intl', 'tw', 'us', 'jp']

  return (
    <div
      role="alert"
      aria-live="assertive"
      className="fixed top-0 inset-x-0 z-[10000] bg-rose-600 text-white shadow-xl border-b-2 border-rose-800"
    >
      <div className="max-w-4xl mx-auto px-4 py-4 flex flex-col sm:flex-row gap-3 items-start">
        <div className="flex-1 space-y-2">
          <p className="font-bold text-base">{t('crisis.heading')}</p>
          <p className="text-sm opacity-95">{t('crisis.body')}</p>
          <ul className="flex flex-wrap gap-3 text-sm pt-1">
            {order.flatMap((region) =>
              (hotlines[region] || []).map((h, i) => (
                <li key={`${region}-${i}`} className="flex items-baseline gap-2 bg-rose-700/40 px-3 py-1.5 rounded-lg">
                  <span className="font-semibold">{h.name}</span>
                  {h.number?.startsWith('http') ? (
                    <a
                      href={h.number}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline font-mono"
                    >
                      {t('crisis.openLink')}
                    </a>
                  ) : (
                    <a href={`tel:${h.number}`} className="underline font-mono">
                      {h.number}
                    </a>
                  )}
                  {h.description && <span className="opacity-80 text-xs">— {h.description}</span>}
                </li>
              )),
            )}
          </ul>
        </div>
        <button
          onClick={dismiss}
          className="text-sm underline opacity-90 hover:opacity-100 self-end sm:self-start whitespace-nowrap"
        >
          {t('crisis.dismiss')}
        </button>
      </div>
    </div>
  )
}
