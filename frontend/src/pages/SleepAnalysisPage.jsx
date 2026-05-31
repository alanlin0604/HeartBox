import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { getSleepAnalysis, getSleepTrends } from '../api/sleep'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'
import { Card, Button } from '../components/ui'
import SkeletonCard from '../components/SkeletonCard'
import SleepTrendsChart from '../components/sleep/SleepTrendsChart'
import SleepCorrelation from '../components/sleep/SleepCorrelation'
import DashboardSection from '../components/DashboardSection'

export default function SleepAnalysisPage() {
  const { t } = useLang()
  const toast = useToast()
  const [analysisData, setAnalysisData] = useState(null)
  const [trendsData, setTrendsData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [errored, setErrored] = useState(false)
  const [days, setDays] = useState(30)
  const fetchIdRef = useRef(0)

  useEffect(() => {
    document.title = `${t('sleep.analysisTitle')} — ${t('app.name')}`
  }, [t])

  useEffect(() => {
    const fetchId = ++fetchIdRef.current
    setLoading(true)
    setErrored(false)

    Promise.all([
      getSleepAnalysis(days),
      getSleepTrends(90)
    ])
      .then(([analysisRes, trendsRes]) => {
        if (fetchId === fetchIdRef.current) {
          setAnalysisData(analysisRes.data)
          setTrendsData(trendsRes.data)
          setErrored(false)
        }
      })
      .catch((err) => {
        if (fetchId === fetchIdRef.current) {
          console.error('Failed to load sleep analysis:', err)
          setErrored(true)
          setAnalysisData(null)
          setTrendsData(null)
          toast?.error(t('sleep.loadFailed'))
        }
      })
      .finally(() => {
        if (fetchId === fetchIdRef.current) {
          setLoading(false)
        }
      })
  }, [days, t, toast])

  const handleRetry = () => {
    setDays((d) => d)
    fetchIdRef.current++
    setErrored(false)
    setLoading(true)
    Promise.all([getSleepAnalysis(days), getSleepTrends(90)])
      .then(([a, tr]) => { setAnalysisData(a.data); setTrendsData(tr.data); setErrored(false) })
      .catch(() => setErrored(true))
      .finally(() => setLoading(false))
  }

  if (loading && !analysisData) {
    return (
      <div className="space-y-6 mt-4">
        <SkeletonCard lines={2} />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <SkeletonCard lines={4} />
          <SkeletonCard lines={4} />
          <SkeletonCard lines={4} />
        </div>
        <SkeletonCard lines={6} />
      </div>
    )
  }

  if (errored && !analysisData) {
    return (
      <div className="space-y-6 mt-4">
        <Card className="p-8 text-center">
          <div className="text-4xl mb-3">⚠️</div>
          <h2 className="text-xl font-semibold mb-2">{t('sleep.loadFailed')}</h2>
          <p className="text-[var(--text-secondary)] mb-4">{t('sleep.loadFailedHint')}</p>
          <Button onClick={handleRetry} variant="primary">{t('common.retry')}</Button>
        </Card>
      </div>
    )
  }

  // No sleep data yet — every stat slot is "--". Guide the user to add the
  // first entry instead of staring at an empty dashboard. Note backend keys:
  // `statistics.avg_sleep_hours` (NOT avg_duration) and `trends` (NOT points).
  const hasAnyData = !!(analysisData?.statistics?.avg_sleep_hours || trendsData?.trends?.length)
  if (!hasAnyData) {
    return (
      <div className="space-y-6 mt-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-rose-600 to-orange-600 bg-clip-text text-transparent">
              {t('sleep.analysisTitle')}
            </h1>
            <p className="text-[var(--text-secondary)] mt-2">{t('sleep.analysisSubtitle')}</p>
          </div>
        </div>
        <Card className="p-10 text-center">
          <div className="text-6xl mb-4">😴</div>
          <h2 className="text-xl font-semibold mb-2">{t('sleep.noDataTitle')}</h2>
          <p className="text-[var(--text-secondary)] mb-6 max-w-md mx-auto">{t('sleep.noDataHint')}</p>
          <div className="flex gap-3 justify-center flex-wrap">
            <Link to="/">
              <Button variant="primary">{t('sleep.startTracking')}</Button>
            </Link>
            <Link to="/habits">
              <Button variant="outline">{t('sleep.setSleepHabit')}</Button>
            </Link>
          </div>
        </Card>
      </div>
    )
  }

  const stats = analysisData?.statistics || {}
  const issues = analysisData?.issues || []
  const recommendations = analysisData?.recommendations || []

  return (
    <div className="space-y-6 mt-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-rose-600 to-orange-600 bg-clip-text text-transparent">
            {t('sleep.analysisTitle')}
          </h1>
          <p className="text-[var(--text-secondary)] mt-2">
            {t('sleep.analysisSubtitle')}
          </p>
        </div>
        <div className="flex gap-2">
          {[7, 30, 90].map(d => (
            <Button
              key={d}
              size="sm"
              variant={days === d ? 'primary' : 'outline'}
              onClick={() => setDays(d)}
            >
              {d} {t('common.days')}
            </Button>
          ))}
        </div>
      </div>

      {/* ===== A. SUMMARY ===== */}
      <DashboardSection id="sleep-summary" title={t('sleep.section.summary')} icon="/icons/sleep.svg">
      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 bg-gradient-to-br from-orange-500/10 to-orange-600/10 border-orange-500/20">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--text-secondary)] mb-1">
                {t('sleep.avgDuration')}
              </p>
              <p className="text-3xl font-bold text-[var(--text-accent)]">
                {stats.avg_sleep_hours != null ? `${stats.avg_sleep_hours.toFixed(1)}h` : '--'}
              </p>
            </div>
            <img src="/icons/sleep-hours.svg" alt="" aria-hidden="true" className="w-12 h-12 object-contain" />
          </div>
          {stats.sleep_debt != null && (
            <p className={`text-sm mt-2 ${stats.sleep_debt >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {stats.sleep_debt >= 0 ? '↑' : '↓'} {Math.abs(stats.sleep_debt).toFixed(1)}h {t('sleep.debtTotal')}
            </p>
          )}
        </Card>

        <Card className="p-6 bg-gradient-to-br from-rose-500/10 to-rose-600/10 border-rose-500/20">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--text-secondary)] mb-1">
                {t('sleep.avgQuality')}
              </p>
              <p className="text-3xl font-bold text-rose-600 dark:text-rose-400">
                {stats.avg_quality_score != null ? `${stats.avg_quality_score}%` : '--'}
              </p>
            </div>
            <img src="/icons/sleep-quality.svg" alt="" aria-hidden="true" className="w-12 h-12 object-contain" />
          </div>
          {stats.total_records != null && (
            <p className="text-sm mt-2 text-[var(--text-secondary)]">
              {stats.total_records} {t('sleep.daysRecorded')}
            </p>
          )}
        </Card>

        <Card className="p-6 bg-gradient-to-br from-amber-500/10 to-amber-600/10 border-amber-500/20">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-[var(--text-secondary)] mb-1">
                {t('sleep.sleepPattern')}
              </p>
              <p className="text-xl font-bold text-amber-700 dark:text-amber-400">
                {stats.most_common_pattern ? t(`sleep.chronotype.${stats.most_common_pattern}`, { defaultValue: stats.most_common_pattern }) : '--'}
              </p>
            </div>
            <img src="/icons/sleep-pattern.svg" alt="" aria-hidden="true" className="w-12 h-12 object-contain" />
          </div>
        </Card>
      </div>

      </DashboardSection>

      {/* ===== B. TRENDS ===== */}
      <DashboardSection id="sleep-trends" title={t('sleep.section.trends')} icon="/icons/mood-trend.svg">
      <SleepTrendsChart data={trendsData} />
      </DashboardSection>

      {/* ===== C. CORRELATIONS ===== */}
      <DashboardSection id="sleep-corr" title={t('sleep.section.correlations')} icon="/icons/brain.svg">
      <SleepCorrelation data={analysisData} />
      </DashboardSection>

      {/* ===== D. INSIGHTS ===== */}
      <DashboardSection id="sleep-insights" title={t('sleep.section.insights')} icon="/icons/lightbulb.svg">
      {/* Issues & Recommendations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Issues */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <img src="/icons/alert.svg" alt="" aria-hidden="true" className="w-7 h-7 object-contain" />
            {t('sleep.detectedIssues')}
          </h3>
          {issues.length > 0 ? (
            <ul className="space-y-3">
              {issues.map((issue, idx) => (
                <li key={idx} className="flex items-start gap-3 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                  <span className="text-red-600 dark:text-red-400 mt-0.5">•</span>
                  <span className="text-sm text-[var(--text-primary)]">{issue}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[var(--text-secondary)] text-center py-8">{t('sleep.noIssues')}</p>
          )}
        </Card>

        {/* Recommendations */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <img src="/icons/lightbulb.svg" alt="" aria-hidden="true" className="w-7 h-7 object-contain" />
            {t('sleep.recommendations')}
          </h3>
          {recommendations.length > 0 ? (
            <ul className="space-y-3">
              {recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-3 p-3 rounded-lg bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800">
                  <span className="text-[var(--text-accent)] mt-0.5">✓</span>
                  <span className="text-sm text-[var(--text-primary)]">{rec}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-[var(--text-secondary)] text-center py-8">{t('sleep.noRecommendations')}</p>
          )}
        </Card>
      </div>
      </DashboardSection>
    </div>
  )
}
