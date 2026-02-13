import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, BarChart, Bar, Legend,
} from 'recharts'
import { getAnalytics } from '../api/analytics'
import { useTheme } from '../context/ThemeContext'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'
import LoadingSpinner from '../components/LoadingSpinner'
import MoodCalendar from '../components/MoodCalendar'
import StressRadarChart from '../components/StressRadarChart'
import EmptyState from '../components/EmptyState'

export default function DashboardPage() {
  const navigate = useNavigate()
  const { theme } = useTheme()
  const { t } = useLang()
  const toast = useToast()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [period, setPeriod] = useState('week')
  const [lookback, setLookback] = useState(30)

  useEffect(() => { document.title = `${t('nav.dashboard')} — ${t('app.name')}` }, [t])

  useEffect(() => {
    setLoading(true)
    getAnalytics(period, lookback)
      .then((res) => setData(res.data))
      .catch((err) => {
        console.error(err)
        toast?.error(t('common.operationFailed'))
      })
      .finally(() => setLoading(false))
  }, [period, lookback])

  const trends = useMemo(() => data?.mood_trends || [], [data])
  const correlation = useMemo(() => data?.weather_correlation || {}, [data])
  const tags = useMemo(() => data?.frequent_tags || [], [data])
  const stressByTag = useMemo(() => data?.stress_by_tag || [], [data])

  // Theme-aware chart colors
  const gridStroke = useMemo(() => theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)', [theme])
  const axisStroke = useMemo(() => theme === 'dark' ? '#9ca3af' : '#475569', [theme])
  const tooltipStyle = useMemo(() => ({
    background: theme === 'dark' ? 'rgba(30,20,60,0.9)' : 'rgba(255,255,255,0.95)',
    border: `1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)'}`,
    borderRadius: '8px',
    color: theme === 'dark' ? '#e2e8f0' : '#1e293b',
  }), [theme])

  if (loading && !data) return <LoadingSpinner />

  return (
    <div className="space-y-6 mt-4">
      <MoodCalendar />

      {/* Streak stats */}
      {(data?.current_streak > 0 || data?.longest_streak > 0) && (
        <div className="glass p-4 flex flex-wrap items-center gap-6">
          {data?.current_streak > 0 && (
            <div className="flex items-center gap-2 text-sm">
              <span className="text-xl">🔥</span>
              <span className="font-medium">{t('journal.streak', { days: data.current_streak })}</span>
            </div>
          )}
          {data?.longest_streak > 0 && (
            <div className="flex items-center gap-2 text-sm opacity-70">
              <span className="text-xl">🏆</span>
              <span>{t('dashboard.longestStreak', { days: data.longest_streak })}</span>
            </div>
          )}
        </div>
      )}

      {/* Controls */}
      <div className="glass p-4 flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <span className="text-sm opacity-60">{t('dashboard.period')}</span>
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
          <span className="text-sm opacity-60">{t('dashboard.lookback')}</span>
          <select
            value={lookback}
            onChange={(e) => setLookback(Number(e.target.value))}
            className="glass-input w-auto text-sm"
          >
            <option value={7}>{t('dashboard.days7')}</option>
            <option value={30}>{t('dashboard.days30')}</option>
            <option value={90}>{t('dashboard.days90')}</option>
          </select>
        </div>
      </div>

      {/* Mood Trends */}
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('dashboard.moodTrends')}</h2>
        {trends.length === 0 ? (
          <EmptyState
            title={t('dashboard.noTrends')}
            description={t('dashboard.noTrendsDesc')}
            actionText={t('dashboard.goWrite')}
            onAction={() => navigate('/')}
          />
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
              <XAxis dataKey="name" stroke={axisStroke} fontSize={12} />
              <YAxis stroke={axisStroke} fontSize={12} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend />
              <Line type="monotone" dataKey="avg_sentiment" stroke="#a78bfa" name={t('dashboard.avgSentiment')} strokeWidth={2} />
              <Line type="monotone" dataKey="avg_stress" stroke="#f87171" name={t('dashboard.avgStress')} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Weather Correlation */}
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-2">{t('dashboard.weatherCorrelation')}</h2>
        {correlation.correlation != null ? (
          <>
            <p className="text-sm opacity-60 mb-4">
              {t('dashboard.pearson', {
                r: correlation.correlation,
                p: correlation.p_value,
                n: correlation.sample_size,
              })}
            </p>
            <ResponsiveContainer width="100%" height={250}>
              <ScatterChart>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                <XAxis dataKey="temperature" name={t('dashboard.temperatureLabel')} unit="°C" stroke={axisStroke} fontSize={12} />
                <YAxis dataKey="sentiment" name={t('dashboard.sentimentLabel')} stroke={axisStroke} fontSize={12} />
                <Tooltip contentStyle={tooltipStyle} />
                <Scatter data={correlation.scatter_data} fill="#a78bfa" />
              </ScatterChart>
            </ResponsiveContainer>
          </>
        ) : (
          <EmptyState
            title={t('dashboard.noCorrelation')}
            description={t('dashboard.noCorrelationDesc')}
            actionText={t('dashboard.goWrite')}
            onAction={() => navigate('/')}
          />
        )}
      </div>

      {/* Frequent Tags */}
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('dashboard.frequentTags')}</h2>
        {tags.length === 0 ? (
          <EmptyState
            title={t('dashboard.noTags')}
            description={t('dashboard.noTagsDesc')}
            actionText={t('dashboard.goWrite')}
            onAction={() => navigate('/')}
          />
        ) : (
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={tags}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
              <XAxis dataKey="name" stroke={axisStroke} fontSize={12} />
              <YAxis stroke={axisStroke} fontSize={12} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="count" name={t('dashboard.tagCount')} fill="#7c3aed" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Stress Radar Chart */}
      <StressRadarChart data={stressByTag} />
    </div>
  )
}
