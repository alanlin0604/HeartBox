import { useState, useEffect, useMemo, useRef, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, BarChart, Bar, Legend,
} from 'recharts'
import { getAnalytics } from '../api/analytics'
import { useTheme } from '../context/ThemeContext'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'
import SkeletonCard from '../components/SkeletonCard'
import MoodCalendar from '../components/MoodCalendar'
import YearInPixels from '../components/YearInPixels'
import StressRadarChart from '../components/StressRadarChart'
import EmptyState from '../components/EmptyState'

function downloadChartAsPNG(containerRef, filename = 'chart.png') {
  const svg = containerRef.current?.querySelector('svg')
  if (!svg) return
  const svgData = new XMLSerializer().serializeToString(svg)
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  const img = new Image()
  img.onload = () => {
    canvas.width = img.width * 2
    canvas.height = img.height * 2
    ctx.scale(2, 2)
    ctx.fillStyle = '#1e1b4b'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0)
    const a = document.createElement('a')
    a.download = filename
    a.href = canvas.toDataURL('image/png')
    a.click()
  }
  img.src = 'data:image/svg+xml;base64,' + btoa(unescape(encodeURIComponent(svgData)))
}

function downloadDataAsCSV(data, columns, filename = 'data.csv') {
  const header = columns.map(c => c.label).join(',')
  const rows = data.map(row => columns.map(c => row[c.key] ?? '').join(','))
  const csv = [header, ...rows].join('\n')
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8' })
  const a = document.createElement('a')
  a.download = filename
  a.href = URL.createObjectURL(blob)
  a.click()
  URL.revokeObjectURL(a.href)
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const { theme } = useTheme()
  const { t } = useLang()
  const toast = useToast()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [period, setPeriod] = useState('week')
  const [lookback, setLookback] = useState(30)
  const trendsRef = useRef(null)
  const tagsRef = useRef(null)

  useEffect(() => { document.title = `${t('nav.dashboard')} — ${t('app.name')}` }, [t])

  useEffect(() => {
    setLoading(true)
    setError(false)
    getAnalytics(period, lookback)
      .then((res) => setData(res.data))
      .catch((err) => {
        setError(true)
        toast?.error(t('common.operationFailed'))
      })
      .finally(() => setLoading(false))
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
      <p className="text-lg mb-4">{t('common.operationFailed')}</p>
      <button className="btn-primary" onClick={() => { setError(false); setLoading(true); getAnalytics(period, lookback).then((res) => setData(res.data)).catch(() => setError(true)).finally(() => setLoading(false)) }}>
        {t('common.retry')}
      </button>
    </div>
  )

  return (
    <div className="space-y-6 mt-4">
      <MoodCalendar />

      {/* Year in Pixels */}
      <YearInPixels />

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
      <div className="glass p-6" ref={trendsRef}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">{t('dashboard.moodTrends')}</h2>
          {trends.length > 0 && (
            <div className="flex gap-2">
              <button
                onClick={() => downloadChartAsPNG(trendsRef, 'mood_trends.png')}
                className="text-xs opacity-50 hover:opacity-100 transition-opacity px-2 py-1 rounded border border-[var(--card-border)]"
                title="PNG"
              >
                PNG
              </button>
              <button
                onClick={() => downloadDataAsCSV(trends, [
                  { key: 'name', label: 'Period' },
                  { key: 'avg_sentiment', label: 'Avg Sentiment' },
                  { key: 'avg_stress', label: 'Avg Stress' },
                ], 'mood_trends.csv')}
                className="text-xs opacity-50 hover:opacity-100 transition-opacity px-2 py-1 rounded border border-[var(--card-border)]"
                title="CSV"
              >
                CSV
              </button>
            </div>
          )}
        </div>
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
            </div>
            <table className="sr-only">
              <caption>{t('dashboard.moodTrends')}</caption>
              <thead><tr><th>Period</th><th>{t('dashboard.avgSentiment')}</th><th>{t('dashboard.avgStress')}</th></tr></thead>
              <tbody>{trends.map((r, i) => <tr key={i}><td>{r.name}</td><td>{r.avg_sentiment}</td><td>{r.avg_stress}</td></tr>)}</tbody>
            </table>
          </>
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
      <div className="glass p-6" ref={tagsRef}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">{t('dashboard.frequentTags')}</h2>
          {tags.length > 0 && (
            <div className="flex gap-2">
              <button
                onClick={() => downloadChartAsPNG(tagsRef, 'frequent_tags.png')}
                className="text-xs opacity-50 hover:opacity-100 transition-opacity px-2 py-1 rounded border border-[var(--card-border)]"
                title="PNG"
              >
                PNG
              </button>
              <button
                onClick={() => downloadDataAsCSV(tags, [
                  { key: 'name', label: 'Tag' },
                  { key: 'count', label: 'Count' },
                ], 'frequent_tags.csv')}
                className="text-xs opacity-50 hover:opacity-100 transition-opacity px-2 py-1 rounded border border-[var(--card-border)]"
                title="CSV"
              >
                CSV
              </button>
            </div>
          )}
        </div>
        {tags.length === 0 ? (
          <EmptyState
            title={t('dashboard.noTags')}
            description={t('dashboard.noTagsDesc')}
            actionText={t('dashboard.goWrite')}
            onAction={() => navigate('/')}
          />
        ) : (
          <div role="img" aria-label={t('dashboard.frequentTags')}>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={tags}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
                <XAxis dataKey="name" stroke={axisStroke} fontSize={12} />
                <YAxis stroke={axisStroke} fontSize={12} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="count" name={t('dashboard.tagCount')} fill="#7c3aed" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Activity-Mood Correlation */}
      {activityCorrelation.length > 0 && (
        <div className="glass p-6">
          <h2 className="text-lg font-semibold mb-4">{t('dashboard.activityCorrelation')}</h2>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={activityCorrelation}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
              <XAxis dataKey="name" stroke={axisStroke} fontSize={11} />
              <YAxis stroke={axisStroke} fontSize={12} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="avg_sentiment" name={t('dashboard.avgSentiment')} fill="#a78bfa" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
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
          <ResponsiveContainer width="100%" height={250}>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
              <XAxis dataKey="sleep_hours" name={t('dashboard.sleepHoursLabel')} unit="h" stroke={axisStroke} fontSize={12} />
              <YAxis dataKey="sentiment" name={t('dashboard.sentimentLabel')} stroke={axisStroke} fontSize={12} />
              <Tooltip contentStyle={tooltipStyle} />
              <Scatter data={sleepCorrelation.scatter_data} fill="#60a5fa" />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Stress Radar Chart */}
      <StressRadarChart data={stressByTag} />
    </div>
  )
}
