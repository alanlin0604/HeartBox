import { useEffect, useState } from 'react'
import { reviewAPI } from '../api/reviews'
import { useLang } from '../context/LanguageContext'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { useTheme } from '../context/ThemeContext'

const SENTIMENT_COLORS = ['#10b981', '#94a3b8', '#ef4444'] // green, gray, red

export default function YearlyReview({ year }) {
  const { t } = useLang()
  const { theme } = useTheme()
  const [review, setReview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadReview()
  }, [year])

  async function loadReview() {
    try {
      setLoading(true)
      setError(null)
      const data = await reviewAPI.getYearlyReview(year)
      setReview(data)
    } catch (err) {
      console.error('Failed to load yearly review:', err)
      setError(err.response?.data?.error || t('review.loadError'))
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="glass p-6">
        <h2 className="text-2xl font-bold mb-6">{t('review.yearInReview', { year })}</h2>
        <p className="text-sm text-slate-400">{t('loading')}</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass p-6">
        <h2 className="text-2xl font-bold mb-6">{t('review.yearInReview', { year })}</h2>
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
  const monthlyData = review.monthly_breakdown.map(m => ({
    month: monthNames[m.month - 1],
    [t('dashboard.avgSentiment')]: m.avg_sentiment,
    [t('dashboard.avgStress')]: m.avg_stress,
    count: m.count,
  }))

  const tooltipStyle = {
    background: theme === 'dark' ? 'rgba(30,20,60,0.9)' : 'rgba(255,255,255,0.95)',
    border: `1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)'}',
    borderRadius: '8px',
    color: theme === 'dark' ? '#e2e8f0' : '#1e293b',
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass p-6">
        <h1 className="text-3xl font-bold mb-2 text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">
          {year} {t('review.yearInReview')}
        </h1>
        <p className="text-slate-400">{t('review.yourJourney')}</p>
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

      {/* Monthly Breakdown */}
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('review.monthlyBreakdown')}</h2>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={monthlyData}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'} />
            <XAxis dataKey="month" tick={{ fill: theme === 'dark' ? '#9ca3af' : '#475569', fontSize: 12 }} />
            <YAxis tick={{ fill: theme === 'dark' ? '#9ca3af' : '#475569' }} />
            <Tooltip contentStyle={tooltipStyle} />
            <Bar dataKey={t('dashboard.avgSentiment')} fill="#8b5cf6" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Highlights */}
      {review.best_month && (
        <div className="glass p-6">
          <h2 className="text-lg font-semibold mb-4">{t('review.highlights')}</h2>
          <div className="space-y-3">
            <div className="p-4 rounded-lg bg-gradient-to-r from-green-500/10 to-emerald-500/10 border border-green-500/20">
              <p className="text-sm text-slate-400">{t('review.bestMonth')}</p>
              <p className="text-lg font-semibold">{monthNames[review.best_month.month - 1]}</p>
              <p className="text-sm">{t('mood.score')}: {review.best_month.avg_sentiment.toFixed(2)}</p>
            </div>

            {review.most_productive_month && (
              <div className="p-4 rounded-lg bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/20">
                <p className="text-sm text-slate-400">{t('review.mostProductive')}</p>
                <p className="text-lg font-semibold">{monthNames[review.most_productive_month.month - 1]}</p>
                <p className="text-sm">{review.most_productive_month.count} {t('review.entries')}</p>
              </div>
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
                className="px-4 py-2 rounded-full bg-purple-500/20 border border-purple-500/30 text-sm"
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
