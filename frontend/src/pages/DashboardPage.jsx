import { useState, useEffect, useMemo, useRef, lazy, Suspense } from 'react'
import { useNavigate } from 'react-router-dom'
import { getAnalytics } from '../api/analytics'
import { getHealthSummary } from '../api/health'
import { useTheme } from '../context/ThemeContext'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'
import { usePerformance } from '../hooks/usePerformance'
import SkeletonCard from '../components/SkeletonCard'
import MoodCalendar from '../components/MoodCalendar'
import YearInPixels from '../components/YearInPixels'
import EmptyState from '../components/EmptyState'
import MoodPrediction from '../components/MoodPrediction'
import ProgressCompareCard from '../components/ProgressCompareCard'
import DashboardSection from '../components/DashboardSection'
import SectionAnchorBar from '../components/SectionAnchorBar'
import PersonalInsights from '../components/PersonalInsights'
import { Card } from '../components/ui'
import { ResponsiveContainer, LineChart, CartesianGrid, XAxis, YAxis, Tooltip, Line } from 'recharts'
const LazyLineChart = lazy(() => import('../components/charts/LazyLineChart'))
const LazyScatterChart = lazy(() => import('../components/charts/LazyScatterChart'))
const LazyBarChart = lazy(() => import('../components/charts/LazyBarChart'))
const StressRadarChart = lazy(() => import('../components/StressRadarChart'))

const ChartSkeleton = () => (
  <div className="w-full h-[300px] flex items-center justify-center opacity-50">
    <div className="animate-pulse text-sm">{/* Loading chart... */}</div>
  </div>
)

// Detect whether the user is on the native mobile shell or the browser.
// Web users have no Apple Health / Health Connect / native sensors, so
// widgets that ONLY light up with those data sources should be hidden on
// web instead of showing a persistent "no data" placeholder that the user
// can't act on (the "去設定健康同步" button leads to a settings tab whose
// integrations are mobile-only).
function isNativePlatform() {
  try {
    return (typeof window !== 'undefined') &&
           !!window?.Capacitor?.isNativePlatform?.()
  } catch {
    return false
  }
}

