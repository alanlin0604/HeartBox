// Renders the personal_insights array from /api/analytics/ as a stack of
// human-readable insight cards. Backend hands us raw numeric breakdowns
// (best/worst phase, sample counts, etc.); this component owns the
// translation + presentation so adding a new insight type doesn't require
// a backend deploy — just add a key to the i18n bundle and a renderer here.
//
// One "card" per insight, accent-coloured by severity:
//   strong  → solid orange border / soft fill   (clear pattern)
//   mild    → muted slate                         (weak signal)
//
// Empty input renders null so the parent can hide the whole section
// when the user doesn't have enough data yet.

import { useLang } from '../context/LanguageContext'

const PHASE_LABELS = { early: 'monthPhase.early', mid: 'monthPhase.mid', late: 'monthPhase.late' }

function severityClasses(severity) {
  if (severity === 'strong') {
    return 'border-l-4 border-orange-500 bg-orange-500/5'
  }
  return 'border-l-4 border-slate-400/40 bg-slate-400/5'
}

function InsightCard({ insight, t, monthLabel }) {
  const { key, severity } = insight
  const classes = `${severityClasses(severity)} rounded-r-lg px-4 py-3`

  if (key === 'month_phase') {
    return (
      <div className={classes}>
        <p className="text-sm font-semibold mb-1">
          {t('insights.monthPhase.title', {
            best: t(PHASE_LABELS[insight.best_phase]) || insight.best_phase,
          })}
        </p>
        <p className="text-xs opacity-70">
          {t('insights.monthPhase.detail', {
            best: t(PHASE_LABELS[insight.best_phase]) || insight.best_phase,
            bestAvg: insight.best_avg.toFixed(2),
            bestCount: insight.best_count,
            worst: t(PHASE_LABELS[insight.worst_phase]) || insight.worst_phase,
            worstAvg: insight.worst_avg.toFixed(2),
            worstCount: insight.worst_count,
          })}
        </p>
      </div>
    )
  }

  if (key === 'weekday_weekend') {
    const better = insight.better === 'weekend' ? t('insights.weekend') : t('insights.weekday')
    const worse = insight.better === 'weekend' ? t('insights.weekday') : t('insights.weekend')
    return (
      <div className={classes}>
        <p className="text-sm font-semibold mb-1">
          {t('insights.weekdayWeekend.title', { better })}
        </p>
        <p className="text-xs opacity-70">
          {t('insights.weekdayWeekend.detail', {
            better,
            betterAvg: (insight.better === 'weekend' ? insight.weekend_avg : insight.weekday_avg).toFixed(2),
            worse,
            worseAvg: (insight.better === 'weekend' ? insight.weekday_avg : insight.weekend_avg).toFixed(2),
            diff: Math.abs(insight.diff).toFixed(2),
          })}
        </p>
      </div>
    )
  }

  if (key === 'month_extremes') {
    return (
      <div className={classes}>
        <p className="text-sm font-semibold mb-1">
          {t('insights.monthExtremes.title', {
            best: monthLabel(insight.best_month),
            worst: monthLabel(insight.worst_month),
          })}
        </p>
        <p className="text-xs opacity-70">
          {t('insights.monthExtremes.detail', {
            best: monthLabel(insight.best_month),
            bestAvg: insight.best_avg.toFixed(2),
            bestCount: insight.best_count,
            worst: monthLabel(insight.worst_month),
            worstAvg: insight.worst_avg.toFixed(2),
            worstCount: insight.worst_count,
          })}
        </p>
      </div>
    )
  }

  if (key === 'weather_sun_rain') {
    const better = insight.better === 'sunny' ? t('insights.sunny') : t('insights.rainy')
    return (
      <div className={classes}>
        <p className="text-sm font-semibold mb-1">
          {t('insights.weatherSunRain.title', { better })}
        </p>
        <p className="text-xs opacity-70">
          {t('insights.weatherSunRain.detail', {
            sunnyAvg: insight.sunny_avg.toFixed(2),
            sunnyCount: insight.sunny_count,
            rainyAvg: insight.rainy_avg.toFixed(2),
            rainyCount: insight.rainy_count,
          })}
        </p>
      </div>
    )
  }

  if (key === 'temperature_band') {
    const better = insight.better === 'warm' ? t('insights.warm') : t('insights.cold')
    return (
      <div className={classes}>
        <p className="text-sm font-semibold mb-1">
          {t('insights.temperatureBand.title', { better })}
        </p>
        <p className="text-xs opacity-70">
          {t('insights.temperatureBand.detail', {
            coldAvg: insight.cold_avg.toFixed(2),
            coldCount: insight.cold_count,
            warmAvg: insight.warm_avg.toFixed(2),
            warmCount: insight.warm_count,
          })}
        </p>
      </div>
    )
  }

  return null  // unknown key — skip rather than crash on future server additions
}

export default function PersonalInsights({ insights, lookbackDays }) {
  const { t, lang } = useLang()
  if (!Array.isArray(insights) || insights.length === 0) return null

  // Localise month numbers via Intl so 6 -> "6 月" / "Jun." / "6月"
  const monthLabel = (m) => {
    try {
      return new Date(2000, m - 1, 1).toLocaleDateString(lang || 'en', { month: 'long' })
    } catch {
      return `${m}`
    }
  }

  return (
    <div className="glass p-6">
      <h2 className="text-lg font-semibold mb-1">{t('insights.sectionTitle')}</h2>
      <p className="text-xs opacity-50 mb-4">
        {t('insights.sectionHint', { days: lookbackDays || 180 })}
      </p>
      <div className="space-y-3">
        {insights.map((ins, idx) => (
          <InsightCard key={idx} insight={ins} t={t} monthLabel={monthLabel} />
        ))}
      </div>
    </div>
  )
}
