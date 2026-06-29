// Replaces the raw scatter plot in the "身心關聯" dashboard section with
// a bucketed bar chart that a non-statistician can read at a glance.
//
// Inputs:
//   scatterData: [{ <xKey>: number, sentiment: number }, ...] — same shape
//                the old LazyScatterChart consumed (from the analytics API)
//   buckets:     [{ label, min, max }] — left-inclusive, right-exclusive;
//                last bucket's max should be Infinity to catch the tail
//   xKey:        property name on each scatter point holding the X value
//   barColor:    bar fill colour
//
// Renders:
//   1. One-line plain-Chinese summary above the chart
//      ("X 區段平均心情 +0.5；Y 區段 -0.2 — 看起來 X 對你比較有利")
//   2. Bar chart with average sentiment per bucket, sample count label
//      under each bucket name, value label above each bar.
//   3. Auto-hides any bucket that has zero samples (cleaner than a gap).

import { useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LabelList, ReferenceLine } from 'recharts'
import { useLang } from '../../context/LanguageContext'

function barColor(avg) {
  // Sentiment is in [-1, +1]; colour by sign + magnitude so the visual
  // matches the meaning: green = positive mood, amber = neutral, red = low.
  if (avg >= 0.3) return '#10b981'      // strong positive
  if (avg >= 0.1) return '#34d399'      // mild positive
  if (avg >= -0.1) return '#fbbf24'     // neutral
  if (avg >= -0.3) return '#fb923c'     // mild negative
  return '#e11d48'                       // strong negative
}

export default function BucketedMoodBar({
  scatterData,
  buckets,
  xKey,
  height = 220,
  gridStroke,
  axisStroke,
  tooltipStyle,
}) {
  const { t } = useLang()

  const bucketed = useMemo(() => {
    if (!scatterData?.length) return []
    const grouped = buckets.map((b) => ({
      label: b.label,
      min: b.min,
      max: b.max,
      values: [],
    }))
    for (const pt of scatterData) {
      const x = Number(pt?.[xKey])
      const y = Number(pt?.sentiment)
      if (!Number.isFinite(x) || !Number.isFinite(y)) continue
      const bucket = grouped.find((b) => x >= b.min && x < b.max)
      if (bucket) bucket.values.push(y)
    }
    return grouped
      .filter((b) => b.values.length > 0)
      .map((b) => ({
        bucket: b.label,
        avg: Math.round(
          (b.values.reduce((s, v) => s + v, 0) / b.values.length) * 100,
        ) / 100,
        count: b.values.length,
      }))
  }, [scatterData, buckets, xKey])

  const summary = useMemo(() => {
    if (bucketed.length < 2) return null
    const best = bucketed.reduce((a, b) => (b.avg > a.avg ? b : a))
    const worst = bucketed.reduce((a, b) => (b.avg < a.avg ? b : a))
    const gap = (best.avg - worst.avg).toFixed(2)
    if (best.bucket === worst.bucket) return null
    return t('dashboard.bucketSummary', {
      best: best.bucket,
      bestAvg: best.avg.toFixed(2),
      worst: worst.bucket,
      worstAvg: worst.avg.toFixed(2),
      gap,
    })
  }, [bucketed, t])

  if (!bucketed.length) return null

  return (
    <div className="space-y-3">
      {summary && (
        <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
          {summary}
        </p>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={bucketed} margin={{ top: 24, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
          <XAxis
            dataKey="bucket"
            stroke={axisStroke}
            tick={{ fill: axisStroke, fontSize: 12 }}
          />
          <YAxis
            stroke={axisStroke}
            tick={{ fill: axisStroke }}
            domain={[-1, 1]}
            ticks={[-1, -0.5, 0, 0.5, 1]}
          />
          <ReferenceLine y={0} stroke={axisStroke} strokeDasharray="3 3" strokeOpacity={0.5} />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value, _name, ctx) => [
              `${value.toFixed(2)} (${t('dashboard.bucketSamples', { n: ctx?.payload?.count || 0 })})`,
              t('dashboard.bucketAvgMood'),
            ]}
          />
          <Bar dataKey="avg" radius={[8, 8, 0, 0]}>
            {bucketed.map((b, i) => (
              <Cell key={`c-${i}`} fill={barColor(b.avg)} />
            ))}
            <LabelList
              dataKey="avg"
              position="top"
              formatter={(v) => v.toFixed(2)}
              style={{ fill: axisStroke, fontSize: 13, fontWeight: 600 }}
            />
            <LabelList
              dataKey="count"
              position="insideBottom"
              formatter={(v) => `n=${v}`}
              style={{ fill: 'white', fontSize: 11, fontWeight: 500 }}
            />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