export default function DashboardPage() {
  usePerformance('DashboardPage', 50)
  const navigate = useNavigate()
  const { theme } = useTheme()
  const { t } = useLang()
  const toast = useToast()
  const [data, setData] = useState(null)
  const [healthData, setHealthData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [period, setPeriod] = useState('week')
  // 180 days default: long enough for casual journalers to populate the
  // tag-driven widgets (tags are usually accumulated over months, not
  // days). Dropdown options below stretch from 7d to 365d so power
  // users can narrow / widen explicitly.
  const [lookback, setLookback] = useState(180)
  const fetchIdRef = useRef(0)

  useEffect(() => { document.title = `${t('nav.dashboard')} — ${t('app.name')}` }, [t])

  useEffect(() => {
    const fetchId = ++fetchIdRef.current
    setLoading(true)
    setError(false)
    Promise.all([
      getAnalytics(period, lookback),
      getHealthSummary(lookback).catch(() => null),
    ])
      .then(([analyticsRes, healthRes]) => {
        if (fetchId === fetchIdRef.current) {
          setData(analyticsRes.data)
          if (healthRes) setHealthData(healthRes.data)
        }
      })
      .catch(() => {
        if (fetchId === fetchIdRef.current) {
          setError(true)
          toast?.error(t('dashboard.loadFailed'))
        }
      })
      .finally(() => {
        if (fetchId === fetchIdRef.current) setLoading(false)
      })
  }, [period, lookback])

  const trends = useMemo(() => data?.mood_trends || [], [data])
  const correlation = useMemo(() => data?.weather_correlation || {}, [data])
  const tags = useMemo(() => data?.frequent_tags || [], [data])
  const stressByTag = useMemo(() => data?.stress_by_tag || [], [data])
  const activityCorrelation = useMemo(() =>
    (data?.activity_correlation || []).map(item => ({
      ...item,
      name: t(`activities.${item.name}`) !== `activities.${item.name}` ? t(`activities.${item.name}`) : item.name,
    })),
  [data, t])
  const sleepCorrelation = useMemo(() => data?.sleep_correlation || {}, [data])
  // health_mood_correlation comes from getHealthSummary (not the main
  // analytics endpoint). Backend already computes Pearson r + scatter
  // points for steps / heart_rate / hrv / exercise_minutes / active_calories
  // vs daily mood — we just need to render them as scatter charts.
  const healthMoodCorr = useMemo(() => healthData?.health_mood_correlation || {}, [healthData])
  const HEALTH_METRIC_LABEL = useMemo(() => ({
    steps: { key: 'health.steps', color: '#60a5fa' },
    heart_rate: { key: 'health.heartRate', color: '#f87171' },
    hrv: { key: 'health.hrv', color: '#fb923c' },
    active_calories: { key: 'health.calories', color: '#fbbf24' },
    exercise_minutes: { key: 'health.exerciseMinutes', color: '#4ade80' },
  }), [])

  // Theme-aware chart colors
  const gridStroke = useMemo(() => theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)', [theme])
  const axisStroke = useMemo(() => theme === 'dark' ? '#9ca3af' : '#475569', [theme])
  const tooltipStyle = useMemo(() => ({
    background: theme === 'dark' ? 'rgba(30,20,60,0.9)' : 'rgba(255,255,255,0.95)',
    border: `1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)'}`,
    borderRadius: '8px',
    color: theme === 'dark' ? '#e2e8f0' : '#1e293b',
  }), [theme])

  if (loading && !data) return (
    <div className="space-y-6 mt-4">
      <SkeletonCard lines={2} />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <SkeletonCard lines={6} />
        <SkeletonCard lines={6} />
      </div>
      <SkeletonCard lines={4} />
    </div>
  )

  if (error && !data) return (
    <div className="flex flex-col items-center justify-center py-20 opacity-60">
      <p className="text-lg mb-4">{t('dashboard.loadFailed')}</p>
      <button className="btn-primary" onClick={() => { setError(false); setLoading(true); getAnalytics(period, lookback).then((res) => setData(res.data)).catch(() => setError(true)).finally(() => setLoading(false)) }}>
        {t('common.retry')}
      </button>
    </div>
  )

  // 5-bucket categorization so the page reads as chapters rather than a
  // 3000px wall of disparate charts. Order is deliberate: overview first
  // (above the fold), patterns and body-mind feed the user's curiosity,
  // health snapshot is reference data, history goes last (tall and
  // exploratory, not glanceable). 2026-06-01 reorg.
  const SECTIONS = [
    { id: 'overview',  label: t('dashboard.section.overview'),       icon: '/icons/mood-report.svg' },
    { id: 'patterns',  label: t('dashboard.section.patterns'),       icon: '/icons/activity.svg' },
    { id: 'body-mind', label: t('dashboard.section.bodyMind'),       icon: '/icons/brain.svg' },
    { id: 'health',    label: t('dashboard.section.healthSnapshot'), icon: '/icons/nav-health.svg' },
    { id: 'history',   label: t('dashboard.section.history'),        icon: '/icons/weekly-report.svg' },
  ]

  return (
    <div className="space-y-10 mt-6 pb-8">
      <SectionAnchorBar sections={SECTIONS} />

      {/* ===== A. OVERVIEW ===== */}
      <DashboardSection
        id="overview"
        title={t('dashboard.section.overview')}
        subtitle={t('dashboard.section.overviewSub')}
        icon="/icons/mood-report.svg"
      >
      <ProgressCompareCard />
      <MoodPrediction />

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Streak stats */}
        {(data?.current_streak > 0 || data?.longest_streak > 0) && (
          <Card padding="md" className="bg-gradient-to-br from-orange-500/10 to-red-500/10 border-orange-500/20">
            <div className="flex flex-wrap items-center gap-6">
              {data?.current_streak > 0 && (
                <div className="flex items-center gap-3">
                  <img src="/icons/flame.svg" alt="" aria-hidden="true" className="w-10 h-10 object-contain" />
                  <div>
                    <div className="text-sm text-[var(--text-tertiary)] mb-0.5">{t('dashboard.currentStreak')}</div>
                    <div className="text-xl font-bold text-[var(--text-primary)]">
                      {data.current_streak} {t(data.current_streak === 1 ? 'dashboard.day' : 'dashboard.days')}
                    </div>
                  </div>
                </div>
              )}
              {data?.longest_streak > 0 && (
                <div className="flex items-center gap-3 opacity-80">
                  <img src="/icons/trophy.svg" alt="" aria-hidden="true" className="w-10 h-10 object-contain" />
                  <div>
                    <div className="text-sm text-[var(--text-tertiary)] mb-0.5">{t('dashboard.bestStreak')}</div>
                    <div className="text-lg font-semibold text-[var(--text-primary)]">
                      {data.longest_streak} {t(data.longest_streak === 1 ? 'dashboard.day' : 'dashboard.days')}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </Card>
        )}

        {/* Gratitude stats */}
        {(data?.gratitude_count > 0 || data?.gratitude_streak > 0) && (
          <Card padding="md" className="bg-gradient-to-br from-orange-500/10 to-rose-500/10 border-orange-500/20">
            <div className="flex flex-wrap items-center gap-6">
              {data?.gratitude_count > 0 && (
                <div className="flex items-center gap-3">
                  <span className="text-3xl">🙏</span>
                  <div>
                    <div className="text-sm text-[var(--text-tertiary)] mb-0.5">{t('dashboard.gratitudeNotes')}</div>
                    <div className="text-xl font-bold text-[var(--text-primary)]">
                      {data.gratitude_count}
                    </div>
                  </div>
                </div>
              )}
              {data?.gratitude_streak > 0 && (
                <div className="flex items-center gap-3 opacity-80">
                  <span className="text-3xl">✨</span>
                  <div>
                    <div className="text-sm text-[var(--text-tertiary)] mb-0.5">{t('dashboard.gratitudeStreak')}</div>
                    <div className="text-lg font-semibold text-[var(--text-primary)]">
                      {data.gratitude_streak} {t(data.gratitude_streak === 1 ? 'dashboard.day' : 'dashboard.days')}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </Card>
        )}
      </div>

      {/* Controls */}
      <Card padding="md" className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-400">{t('dashboard.period')}</span>
          <select
            value={period}
            onChange={(e) => setPeriod(e.target.value)}
            className="glass-input w-auto text-sm"
          >
            <option value="week">{t('dashboard.periodWeek')}</option>
            <option value="month">{t('dashboard.periodMonth')}</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-sm text-slate-400">{t('dashboard.lookback')}</span>
          <select
            value={lookback}
            onChange={(e) => setLookback(Number(e.target.value))}
            className="glass-input w-auto text-sm"
          >
            <option value={7}>{t('dashboard.days7')}</option>
            <option value={30}>{t('dashboard.days30')}</option>
            <option value={90}>{t('dashboard.days90')}</option>
            <option value={180}>{t('dashboard.days180')}</option>
            <option value={365}>{t('dashboard.days365')}</option>
          </select>
        </div>
      </Card>

      {/* Mood Trends */}
      <Card padding="lg">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">{t('dashboard.moodTrends')}</h2>
        </div>
        <p className="text-xs opacity-50 mb-4">
          {t('dashboard.dataWindowNoCount', { days: data?.actual_lookback_days || lookback })}
        </p>
        {trends.length === 0 ? (
          <EmptyState
            title={t('dashboard.noTrends')}
            description={t('dashboard.noTrendsDesc')}
            actionText={t('dashboard.goWrite')}
            onAction={() => navigate('/')}
          />
        ) : (
          <>
            <div role="img" aria-label={t('dashboard.moodTrends')}>
              <Suspense fallback={<ChartSkeleton />}>
                <LazyLineChart
                  data={trends}
                  xAxisKey="name"
                  height={300}
                  gridStroke={gridStroke}
                  axisStroke={axisStroke}
                  tooltipStyle={tooltipStyle}
                  showLegend
                  lines={[
                    { dataKey: 'avg_sentiment', stroke: '#fb923c', name: t('dashboard.avgSentiment'), strokeWidth: 2 },
                    { dataKey: 'avg_stress', stroke: '#f87171', name: t('dashboard.avgStress'), strokeWidth: 2 },
                  ]}
                />
              </Suspense>
            </div>
            <table className="sr-only">
              <caption>{t('dashboard.moodTrends')}</caption>
              <thead><tr><th>Period</th><th>{t('dashboard.avgSentiment')}</th><th>{t('dashboard.avgStress')}</th></tr></thead>
              <tbody>{trends.map((r, i) => <tr key={i}><td>{r.name}</td><td>{r.avg_sentiment}</td><td>{r.avg_stress}</td></tr>)}</tbody>
            </table>
          </>
        )}
      </Card>
      </DashboardSection>

      {/* ===== B. PATTERNS ===== */}
      <DashboardSection
        id="patterns"
        title={t('dashboard.section.patterns')}
        subtitle={t('dashboard.section.patternsSub')}
        icon="/icons/activity.svg"
      >
      {/* Weather Correlation */}
      <Card padding="lg">
        <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-4">{t('dashboard.weatherCorrelation')}</h2>
        {(correlation.mood_by_temperature?.length || 0) >= 2 ? (
          <>
            {/* Headline: which temperature range correlates with the
                user's best mood. Reads at a glance — no statistics
                background required. Pearson r line removed — meaningless
                to a non-stats user; the chart + headline together
                communicate the relationship plenty. */}
            {correlation.best_temp_bucket && (
              <p className="text-base mb-2">
                <span className="opacity-70">{t('dashboard.bestMoodAt')}</span>{' '}
                <span className="font-bold text-orange-500">
                  {correlation.best_temp_bucket.bucket}°C
                </span>
                <span className="opacity-70 text-sm ml-2">
                  ({t('dashboard.avgMood')}: {correlation.best_temp_bucket.avg_sentiment.toFixed(2)},{' '}
                  n={correlation.best_temp_bucket.count})
                </span>
              </p>
            )}
            <p className="text-xs opacity-50 mb-4">
              {t('dashboard.dataWindow', { days: data?.actual_lookback_days || lookback, count: correlation.sample_size })}
            </p>
            <Suspense fallback={<ChartSkeleton />}>
              <LazyBarChart
                data={correlation.mood_by_temperature.map(b => ({
                  name: `${b.bucket}°C`,
                  value: b.avg_sentiment,
                  count: b.count,
                }))}
                xAxisKey="name"
                height={260}
                gridStroke={gridStroke}
                axisStroke={axisStroke}
                tooltipStyle={tooltipStyle}
                bars={[{ name: t('dashboard.avgMood'), fill: '#fb923c', dataKey: 'value' }]}
                yDomain={[-1, 1]}
                showCountLabel={true}
              />
            </Suspense>
            <p className="text-xs opacity-50 mt-2">
              {t('dashboard.weatherHint')}
            </p>
          </>
        ) : (
          <EmptyState
            title={t('dashboard.noCorrelation')}
            description={t('dashboard.noCorrelationDesc')}
            actionText={t('dashboard.goWrite')}
            onAction={() => navigate('/')}
          />
        )}
      </Card>

      {/* Activity-Mood Correlation (placed before tag widgets so the
          tag-driven cards group together below). */}
      {activityCorrelation.length > 0 && (
        <div className="glass p-6">
          <h2 className="text-lg font-semibold mb-4">{t('dashboard.activityCorrelation')}</h2>
          <p className="text-xs opacity-50 mb-3">
            {t('dashboard.dataWindowNoCount', { days: data?.actual_lookback_days || lookback })}
          </p>
          <Suspense fallback={<ChartSkeleton />}>
            <LazyBarChart
              data={activityCorrelation}
              xAxisKey="name"
              height={250}
              gridStroke={gridStroke}
              axisStroke={axisStroke}
              tooltipStyle={tooltipStyle}
              bars={[
                { dataKey: 'avg_sentiment', name: t('dashboard.avgSentiment'), fill: '#fb923c' },
              ]}
            />
          </Suspense>
        </div>
      )}

      {/* Tag-driven widgets grouped: 常用標籤 + 壓力雷達 are BOTH derived
          from the user's tag usage. Side-by-side on desktop, stacked on
          mobile. Single Card wrapper so the visual "this is one section
          about your tags" reads at a glance. */}
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-1">{t('dashboard.tagsSectionTitle')}</h2>
        <p className="text-xs opacity-50 mb-5">
          {t('dashboard.dataWindowNoCount', { days: data?.actual_lookback_days || lookback })}
        </p>
        {/* 2-col grid on desktop, stack on mobile. Each side gets a
            matching mini-card so left and right have visual parity (no
            more "left is bare, right has a card" asymmetry). */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="rounded-xl border border-white/5 bg-white/[0.03] p-4 min-h-[320px] flex flex-col">
            <h3 className="text-sm font-medium opacity-80 mb-3">{t('dashboard.frequentTags')}</h3>
            {tags.length === 0 ? (
              <div className="flex-1 flex items-center">
                <EmptyState
                  title={t('dashboard.noTags')}
                  description={t('dashboard.noTagsDesc')}
                  actionText={t('dashboard.goWrite')}
                  onAction={() => navigate('/')}
                />
              </div>
            ) : (
              <div role="img" aria-label={t('dashboard.frequentTags')} className="flex-1">
                <Suspense fallback={<ChartSkeleton />}>
                  <LazyBarChart
                    data={tags}
                    xAxisKey="name"
                    height={280}
                    gridStroke={gridStroke}
                    axisStroke={axisStroke}
                    tooltipStyle={tooltipStyle}
                    bars={[
                      { dataKey: 'count', name: t('dashboard.tagCount'), fill: '#C2410C' },
                    ]}
                    yDomain={[0, 'auto']}
                  />
                </Suspense>
              </div>
            )}
          </div>
          <div className="rounded-xl border border-white/5 bg-white/[0.03] p-4 min-h-[320px] flex flex-col">
            <h3 className="text-sm font-medium opacity-80 mb-3">{t('dashboard.stressRadarTitle')}</h3>
            <div className="flex-1">
              <Suspense fallback={<ChartSkeleton />}>
                <StressRadarChart data={stressByTag} bare />
              </Suspense>
            </div>
          </div>
        </div>
      </div>
      </DashboardSection>

      {/* ===== C. BODY & MIND ===== */}
      {/* Web has no Apple Health / Health Connect / native sensors, so
          sleep/heart-rate/steps correlations can never light up without
          the mobile app. Skip the entire section on web when there's
          no data — the "set up health sync" CTA leads to a tab whose
          integrations are mobile-only, so it's actively misleading. On
          native, keep the empty state so the user knows what to enable. */}
      {(sleepCorrelation.scatter_data?.length > 0 ||
        Object.keys(healthMoodCorr).length > 0 ||
        isNativePlatform()) && (
      <DashboardSection
        id="body-mind"
        title={t('dashboard.section.bodyMind')}
        subtitle={t('dashboard.section.bodyMindSub')}
        icon="/icons/brain.svg"
      >
      {sleepCorrelation.scatter_data?.length > 0 || Object.keys(healthMoodCorr).length > 0 ? null : (
        <EmptyState
          title={t('dashboard.bodyMindEmptyTitle')}
          description={t('dashboard.bodyMindEmptyDesc')}
          actionText={t('dashboard.bodyMindEmptyAction')}
          onAction={() => navigate('/settings', { state: { tab: 'health' } })}
        />
      )}
      {/* Sleep-Mood Correlation */}
      {sleepCorrelation.scatter_data?.length > 0 && (
        <div className="glass p-6">
          <h2 className="text-lg font-semibold mb-2">{t('dashboard.sleepCorrelation')}</h2>
          {sleepCorrelation.hours_correlation != null && (
            <p className="text-sm opacity-60 mb-4">
              {t('dashboard.pearson', {
                r: sleepCorrelation.hours_correlation,
                p: sleepCorrelation.hours_p_value,
                n: sleepCorrelation.sample_size,
              })}
            </p>
          )}
          <Suspense fallback={<ChartSkeleton />}>
            <LazyScatterChart
              data={sleepCorrelation.scatter_data}
              xAxisKey="sleep_hours"
              yAxisKey="sentiment"
              height={250}
              gridStroke={gridStroke}
              axisStroke={axisStroke}
              tooltipStyle={tooltipStyle}
              scatters={[
                { name: t('dashboard.sleepHoursLabel'), fill: '#60a5fa', data: sleepCorrelation.scatter_data },
              ]}
            />
          </Suspense>
        </div>
      )}

      {/* Health-Mood Correlation — one scatter card per metric type that
          has enough samples (backend min: 3 days of overlap). Pearson r,
          p-value, and scatter points come from get_health_mood_correlation.
          Order is fixed via HEALTH_METRIC_LABEL so cards appear in the
          same sequence regardless of dict iteration. Inline header is
          omitted now that the parent DashboardSection provides one. */}
      {Object.keys(healthMoodCorr).length > 0 && (
        <div className="space-y-4">
          {Object.entries(HEALTH_METRIC_LABEL).map(([metricType, meta]) => {
            const corr = healthMoodCorr[metricType]
            if (!corr?.scatter_data?.length) return null
            const label = t(meta.key)
            return (
              <div key={metricType} className="glass p-6">
                <h3 className="text-md font-semibold mb-2">
                  {t('dashboard.healthMoodCardTitle', { metric: label })}
                </h3>
                {corr.correlation != null && (
                  <p className="text-sm opacity-60 mb-4">
                    {t('dashboard.pearson', {
                      r: corr.correlation,
                      p: corr.p_value,
                      n: corr.sample_size,
                    })}
                  </p>
                )}
                <Suspense fallback={<ChartSkeleton />}>
                  <LazyScatterChart
                    data={corr.scatter_data}
                    xAxisKey="value"
                    yAxisKey="sentiment"
                    height={220}
                    gridStroke={gridStroke}
                    axisStroke={axisStroke}
                    tooltipStyle={tooltipStyle}
                    scatters={[
                      { name: label, fill: meta.color, data: corr.scatter_data },
                    ]}
                  />
                </Suspense>
              </div>
            )
          })}
        </div>
      )}

      </DashboardSection>
      )}

      {/* ===== D. HEALTH SNAPSHOT ===== */}
      {/* Same web-skip rule as Body & Mind: the Health Snapshot widget
          (steps / heart rate / HRV trend) is driven entirely by native
          Health-platform sync. On web the section has nothing to show,
          so suppress it instead of rendering a permanent empty card. */}
      {(healthData?.summary && Object.keys(healthData.summary).length > 0) || isNativePlatform() ? (
      <DashboardSection
        id="health"
        title={t('dashboard.section.healthSnapshot')}
        subtitle={t('dashboard.section.healthSnapshotSub')}
        icon="/icons/nav-health.svg"
      >
      {/* Health Overview */}
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('health.dashboardTitle')}</h2>

        {healthData?.summary && Object.keys(healthData.summary).length > 0 ? (
          <>
            {/* Health metric cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-6">
            {healthData.summary.steps && (
              <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20">
                <p className="text-xs text-slate-400">{t('health.steps')}</p>
                <p className="text-lg font-bold text-blue-400">
                  {Math.round(healthData.summary.steps.latest || 0).toLocaleString()}
                </p>
                <p className="text-xs opacity-50">
                  {t('health.avg')}: {Math.round(healthData.summary.steps.avg || 0).toLocaleString()}
                </p>
              </div>
            )}
            {healthData.summary.heart_rate && (
              <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20">
                <p className="text-xs text-slate-400">{t('health.heartRate')}</p>
                <p className="text-lg font-bold text-red-400">
                  {Math.round(healthData.summary.heart_rate.latest || 0)} bpm
                </p>
                <p className="text-xs opacity-50">
                  {t('health.avg')}: {Math.round(healthData.summary.heart_rate.avg || 0)} bpm
                </p>
              </div>
            )}
            {healthData.summary.hrv && (
              <div className="p-3 rounded-xl bg-orange-500/10 border border-orange-500/20">
                <p className="text-xs text-slate-400">{t('health.hrv')}</p>
                <p className="text-lg font-bold text-orange-400">
                  {Math.round(healthData.summary.hrv.latest || 0)} ms
                </p>
                <p className="text-xs opacity-50">
                  {t('health.avg')}: {Math.round(healthData.summary.hrv.avg || 0)} ms
                </p>
              </div>
            )}
            {healthData.summary.active_calories && (
              <div className="p-3 rounded-xl bg-orange-500/10 border border-orange-500/20">
                <p className="text-xs text-slate-400">{t('health.calories')}</p>
                <p className="text-lg font-bold text-orange-400">
                  {Math.round(healthData.summary.active_calories.latest || 0)} kcal
                </p>
                <p className="text-xs opacity-50">
                  {t('health.avg')}: {Math.round(healthData.summary.active_calories.avg || 0)} kcal
                </p>
              </div>
            )}
            {healthData.summary.exercise_minutes && (
              <div className="p-3 rounded-xl bg-green-500/10 border border-green-500/20">
                <p className="text-xs text-slate-400">{t('health.exerciseMinutes')}</p>
                <p className="text-lg font-bold text-green-400">
                  {Math.round(healthData.summary.exercise_minutes.latest || 0)} {t('health.min')}
                </p>
                <p className="text-xs opacity-50">
                  {t('health.avg')}: {Math.round(healthData.summary.exercise_minutes.avg || 0)} {t('health.min')}
                </p>
              </div>
            )}
            {healthData.summary.sleep && (
              <div className="p-3 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
                <p className="text-xs text-slate-400">{t('health.sleepData')}</p>
                <p className="text-lg font-bold text-indigo-400">
                  {healthData.summary.sleep.avg_hours || '-'} h
                </p>
                <p className="text-xs opacity-50">
                  {t('health.quality')}: {healthData.summary.sleep.avg_quality || '-'}/5
                </p>
              </div>
            )}
          </div>

          {/* Steps trend chart */}
          {healthData.summary.steps?.trend?.length > 1 && (
            <div className="mt-4">
              <h3 className="text-sm font-medium mb-2 text-slate-400">{t('health.stepsTrend')}</h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={healthData.summary.steps.trend.map(d => ({
                  name: d.date?.slice(5),
                  value: d.value,
                }))}>
                  <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                  <XAxis dataKey="name" stroke={axisStroke} fontSize={11} />
                  <YAxis stroke={axisStroke} fontSize={11} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Line type="monotone" dataKey="value" stroke="#60a5fa" strokeWidth={2} name={t('health.steps')} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
          </>
        ) : (
          /* Empty state when no health data */
          <div className="text-center py-8">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-blue-500/20 to-orange-500/20 flex items-center justify-center">
              <svg className="w-8 h-8 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold mb-2">{t('health.noData')}</h3>
            <p className="text-sm opacity-60 mb-4 max-w-md mx-auto">{t('health.noDataDesc')}</p>
            <button
              onClick={() => navigate('/settings', { state: { tab: 'health' } })}
              className="btn-primary text-sm"
            >
              {t('health.goToSettings')}
            </button>
          </div>
        )}
      </div>

      {/* Old Health-Mood text summary deleted 2026-06-01 — duplicated
          the new Body & Mind scatter cards which already render the
          same r/p/n values inline. Less noise, less cognitive load. */}
      {/* Old bottom-of-page Stress Radar moved up into Patterns section
          where it conceptually belongs. */}
      </DashboardSection>
      ) : null}

      {/* ===== E. HISTORY ===== */}
      <DashboardSection
        id="history"
        title={t('dashboard.section.history')}
        subtitle={t('dashboard.section.historySub')}
        icon="/icons/weekly-report.svg"
      >
      {/* PersonalInsights renders null when backend hasn't found any
          significant pattern yet — so the section just shows the calendar
          + year pixels for new users, and adds the insight cards on top
          once they accumulate enough data to surface trends. */}
      <PersonalInsights
        insights={data?.personal_insights}
        lookbackDays={data?.actual_lookback_days || lookback}
      />
      <MoodCalendar />
      <YearInPixels />
      </DashboardSection>
    </div>
  )
}
