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

  // lowerIsBetter: true means a NEGATIVE delta is an improvement
  // (stress goes from 9 to 4 = -5 = good). All others: positive delta =
  // improvement. Colour mapping (red進步/綠退步) handled in DeltaPill per
  // Taiwan stock-market convention. Sleep + habit metrics dropped per
  // 2026-06-29 user feedback ("沒什麼用") — they were rendering as "—"
  // for most accounts and the row clutter outweighed the signal.
  const METRIC_DEFS = [
    { key: 'avg_sentiment', label: t('progress.metric.avgSentiment'), fmt: (v) => v?.toFixed(2), lowerIsBetter: false },
    { key: 'avg_stress',    label: t('progress.metric.avgStress'),    fmt: (v) => v?.toFixed(2), lowerIsBetter: true },
    { key: 'journal_days',  label: t('progress.metric.journalDays'),  fmt: (v) => `${v}/7`,      lowerIsBetter: false },
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
                      <DeltaPill delta={delta} lowerIsBetter={m.lowerIsBetter} />
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

function DeltaPill({ delta, lowerIsBetter = false }) {
  if (Math.abs(delta) < 0.005) {
    return <span className="text-xs opacity-50">≈</span>
  }
  // Color convention follows Taiwan / 大中華 stock market style: RED = 進步
  // (price up / improvement), GREEN = 退步 (price down / regression). The
  // opposite of Western traffic-light convention. Arrow keeps showing the
  // literal numeric direction (↑/↓) regardless.
  //   sentiment 0.6 → 0.8  : delta +0.2, isImprovement=true  → 紅 (進步)
  //   sentiment 0.8 → 0.5  : delta -0.3, isImprovement=false → 綠 (退步)
  //   stress    7   → 5    : delta -2.0, isImprovement=true  → 紅 (進步)
  //   stress    4   → 9    : delta +5.0, isImprovement=false → 綠 (退步)
  const direction = delta > 0 ? 'up' : 'down'
  const isImprovement = lowerIsBetter ? delta < 0 : delta > 0
  return (
    <span
      className={`inline-flex items-center gap-0.5 px-2 py-0.5 rounded-full text-xs font-medium ${
        isImprovement
          ? 'bg-red-500/15 text-red-500'
          : 'bg-green-500/15 text-green-600 dark:text-green-400'
      }`}
    >
      {direction === 'up' ? '↑' : '↓'}
      {Math.abs(delta).toFixed(2)}
    </span>
  )
}
