import { useEffect, useState } from 'react'
import { aiAPI } from '../api/ai'
import { useLang } from '../context/LanguageContext'

// Reverse map from the legacy English sentences the backend used to
// hard-code, back to the canonical IDs we now use as i18n key suffixes.
// Lets localization work even when the frontend has shipped the new
// schema but Cloud Run still serves the old prediction payload — which
// is the failure mode user reported on 2026-05-22 after the previous
// rollout (zh UI shell, en recommendations + tips body).
const LEGACY_REC_TO_ID = {
  'Consider reaching out to friends, family, or a counselor for support.': 'reach_out',
  'Engage in activities that previously brought you joy.': 'joy_activities',
  'Practice stress-reduction techniques like deep breathing or meditation.': 'deep_breathing',
  'Review your current commitments and consider what you might delegate or postpone.': 'review_commitments',
  'Prioritize rest and self-care activities.': 'rest_self_care',
  'Consider professional help if stress persists.': 'professional_help',
  'Reach out to a mental health professional.': 'mental_health_pro',
  'Talk to trusted friends or family members.': 'talk_friends',
  'Reflect on what changes or habits have helped you feel better.': 'reflect_habits',
  'Continue the practices that are working well for you.': 'continue_practices',
  'Maintain your current stress management strategies.': 'maintain_strategies',
  'Continue journaling regularly to track your emotional patterns.': 'continue_journaling',
  'Maintain a balanced routine with sleep, exercise, and social connection.': 'balanced_routine',
  'Be mindful of early warning signs and seek support when needed.': 'mindful_warning_signs',
}

// Same idea for health tips. Old backend shipped only `tip.tip` (full
// English string); the new backend adds `tip.tip_key`. Map the legacy
// English back to the canonical key so we can still translate.
const LEGACY_TIP_TO_KEY = {
  'High stress detected. Try the 4-7-8 breathing technique: breathe in for 4 counts, hold for 7, exhale for 8.': 'breathing_4_7_8',
  'Physical activity can boost mood. Try a 10-minute walk or light stretching.': 'physical_activity',
  'Maintain a consistent sleep schedule. Aim for 7-9 hours per night.': 'consistent_sleep',
  'Stay hydrated. Aim for 8 glasses of water daily. Dehydration can affect mood.': 'hydration',
  'Connect with others. Social support is crucial for mental well-being.': 'social_connection',
  "Practice gratitude. Write down 3 things you're grateful for each day.": 'gratitude',
}

/**
 * Mood Prediction widget — unified into one Card with internal section
 * dividers per user request 2026-05-22 (was 5 separate glass panels which
 * felt visually scattered). Each warning / recommendation / health tip now
 * resolves through i18n: backend returns a stable `type` / `id` / `tip_key`
 * which we look up as t(`prediction.warning.${type}`, params). If a key is
 * missing on the client (stale build), we fall back to the English string
 * the backend still ships in `message` / `tip` for backward compat.
 */
