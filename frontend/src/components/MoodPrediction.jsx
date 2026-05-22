import { useEffect, useState } from 'react'
import { aiAPI } from '../api/ai'
import { useLang } from '../context/LanguageContext'

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

  const getTrendIcon = (trend) => {
    if (trend === 'improving' || trend === 'decreasing') return '📈'
    if (trend === 'declining' || trend === 'increasing') return '📉'
    return '➡️'
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
    // Backend now sends string IDs (e.g. "reach_out"); pre-refactor builds
    // sent the full English sentence — accept both transparently.
    if (typeof rec !== 'string') return ''
    const key = `prediction.rec.${rec}`
    const translated = t(key)
    if (translated && translated !== key) return translated
    return rec  // legacy: backend still sent the English sentence
  }

  const localizeTip = (tip) => {
    if (tip.tip_key) {
      const key = `prediction.tip.${tip.tip_key}`
      const translated = t(key)
      if (translated && translated !== key) return translated
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
            <span>😊</span>
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
            <span>📊</span>
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
