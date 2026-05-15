import { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { useTheme } from '../../context/ThemeContext'
import { useLang } from '../../context/LanguageContext'
import { Card } from '../ui'

/**
 * SleepTrendsChart - Display 90-day sleep duration and quality trends
 * Uses dual Y-axis to show both hours and quality score
 */
export default function SleepTrendsChart({ data }) {
  const { theme } = useTheme()
  const { t } = useLang()

  const chartData = useMemo(() => {
    if (!data?.trends) return []
    // Backend emits {week_start, avg_sleep_hours, avg_quality_score, avg_mood}.
    // Earlier this component read `item.date / .duration / .quality_score`,
    // which silently produced NaN for every point and rendered an empty chart.
    return data.trends
      .filter(item => item.avg_sleep_hours != null || item.avg_quality_score != null)
      .map(item => ({
        date: new Date(item.week_start).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
        duration: item.avg_sleep_hours != null ? parseFloat(item.avg_sleep_hours) : 0,
        quality: item.avg_quality_score != null ? parseFloat(item.avg_quality_score) : 0,
      }))
  }, [data])

  const gridStroke = useMemo(() => theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)', [theme])
  const axisStroke = useMemo(() => theme === 'dark' ? '#9ca3af' : '#475569', [theme])
  const tooltipStyle = useMemo(() => ({
    background: theme === 'dark' ? 'rgba(30,20,60,0.95)' : 'rgba(255,255,255,0.98)',
    border: `1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)'}`,
    borderRadius: '12px',
    padding: '12px',
    color: theme === 'dark' ? '#e2e8f0' : '#1e293b',
  }), [theme])

  if (!chartData.length) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">{t('sleep.trendsTitle')}</h3>
        <div className="text-center py-12 text-gray-500">
          {t('sleep.noData')}
        </div>
      </Card>
    )
  }

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold mb-4">{t('sleep.trendsTitle')}</h3>
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
          <XAxis
            dataKey="date"
            stroke={axisStroke}
            tick={{ fill: axisStroke }}
            style={{ fontSize: '12px' }}
          />
          <YAxis
            yAxisId="left"
            stroke={axisStroke}
            tick={{ fill: axisStroke }}
            label={{ value: t('sleep.hoursLabel'), angle: -90, position: 'insideLeft' }}
          />
          <YAxis
            yAxisId="right"
            orientation="right"
            stroke={axisStroke}
            tick={{ fill: axisStroke }}
            domain={[0, 100]}
            label={{ value: t('sleep.qualityLabel'), angle: 90, position: 'insideRight' }}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value, name) => {
              if (name === 'duration') return [`${value.toFixed(1)} ${t('sleep.hours')}`, t('sleep.duration')]
              if (name === 'quality') return [`${value.toFixed(0)}`, t('sleep.quality')]
              return [value, name]
            }}
          />
          <Legend
            formatter={(value) => {
              if (value === 'duration') return t('sleep.duration')
              if (value === 'quality') return t('sleep.quality')
              return value
            }}
          />
          <Line
            yAxisId="left"
            type="monotone"
            dataKey="duration"
            stroke="#fb923c"
            strokeWidth={2}
            dot={{ fill: '#fb923c', r: 3 }}
            activeDot={{ r: 5 }}
          />
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="quality"
            stroke="#e11d48"
            strokeWidth={2}
            dot={{ fill: '#e11d48', r: 3 }}
            activeDot={{ r: 5 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </Card>
  )
}