export default function MoodPrediction() {
  const { t } = useLang()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        setError(null)
        const result = await aiAPI.getPredictions()
        if (!cancelled) setData(result)
      } catch (err) {
        if (cancelled) return
        console.error('Failed to load predictions:', err)
        setError(err.response?.data?.error || t('prediction.loadError'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [t])

  if (loading) {
    return (
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('prediction.title')}</h2>
        <p className="text-sm text-[var(--text-secondary)]">{t('loading')}</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('prediction.title')}</h2>
        <p className="text-sm text-[var(--text-secondary)]">{error}</p>
      </div>
    )
  }

  if (!data) return null
  const { prediction, health_tips } = data

  if (!prediction.has_prediction) {
    return (
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('prediction.title')}</h2>
        <p className="text-sm text-[var(--text-secondary)]">
          {/* `prediction.message` here is still English from the backend
              when we have insufficient data — keep the localised key as
              the primary, fall through to the backend hint only if missing. */}
          {t('prediction.insufficientData') || prediction.message}
        </p>
      </div>
    )
  }

  // Trend indicator — for sentiment improving / stress decreasing we want
  // an "up" feel (green) and vice versa; for stress increasing / sentiment
  // declining we want a "down" feel (red). Stable = no arrow. Returns an
  // <img> element (or null) so the caller can just render {it}.
  const getTrendIcon = (trend) => {
    const up = (trend === 'improving' || trend === 'decreasing')
    const down = (trend === 'declining' || trend === 'increasing')
    if (up) return <img src="/icons/trend-up.svg" alt="" aria-hidden="true" className="inline-block w-5 h-5 object-contain align-middle mr-1" />
    if (down) return <img src="/icons/trend-down.svg" alt="" aria-hidden="true" className="inline-block w-5 h-5 object-contain align-middle mr-1" />
    return null
  }

  const getTrendColor = (type, trend) => {
    if (type === 'sentiment') {
      if (trend === 'improving') return 'text-green-500'
      if (trend === 'declining') return 'text-red-500'
    } else {
      if (trend === 'decreasing') return 'text-green-500'
      if (trend === 'increasing') return 'text-red-500'
    }
    return 'text-[var(--text-secondary)]'
  }

  const getWarningStyle = (level) => {
    if (level === 'high') return 'border-red-500/40 bg-red-500/10'
    if (level === 'medium') return 'border-yellow-500/40 bg-yellow-500/10'
    if (level === 'positive') return 'border-green-500/40 bg-green-500/10'
    return 'border-slate-500/40 bg-slate-500/10'
  }

  // Look up a warning's localised message. Falls back to the backend's
  // English `message` if the type isn't in the i18n catalog yet (e.g.
  // backend rolled out before frontend), so the user always sees something.
  const localizeWarning = (warning) => {
    const key = `prediction.warning.${warning.type}`
    const translated = t(key, warning.params || {})
    if (translated && translated !== key) return translated
    return warning.message || ''
  }

  const localizeRecommendation = (rec) => {
    // Backend may send: (a) a string ID like "reach_out" (new schema), or
    // (b) the full English sentence (legacy schema — Cloud Run hasn't been
    // redeployed yet). Try ID first, then reverse-lookup the English to
    // its canonical ID and try again. Final fallback shows whatever the
    // backend sent so the user never sees a blank bullet.
    if (typeof rec !== 'string') return ''
    let key = `prediction.rec.${rec}`
    let translated = t(key)
    if (translated && translated !== key) return translated
    const mappedId = LEGACY_REC_TO_ID[rec]
    if (mappedId) {
      key = `prediction.rec.${mappedId}`
      translated = t(key)
      if (translated && translated !== key) return translated
    }
    return rec
  }

  const localizeTip = (tip) => {
    // Prefer the new `tip_key` field. If the backend is on the old schema
    // that only sent `tip` (full English), reverse-map and try again.
    if (tip.tip_key) {
      const key = `prediction.tip.${tip.tip_key}`
      const translated = t(key)
      if (translated && translated !== key) return translated
    }
    if (tip.tip) {
      const mappedKey = LEGACY_TIP_TO_KEY[tip.tip]
      if (mappedKey) {
        const key = `prediction.tip.${mappedKey}`
        const translated = t(key)
        if (translated && translated !== key) return translated
      }
    }
    return tip.tip || ''
  }

  return (
    // ONE unified container per UX request 2026-05-22. Inner sections are
    // separated by border-t dividers instead of nesting separate panels —
    // less visual fragmentation, easier to scan top-to-bottom.
    <div className="glass p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-orange-500 to-rose-500">
          {t('prediction.title')}
        </h1>
        <p className="text-sm text-[var(--text-secondary)] mt-1">
          {t('prediction.subtitle')}
        </p>
      </div>

      {/* Current Status — sentiment + stress side-by-side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-[var(--card-border)]">
        {/* Sentiment */}
        <div className="pt-4">
          <h2 className="text-base font-semibold mb-3 flex items-center gap-2">
            <img src="/icons/mood-trend.svg" alt="" aria-hidden="true" className="w-6 h-6 object-contain" />
            {t('prediction.moodTrend')}
          </h2>
          <div className="space-y-2.5">
            <div>
              <p className="text-xs text-[var(--text-secondary)]">{t('prediction.current')}</p>
              <p className="text-2xl font-bold text-[var(--text-primary)]">{prediction.sentiment.current}</p>
            </div>
            <div>
              <p className="text-xs text-[var(--text-secondary)]">{t('prediction.trend')}</p>
              <p className={`text-base font-semibold ${getTrendColor('sentiment', prediction.sentiment.trend)}`}>
                {getTrendIcon(prediction.sentiment.trend)} {t(`prediction.trend_${prediction.sentiment.trend}`)}
              </p>
            </div>
            {Math.abs(prediction.sentiment.slope) > 0.01 && (
              <div>
                <p className="text-xs text-[var(--text-secondary)]">{t('prediction.forecast7d')}</p>
                <p className="text-base text-[var(--text-primary)]">{prediction.sentiment.forecast_7d}</p>
              </div>
            )}
          </div>
        </div>

        {/* Stress */}
        <div className="pt-4">
          <h2 className="text-base font-semibold mb-3 flex items-center gap-2">
            <img src="/icons/stress-trend.svg" alt="" aria-hidden="true" className="w-6 h-6 object-contain" />
            {t('prediction.stressTrend')}
          </h2>
          <div className="space-y-2.5">
            <div>
              <p className="text-xs text-[var(--text-secondary)]">{t('prediction.current')}</p>
              <p className="text-2xl font-bold text-[var(--text-primary)]">{prediction.stress.current} / 10</p>
            </div>
            <div>
              <p className="text-xs text-[var(--text-secondary)]">{t('prediction.trend')}</p>
              <p className={`text-base font-semibold ${getTrendColor('stress', prediction.stress.trend)}`}>
                {getTrendIcon(prediction.stress.trend)} {t(`prediction.trend_${prediction.stress.trend}`)}
              </p>
            </div>
            {Math.abs(prediction.stress.slope) > 0.05 && (
              <div>
                <p className="text-xs text-[var(--text-secondary)]">{t('prediction.forecast7d')}</p>
                <p className="text-base text-[var(--text-primary)]">{prediction.stress.forecast_7d} / 10</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Warnings */}
      {prediction.warnings && prediction.warnings.length > 0 && (
        <div className="pt-4 border-t border-[var(--card-border)]">
          <h2 className="text-base font-semibold mb-3">{t('prediction.alerts')}</h2>
          <div className="space-y-2">
            {prediction.warnings.map((warning, index) => (
              <div
                key={index}
                className={`p-3 rounded-lg border ${getWarningStyle(warning.level)}`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-xl flex-shrink-0">{warning.icon}</span>
                  <p className="text-sm text-[var(--text-primary)] leading-relaxed">
                    {localizeWarning(warning)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {prediction.recommendations && prediction.recommendations.length > 0 && (
        <div className="pt-4 border-t border-[var(--card-border)]">
          <h2 className="text-base font-semibold mb-3">{t('prediction.recommendations')}</h2>
          <ul className="space-y-2">
            {prediction.recommendations.map((rec, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-[var(--text-primary)]">
                <span className="text-orange-500 mt-0.5 flex-shrink-0">•</span>
                <span className="leading-relaxed">{localizeRecommendation(rec)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Health Tips */}
      {health_tips && health_tips.length > 0 && (
        <div className="pt-4 border-t border-[var(--card-border)]">
          <h2 className="text-base font-semibold mb-3">{t('prediction.healthTips')}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {health_tips.map((tip, index) => (
              <div
                key={index}
                className="p-3 rounded-lg bg-[var(--surface-secondary)] border border-[var(--card-border)]"
              >
                <div className="flex items-start gap-3">
                  <span className="text-xl flex-shrink-0">{tip.icon}</span>
                  <p className="text-sm text-[var(--text-primary)] leading-relaxed">
                    {localizeTip(tip)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-[var(--text-tertiary)] text-center pt-2 border-t border-[var(--card-border)]">
        {t('prediction.disclaimer')}
      </p>
    </div>
  )
}
