import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { getAssessments, createAssessment } from '../api/wellness'
import { useLang } from '../context/LanguageContext'
import { useTheme } from '../context/ThemeContext'
import { useToast } from '../context/ToastContext'

const SCORE_LABELS = {
  phq9: [
    { max: 4, key: 'assessment.minimal' },
    { max: 9, key: 'assessment.mild' },
    { max: 14, key: 'assessment.moderate' },
    { max: 19, key: 'assessment.moderatelySevere' },
    { max: 27, key: 'assessment.severe' },
  ],
  gad7: [
    { max: 4, key: 'assessment.minimal' },
    { max: 9, key: 'assessment.mild' },
    { max: 14, key: 'assessment.moderate' },
    { max: 21, key: 'assessment.severe' },
  ],
}

function getScoreLabel(type, score, t) {
  const labels = SCORE_LABELS[type] || []
  for (const l of labels) {
    if (score <= l.max) return t(l.key)
  }
  return ''
}

function getScoreColor(type, score) {
  if (type === 'phq9') {
    if (score <= 4) return 'text-green-400'
    if (score <= 9) return 'text-yellow-400'
    if (score <= 14) return 'text-orange-400'
    return 'text-red-400'
  }
  if (score <= 4) return 'text-green-400'
  if (score <= 9) return 'text-yellow-400'
  return 'text-red-400'
}

export default function AssessmentsPage() {
  const { t } = useLang()
  const { theme } = useTheme()
  const toast = useToast()
  const [tab, setTab] = useState('phq9')
  const [history, setHistory] = useState([])
  const [responses, setResponses] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState(null)

  useEffect(() => { document.title = `${t('nav.assessments')} — ${t('app.name')}` }, [t])

  const questionCount = tab === 'phq9' ? 9 : 7

  useEffect(() => {
    setResponses(Array(questionCount).fill(-1))
    setResult(null)
    getAssessments(tab)
      .then((res) => setHistory(res.data?.results || res.data || []))
      .catch(() => setHistory([]))
  }, [tab])

  const handleAnswer = (qIndex, value) => {
    setResponses((prev) => {
      const next = [...prev]
      next[qIndex] = value
      return next
    })
  }

  const handleSubmit = async () => {
    if (responses.some((r) => r < 0)) {
      toast?.error(t('assessment.answerAll'))
      return
    }
    setSubmitting(true)
    try {
      const { data } = await createAssessment({
        assessment_type: tab,
        responses,
      })
      setResult(data)
      setHistory((prev) => [data, ...prev])
      toast?.success(t('assessment.submitted'))
    } catch {
      toast?.error(t('common.operationFailed'))
    } finally {
      setSubmitting(false)
    }
  }

  const gridStroke = theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'
  const axisStroke = theme === 'dark' ? '#9ca3af' : '#475569'
  const tooltipStyle = {
    background: theme === 'dark' ? 'rgba(30,20,60,0.9)' : 'rgba(255,255,255,0.95)',
    border: `1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)'}`,
    borderRadius: '8px',
    color: theme === 'dark' ? '#e2e8f0' : '#1e293b',
  }

  const chartData = [...history].reverse().map((item) => ({
    date: new Date(item.created_at).toLocaleDateString(),
    score: item.total_score,
  }))

  return (
    <div className="space-y-6 mt-4 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold">{t('nav.assessments')}</h1>

      {/* Tabs */}
      <div className="flex gap-2">
        {['phq9', 'gad7'].map((type) => (
          <button
            key={type}
            onClick={() => setTab(type)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === type ? 'bg-purple-500/30 text-purple-400' : 'opacity-60 hover:opacity-100'
            }`}
          >
            {type === 'phq9' ? 'PHQ-9' : 'GAD-7'}
          </button>
        ))}
      </div>

      {/* Result banner */}
      {result && (
        <div className="glass p-4 border-l-4 border-purple-500/50">
          <p className="font-semibold">
            {t('assessment.yourScore')}: <span className={getScoreColor(tab, result.total_score)}>{result.total_score}</span>
            {' — '}
            <span className={getScoreColor(tab, result.total_score)}>
              {getScoreLabel(tab, result.total_score, t)}
            </span>
          </p>
          <p className="text-xs opacity-60 mt-2">{t('assessment.disclaimer')}</p>
        </div>
      )}

      {/* Questionnaire */}
      <div className="glass p-6 space-y-6">
        <h2 className="text-lg font-semibold">
          {tab === 'phq9' ? t('assessment.phq9Title') : t('assessment.gad7Title')}
        </h2>
        <p className="text-sm opacity-60">{t('assessment.instructions')}</p>

        {Array.from({ length: questionCount }, (_, i) => (
          <div key={i} className="space-y-2">
            <p className="text-sm font-medium">
              {i + 1}. {t(`assessment.${tab}_q${i + 1}`)}
            </p>
            <div className="flex flex-wrap gap-2">
              {[0, 1, 2, 3].map((val) => (
                <button
                  key={val}
                  type="button"
                  onClick={() => handleAnswer(i, val)}
                  className={`text-xs px-3 py-1.5 rounded-lg border transition-colors cursor-pointer ${
                    responses[i] === val
                      ? 'bg-purple-500/30 border-purple-500/40 text-purple-400'
                      : 'border-[var(--card-border)] opacity-60 hover:opacity-100'
                  }`}
                >
                  {t(`assessment.option${val}`)}
                </button>
              ))}
            </div>
          </div>
        ))}

        <button
          onClick={handleSubmit}
          disabled={submitting || responses.some((r) => r < 0)}
          className="btn-primary"
        >
          {submitting ? t('common.loading') : t('assessment.submit')}
        </button>
      </div>

      {/* History chart */}
      {chartData.length > 1 && (
        <div className="glass p-6">
          <h2 className="text-lg font-semibold mb-4">{t('assessment.history')}</h2>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
              <XAxis dataKey="date" stroke={axisStroke} fontSize={12} />
              <YAxis stroke={axisStroke} fontSize={12} />
              <Tooltip contentStyle={tooltipStyle} />
              <Line type="monotone" dataKey="score" stroke="#a78bfa" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
