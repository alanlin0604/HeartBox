import { useState, useEffect, useRef } from 'react'
import { getSleepAnalysis, getSleepTrends } from '../api/sleep'
import { useTheme } from '../context/ThemeContext'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'
import { Card, Button } from '../components/ui'
import SkeletonCard from '../components/SkeletonCard'
import SleepTrendsChart from '../components/sleep/SleepTrendsChart'
import SleepCorrelation from '../components/sleep/SleepCorrelation'

export default function SleepAnalysisPage() {
  const { theme } = useTheme()
  const { t } = useLang()
  const toast = useToast()
  const [analysisData, setAnalysisData] = useState(null)
  const [trendsData, setTrendsData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [days, setDays] = useState(30)
  const fetchIdRef = useRef(0)

  useEffect(() => {
    document.title = `${t('sleep.analysisTitle')} — ${t('app.name')}`
  }, [t])

  useEffect(() => {
    const fetchId = ++fetchIdRef.current
    setLoading(true)

    Promise.all([
      getSleepAnalysis(days),
      getSleepTrends(90)
    ])
      .then(([analysisRes, trendsRes]) => {
        if (fetchId === fetchIdRef.current) {
          setAnalysisData(analysisRes.data)
          setTrendsData(trendsRes.data)
        }
      })
      .catch((err) => {
        if (fetchId === fetchIdRef.current) {
          console.error('Failed to load sleep analysis:', err)
          toast?.error(t('common.operationFailed'))
        }
      })
      .finally(() => {
        if (fetchId === fetchIdRef.current) {
          setLoading(false)
        }
      })
  }, [days, t, toast])

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

  const stats = analysisData?.statistics || {}
  const patterns = analysisData?.patterns || {}
  const issues = analysisData?.issues || []
  const recommendations = analysisData?.recommendations || []

  return (
    <div className="space-y-6 mt-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-orange-600 to-blue-600 bg-clip-text text-transparent">
            {t('sleep.analysisTitle')}
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-2">
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

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="p-6 bg-gradient-to-br from-orange-500/10 to-orange-600/10 border-orange-500/20">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                {t('sleep.avgDuration')}
              </p>
              <p className="text-3xl font-bold text-orange-600 dark:text-orange-400">
                {stats.avg_duration ? `${stats.avg_duration.toFixed(1)}h` : '--'}
              </p>
            </div>
            <div className="text-4xl">😴</div>
          </div>
          {stats.duration_trend && (
            <p className={`text-sm mt-2 ${stats.duration_trend > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {stats.duration_trend > 0 ? '↑' : '↓'} {Math.abs(stats.duration_trend).toFixed(1)}h {t('sleep.vsLastPeriod')}
            </p>
          )}
        </Card>

        <Card className="p-6 bg-gradient-to-br from-blue-500/10 to-blue-600/10 border-blue-500/20">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                {t('sleep.avgQuality')}
              </p>
              <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">
                {stats.avg_quality ? `${stats.avg_quality.toFixed(0)}%` : '--'}
              </p>
            </div>
            <div className="text-4xl">⭐</div>
          </div>
          {stats.quality_trend && (
            <p className={`text-sm mt-2 ${stats.quality_trend > 0 ? 'text-green-600' : 'text-red-600'}`}>
              {stats.quality_trend > 0 ? '↑' : '↓'} {Math.abs(stats.quality_trend).toFixed(0)}% {t('sleep.vsLastPeriod')}
            </p>
          )}
        </Card>

        <Card className="p-6 bg-gradient-to-br from-indigo-500/10 to-indigo-600/10 border-indigo-500/20">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-1">
                {t('sleep.sleepPattern')}
              </p>
              <p className="text-xl font-bold text-indigo-600 dark:text-indigo-400">
                {patterns.chronotype ? t(`sleep.chronotype.${patterns.chronotype}`) : '--'}
              </p>
            </div>
            <div className="text-4xl">🌙</div>
          </div>
          {patterns.consistency && (
            <p className="text-sm mt-2 text-gray-600 dark:text-gray-400">
              {t('sleep.consistency')}: {patterns.consistency.toFixed(0)}%
            </p>
          )}
        </Card>
      </div>

      {/* Trends Chart */}
      <SleepTrendsChart data={trendsData} />

      {/* Correlation Analysis */}
      <SleepCorrelation data={analysisData} />

      {/* Issues & Recommendations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Issues */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">⚠️</span>
            {t('sleep.detectedIssues')}
          </h3>
          {issues.length > 0 ? (
            <ul className="space-y-3">
              {issues.map((issue, idx) => (
                <li key={idx} className="flex items-start gap-3 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                  <span className="text-red-600 dark:text-red-400 mt-0.5">•</span>
                  <span className="text-sm text-gray-700 dark:text-gray-300">{issue}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500 text-center py-8">{t('sleep.noIssues')}</p>
          )}
        </Card>

        {/* Recommendations */}
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="text-2xl">💡</span>
            {t('sleep.recommendations')}
          </h3>
          {recommendations.length > 0 ? (
            <ul className="space-y-3">
              {recommendations.map((rec, idx) => (
                <li key={idx} className="flex items-start gap-3 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                  <span className="text-blue-600 dark:text-blue-400 mt-0.5">✓</span>
                  <span className="text-sm text-gray-700 dark:text-gray-300">{rec}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-gray-500 text-center py-8">{t('sleep.noRecommendations')}</p>
          )}
        </Card>
      </div>
    </div>
  )
}
