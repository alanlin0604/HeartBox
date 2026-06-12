import { useEffect, useState } from 'react'
import { useLang } from '../context/LanguageContext'
import api from '../api/axios'

/**
 * Before/after self-comparison card. Added 2026-06-02 per thesis-advisor
 * feedback that users should be able to SEE the system's impact on them
 * (a within-subjects control vs current week, rather than a between-
 * subjects population cohort comparison).
 *
 * Backend computes 5 metrics for two 7-day windows — baseline (first week
 * the user journaled) vs current (last 7 days). We render them as
 * compact rows: label, baseline value, current value, delta arrow.
 *
 * Delta sign convention: positive number = improvement. Backend inverts
 * stress so "stress dropped" comes through as a positive delta — UI only
 * needs to color positive=green and negative=red.
 *
 * If the user is < 14 days in we render a "keep going" prompt instead
 * of a misleading table of zeros.
 */
export default function ProgressCompareCard() {
  const { t } = useLang()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    api.get('/analytics/progress/')
      .then((res) => { if (!cancelled) setData(res.data) })
      .catch(() => { if (!cancelled) setData(null) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [])

  if (loading) return null
  if (!data) return null

  if (!data.has_enough_data) {
    return (
      <div className="glass-card p-5 border-l-[3px] border-orange-500/70">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500/20 to-rose-500/10 ring-1 ring-orange-500/20 flex items-center justify-center flex-shrink-0">
            <img src="/icons/sprout.svg" alt="" className="w-5 h-5 object-contain" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-sm mb-1">{t('progress.notReadyTitle')}</h3>
            <p className="text-xs opacity-70 leading-relaxed">{t('progress.notReadyDesc')}</p>
          </div>
        </div>
      </div>
    )
  }

  const METRIC_DEFS = [
    { key: 'avg_sentiment',    label: t('progress.metric.avgSentiment'),    fmt: (v) => v?.toFixed(2),  betterWhenPositive: true },
    { key: 'avg_stress',       label: t('progress.metric.avgStress'),       fmt: (v) => v?.toFixed(2),  betterWhenPositive: false /* raw value: lower is better — but backend already inverted delta */ },
    { key: 'journal_days',     label: t('progress.metric.journalDays'),     fmt: (v) => `${v}/7`,       betterWhenPositive: true },
    { key: 'avg_sleep_hours',  label: t('progress.metric.sleepHours'),      fmt: (v) => `${v?.toFixed(1)}h`, betterWhenPositive: true },
    { key: 'habit_completion', label: t('progress.metric.habitCompletion'), fmt: (v) => `${Math.round(v * 100)}%`, betterWhenPositive: true },
  ]

  return (
    <div className="glass-card p-5 space-y-4">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-base">{t('progress.title')}</h3>
          <p className="text-xs opacity-60 mt-0.5">
            {t('progress.usingFor', { days: data.days_using })}
          </p>
        </div>
        <div className="text-right">
          <div className="text-xs opacity-50">{t('progress.compare')}</div>
          <div className="text-xs font-medium opacity-80">{t('progress.firstWeekVsLatest')}</div>
        </div>
      </header>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs opacity-60">
              <th className="text-left py-1.5 font-normal">{t('progress.col.metric')}</th>
              <th className="text-right py-1.5 font-normal whitespace-nowrap">{t('progress.col.baseline')}</th>
              <th className="text-right py-1.5 font-normal whitespace-nowrap">{t('progress.col.current')}</th>
              <th className="text-right py-1.5 font-normal whitespace-nowrap">{t('progress.col.change')}</th>
            </tr>
          </thead>
          <tbody>
            {METRIC_DEFS.map(m => {
              const base = data.baseline?.[m.key]
              const curr = data.current?.[m.key]
              const delta = data.deltas?.[m.key]
              const hasData = base !== null && base !== undefined && curr !== null && curr !== undefined
              return (
                <tr key={m.key} className="border-t border-[var(--card-border)]/40">
                  <td className="py-2 pr-2">{m.label}</td>
                  <td className="text-right py-2 px-2 opacity-70 whitespace-nowrap">
                    {hasData ? m.fmt(base) : '—'}
                  </td>
                  <td className="text-right py-2 px-2 font-medium whitespace-nowrap">
                    {hasData ? m.fmt(curr) : '—'}
                  </td>
                  <td className="text-right py-2 pl-2 whitespace-nowrap">
                    {delta === null || delta === undefined ? (
                      <span className="opacity-30">—</span>
                    ) : (
                      <DeltaPill delta={delta} />
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <p className="text-[11px] opacity-50 leading-relaxed">{t('progress.footer')}</p>
    </div>
  )
}

function DeltaPill({ delta }) {
  if (Math.abs(delta) < 0.005) {
    return <span className="text-xs opacity-50">≈</span>
  }
  const improved = delta > 0
  return (
    <span
      className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs font-medium ${
        improved
          ? 'bg-green-500/15 text-green-500'
          : 'bg-red-500/15 text-red-400'
      }`}
    >
      {improved ? '↑' : '↓'}
      {Math.abs(delta).toFixed(2)}
    </span>
  )
}
