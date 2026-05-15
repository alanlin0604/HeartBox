import { useEffect, useState } from 'react'
import { reviewAPI } from '../api/reviews'
import { useLang } from '../context/LanguageContext'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { useTheme } from '../context/ThemeContext'
import { Link } from 'react-router-dom'

const SENTIMENT_COLORS = ['#10b981', '#94a3b8', '#ef4444'] // green, gray, red

export default function MonthlyReview() {
  const { t } = useLang()
  const { theme } = useTheme()
  const [review, setReview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // 取得當前年月
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await reviewAPI.getMonthlyReview(year, month)
        if (!cancelled) setReview(data)
      } catch (err) {
        if (cancelled) return
        console.error('Failed to load monthly review:', err)
        setError(err.response?.data?.error || t('review.loadError'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [year, month, t])

  if (loading) {
    return (
      <div className="glass p-6">
        <h2 className="text-2xl font-bold mb-6">{t('review.monthlyReview')}</h2>
        <p className="text-sm text-slate-400">{t('loading')}</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass p-6">
        <h2 className="text-2xl font-bold mb-6">{t('review.monthlyReview')}</h2>
        <p className="text-sm text-slate-400">{error}</p>
      </div>
    )
  }

  if (!review) return null

  const sentimentData = [
    { name: t('mood.positive'), value: review.sentiment_distribution.positive },
    { name: t('mood.neutral'), value: review.sentiment_distribution.neutral },
    { name: t('mood.negative'), value: review.sentiment_distribution.negative },
  ]

  const monthNames = t('review.monthNames').split(',')

  const tooltipStyle = {
    background: theme === 'dark' ? 'rgba(30,20,60,0.9)' : 'rgba(255,255,255,0.95)',
    border: `1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)'}`,
    borderRadius: '8px',
    color: theme === 'dark' ? '#e2e8f0' : '#1e293b',
  }

  return (
    <div className="space-y-6">
      {/* Header with Month/Year Selector */}
      <div className="glass p-6">
        <h1 className="text-3xl font-bold mb-4 text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-rose-400">
          {t('review.monthlyReview')}
        </h1>
        <div className="flex gap-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">{t('review.selectYear')}</label>
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="bg-white/10 border border-white/20 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-500"
            >
              {Array.from({ length: 10 }, (_, i) => now.getFullYear() - i).map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm text-slate-400 mb-1">{t('review.selectMonth')}</label>
            <select
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
              className="bg-white/10 border border-white/20 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-orange-500"
            >
              {monthNames.map((name, idx) => (
                <option key={idx} value={idx + 1}>
                  {name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Key Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass p-6 text-center">
          <div className="text-4xl mb-2">📝</div>
          <p className="text-3xl font-bold">{review.total_notes}</p>
          <p className="text-sm text-slate-400">{t('review.totalEntries')}</p>
        </div>

        <div className="glass p-6 text-center">
          <div className="text-4xl mb-2">😊</div>
          <p className="text-3xl font-bold">{review.avg_sentiment?.toFixed(2) || 'N/A'}</p>
          <p className="text-sm text-slate-400">{t('review.avgMood')}</p>
        </div>

        <div className="glass p-6 text-center">
          <div className="text-4xl mb-2">📊</div>
          <p className="text-3xl font-bold">{review.avg_stress?.toFixed(1) || 'N/A'}</p>
          <p className="text-sm text-slate-400">{t('review.avgStress')}</p>
        </div>
      </div>

      {/* Sentiment Distribution */}
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('review.moodDistribution')}</h2>
        <ResponsiveContainer width="100%" height={250}>
          <PieChart>
            <Pie
              data={sentimentData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={(entry) => `${entry.name}: ${entry.value}`}
              outerRadius={80}
              fill="#8884d8"
              dataKey="value"
            >
              {sentimentData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={SENTIMENT_COLORS[index]} />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Best & Worst Days */}
      {(review.best_day || review.worst_day) && (
        <div className="glass p-6">
          <h2 className="text-lg font-semibold mb-4">{t('review.highlights')}</h2>
          <div className="space-y-3">
            {review.best_day && (
              <Link
                to={`/journal/${review.best_day.id}`}
                className="block p-4 rounded-lg bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/20 hover:border-green-500/40 transition-colors"
              >
                <p className="text-sm text-slate-400">{t('review.bestDay')}</p>
                <p className="text-lg font-semibold">{review.best_day.date}</p>
                <p className="text-sm">{t('mood.score')}: {review.best_day.sentiment.toFixed(2)}</p>
                <p className="text-sm text-slate-300 mt-2 line-clamp-2">{review.best_day.preview}</p>
              </Link>
            )}

            {review.worst_day && (
              <Link
                to={`/journal/${review.worst_day.id}`}
                className="block p-4 rounded-lg bg-gradient-to-r from-red-500/10 to-orange-500/10 border border-red-500/20 hover:border-red-500/40 transition-colors"
              >
                <p className="text-sm text-slate-400">{t('review.worstDay')}</p>
                <p className="text-lg font-semibold">{review.worst_day.date}</p>
                <p className="text-sm">{t('mood.score')}: {review.worst_day.sentiment.toFixed(2)}</p>
                <p className="text-sm text-slate-300 mt-2 line-clamp-2">{review.worst_day.preview}</p>
              </Link>
            )}
          </div>
        </div>
      )}

      {/* Top Tags */}
      {review.top_tags.length > 0 && (
        <div className="glass p-6">
          <h2 className="text-lg font-semibold mb-4">{t('review.topTags')}</h2>
          <div className="flex flex-wrap gap-2">
            {review.top_tags.map((tag, index) => (
              <span
                key={index}
                className="px-4 py-2 rounded-full bg-orange-500/20 border border-orange-500/30 text-sm"
              >
                {tag.name} <span className="text-slate-400">({tag.count})</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
