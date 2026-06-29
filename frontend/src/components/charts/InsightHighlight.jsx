// Card-based replacement for both the original scatter+Pearson plot AND
// the bucketed bar chart. Both visuals still required the user to read
// numbers off axes; this version puts the conclusion in plain text:
//
//   你睡 7-8 小時時心情通常最高 (+0.52)
//   你睡 <6 小時時心情通常最低 (+0.12)
//   差距 0.40 — 看起來睡夠對你比較重要
//
// Renders nothing when the data is too sparse to draw a conclusion
// (need at least 2 distinct buckets with ≥3 samples each).

import { useMemo } from 'react'
import { useLang } from '../../context/LanguageContext'

const MIN_SAMPLES_PER_BUCKET = 3

export default function InsightHighlight({ scatterData, buckets, xKey, metricName }) {
  const { t } = useLang()

  const computed = useMemo(() => {
    if (!scatterData?.length) return null
    const grouped = buckets.map((b) => ({
      label: b.label,
      values: [],
    }))
    for (const pt of scatterData) {
      const x = Number(pt?.[xKey])
      const y = Number(pt?.sentiment)
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue
      const idx = buckets.findIndex((b) => x >= b.min && x < b.max)
      if (idx >= 0) grouped[idx].values.push(y)
    }
    const valid = grouped
      .map((b) => ({
        label: b.label,
        count: b.values.length,
        avg: b.values.length ? b.values.reduce((s, v) => s + v, 0) / b.values.length : null,
      }))
      .filter((b) => b.count >= MIN_SAMPLES_PER_BUCKET)
    if (valid.length < 2) return null
    const best = valid.reduce((a, b) => (b.avg > a.avg ? b : a))
    const worst = valid.reduce((a, b) => (b.avg < a.avg ? b : a))
    if (best.label === worst.label) return null
    return {
      best,
      worst,
      gap: best.avg - worst.avg,
      allBuckets: valid,
      total: valid.reduce((s, b) => s + b.count, 0),
    }
  }, [scatterData, buckets, xKey])

  if (!computed) {
    return (
      <p className="text-sm opacity-60">
        {t('dashboard.insightNotEnoughData', { metric: metricName })}
      </p>
    )
  }

  const { best, worst, gap, total } = computed
  const gapMagnitude = gap >= 0.4 ? 'strong' : gap >= 0.2 ? 'mild' : 'subtle'
  const interpretation = t(`dashboard.insightInterpretation.${gapMagnitude}`, {
    metric: metricName,
    best: best.label,
  })

  return (
    <div className="space-y-3">
      {/* Two highlighted rows: best + worst */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="rounded-xl border-l-4 border-green-500 bg-green-500/5 p-3">
          <div className="text-xs opacity-60 mb-1">{t('dashboard.insightHigh')}</div>
          <div className="flex items-baseline gap-2 flex-wrap">
            <span className="font-semibold text-base">{best.label}</span>
            <span className="text-lg font-bold text-green-600 dark:text-green-400">
              {best.avg >= 0 ? '+' : ''}{best.avg.toFixed(2)}
            </span>
          </div>
          <div className="text-xs opacity-50 mt-1">
            {t('dashboard.insightSampleCount', { n: best.count })}
          </div>
        </div>
        <div className="rounded-xl border-l-4 border-rose-500 bg-rose-500/5 p-3">
          <div className="text-xs opacity-60 mb-1">{t('dashboard.insightLow')}</div>
          <div className="flex items-baseline gap-2 flex-wrap">
            <span className="font-semibold text-base">{worst.label}</span>
            <span className="text-lg font-bold text-rose-600 dark:text-rose-400">
              {worst.avg >= 0 ? '+' : ''}{worst.avg.toFixed(2)}
            </span>
          </div>
          <div className="text-xs opacity-50 mt-1">
            {t('dashboard.insightSampleCount', { n: worst.count })}
          </div>
        </div>
      </div>

      {/* Plain-language interpretation */}
      <p className="text-sm leading-relaxed text-[var(--text-secondary)]">
        {t('dashboard.insightGap', { gap: gap.toFixed(2), n: total })}
        {' '}
        {interpretation}
      </p>
    </div>
  )
}
