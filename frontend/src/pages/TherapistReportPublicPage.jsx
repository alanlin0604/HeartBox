import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { getPublicReport } from '../api/wellness'
import LoadingSpinner from '../components/LoadingSpinner'

const REPORT_LOCALE = navigator.language || 'zh-TW'

export default function TherapistReportPublicPage() {
  const { token } = useParams()
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    document.title = 'Therapist Report — HeartBox'
    getPublicReport(token)
      .then((res) => setReport(res.data))
      .catch((err) => {
        if (err.response?.status === 404) setError('Report not found.')
        else if (err.response?.status === 410) setError('This report has expired.')
        else setError('Failed to load report.')
      })
      .finally(() => setLoading(false))
  }, [token])

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
    date: new Date(item.created_at).toLocaleDateString(REPORT_LOCALE),
    sentiment: item.sentiment_score,
    stress: item.stress_index,
  }))

  return (
    <div className="min-h-screen p-6 max-w-3xl mx-auto space-y-6">
      <div className="glass p-6">
        <h1 className="text-2xl font-bold mb-2">{report.title}</h1>
        <p className="text-sm opacity-60">
          {report.period_start} — {report.period_end}
        </p>
        <p className="text-xs opacity-40 mt-1">
          Generated: {new Date(report.created_at).toLocaleDateString(REPORT_LOCALE)}
        </p>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="glass p-4 text-center">
          <p className="text-xs opacity-60">Notes</p>
          <p className="text-2xl font-bold">{report.report_data?.note_count ?? '-'}</p>
        </div>
        <div className="glass p-4 text-center">
          <p className="text-xs opacity-60">Avg Mood</p>
          <p className="text-2xl font-bold">{report.report_data?.mood_avg ?? '-'}</p>
        </div>
        <div className="glass p-4 text-center">
          <p className="text-xs opacity-60">Avg Stress</p>
          <p className="text-2xl font-bold">{report.report_data?.stress_avg ?? '-'}</p>
        </div>
      </div>

      {/* Mood trends chart */}
      {moodData.length > 1 && (
        <div className="glass p-6">
          <h2 className="text-lg font-semibold mb-4">Mood Trends</h2>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={moodData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} />
              <YAxis stroke="#9ca3af" fontSize={12} />
              <Tooltip />
              <Line type="monotone" dataKey="sentiment" stroke="#a78bfa" strokeWidth={2} name="Sentiment" />
              <Line type="monotone" dataKey="stress" stroke="#f87171" strokeWidth={2} name="Stress" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Assessments */}
      {report.report_data?.assessments?.length > 0 && (
        <div className="glass p-6">
          <h2 className="text-lg font-semibold mb-4">Self-Assessment Scores</h2>
          <div className="space-y-2">
            {report.report_data.assessments.map((a, i) => (
              <div key={i} className="glass-card p-3 flex items-center justify-between text-sm">
                <span>{a.assessment_type.toUpperCase()}</span>
                <span className="font-bold">{a.total_score}</span>
                <span className="text-xs opacity-60">{new Date(a.created_at).toLocaleDateString(REPORT_LOCALE)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="text-center text-xs opacity-30 py-4">
        Shared via HeartBox
      </div>
    </div>
  )
}
