import { useState, useEffect, lazy, Suspense } from 'react'
import { useParams } from 'react-router-dom'
import { getPublicReport } from '../api/wellness'
import { useLang } from '../context/LanguageContext'
import LoadingSpinner from '../components/LoadingSpinner'

import { LOCALE_MAP } from '../utils/locales'

const LazyLineChart = lazy(() => import('../components/charts/LazyLineChart'))

const ChartSkeleton = () => (
  <div className="w-full h-[250px] flex items-center justify-center opacity-50">
    <div className="animate-pulse text-sm">{/* Loading chart... */}</div>
  </div>
)

export default function TherapistReportPublicPage() {
  const { token } = useParams()
  const { lang, t } = useLang()
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const locale = LOCALE_MAP[lang] || lang

  useEffect(() => {
    let cancelled = false
    document.title = `${t('publicReport.title')} — ${t('app.name')}`
    getPublicReport(token)
      .then((res) => { if (!cancelled) setReport(res.data) })
      .catch((err) => {
        if (cancelled) return
        if (err.response?.status === 404) setError(t('publicReport.notFound'))
        else if (err.response?.status === 410) setError(t('publicReport.expired'))
        else setError(t('common.operationFailed'))
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [token, t])

  if (loading) return <div className="min-h-screen flex items-center justify-center"><LoadingSpinner /></div>

  if (error) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="glass p-8 text-center max-w-md">
        <p className="text-lg font-semibold text-red-400">{error}</p>
      </div>
    </div>
  )

  if (!report) return null

  const moodData = (report.report_data?.mood_trends || []).map((item) => ({
    date: new Date(item.created_at).toLocaleDateString(locale),
    sentiment: item.sentiment_score,
    stress: item.stress_index,
  }))

  return (
    <div className="min-h-screen p-6 max-w-3xl mx-auto space-y-6">
      <div className="glass p-6">
        <h1 className="text-2xl font-bold mb-2">{report.title}</h1>
        <p className="text-sm text-slate-400">
          {report.period_start} — {report.period_end}
        </p>
        <p className="text-xs text-slate-400 mt-1">
          {t('publicReport.generated')}: {new Date(report.created_at).toLocaleDateString(locale)}
        </p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass p-4 text-center">
          <p className="text-xs text-slate-400">{t('publicReport.notes')}</p>
          <p className="text-2xl font-bold">{report.report_data?.note_count ?? '-'}</p>
        </div>
        <div className="glass p-4 text-center">
          <p className="text-xs text-slate-400">{t('publicReport.avgMood')}</p>
          <p className="text-2xl font-bold">{report.report_data?.mood_avg ?? '-'}</p>
        </div>
        <div className="glass p-4 text-center">
          <p className="text-xs text-slate-400">{t('publicReport.avgStress')}</p>
          <p className="text-2xl font-bold">{report.report_data?.stress_avg ?? '-'}</p>
        </div>
      </div>

      {/* Mood trends chart */}
      {moodData.length > 1 && (
        <div className="glass p-6">
          <h2 className="text-lg font-semibold mb-4">{t('publicReport.moodTrends')}</h2>
          <Suspense fallback={<ChartSkeleton />}>
            <LazyLineChart
              data={moodData}
              xAxisKey="date"
              height={250}
              gridStroke="rgba(255,255,255,0.1)"
              axisStroke="#9ca3af"
              tooltipStyle={{}}
              lines={[
                { dataKey: 'sentiment', stroke: '#fb923c', strokeWidth: 2, name: t('publicReport.sentiment') },
                { dataKey: 'stress', stroke: '#f87171', strokeWidth: 2, name: t('publicReport.stress') },
              ]}
            />
          </Suspense>
        </div>
      )}

      {/* Assessments */}
      {report.report_data?.assessments?.length > 0 && (
        <div className="glass p-6">
          <h2 className="text-lg font-semibold mb-4">{t('publicReport.assessments')}</h2>
          <div className="space-y-2">
            {report.report_data.assessments.map((a, i) => (
              <div key={i} className="glass-card p-3 flex items-center justify-between text-sm">
                <span>{a.assessment_type.toUpperCase()}</span>
                <span className="font-bold">{a.total_score}</span>
                <span className="text-xs text-slate-400">{new Date(a.created_at).toLocaleDateString(locale)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-center text-xs opacity-30 py-4">
        {t('publicReport.sharedVia')}
      </div>
    </div>
  )
}
