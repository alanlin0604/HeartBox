import { useMemo } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { useTheme } from '../../context/ThemeContext'
import { useLang } from '../../context/LanguageContext'
import { Card } from '../ui'

/**
 * SleepCorrelation - Display correlation between sleep and mood/stress
 * Shows two separate bar charts with color-coded correlation strength
 */
export default function SleepCorrelation({ data }) {
  const { theme } = useTheme()
  const { t } = useLang()

  const moodData = useMemo(() => {
    if (!data?.mood_correlation) return []
    return Object.entries(data.mood_correlation).map(([mood, score]) => ({
      name: t(`moods.${mood}`) || mood,
      value: parseFloat(score)
    }))
  }, [data, t])

  const stressData = useMemo(() => {
    if (!data?.stress_correlation) return []
    return Object.entries(data.stress_correlation).map(([level, score]) => ({
      name: t(`stress.${level}`) || level,
      value: parseFloat(score)
    }))
  }, [data, t])

  const gridStroke = useMemo(() => theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)', [theme])
  const axisStroke = useMemo(() => theme === 'dark' ? '#9ca3af' : '#475569', [theme])
  const tooltipStyle = useMemo(() => ({
    background: theme === 'dark' ? 'rgba(30,20,60,0.95)' : 'rgba(255,255,255,0.98)',
    border: `1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)'}`,
    borderRadius: '12px',
    padding: '12px',
    color: theme === 'dark' ? '#e2e8f0' : '#1e293b',
  }), [theme])

  // Color based on correlation strength
  const getBarColor = (value) => {
    const absValue = Math.abs(value)
    if (absValue >= 0.7) return '#10b981' // Strong - green
    if (absValue >= 0.4) return '#3b82f6' // Moderate - blue
    return '#9ca3af' // Weak - gray
  }

  if (!moodData.length && !stressData.length) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">{t('sleep.correlationTitle')}</h3>
        <div className="text-center py-12 text-gray-500">
          {t('sleep.noData')}
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {moodData.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">{t('sleep.moodCorrelation')}</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={moodData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
              <XAxis
                dataKey="name"
                stroke={axisStroke}
                tick={{ fill: axisStroke }}
                style={{ fontSize: '12px' }}
              />
              <YAxis
                stroke={axisStroke}
                tick={{ fill: axisStroke }}
                domain={[-1, 1]}
              />
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(value) => [`${value.toFixed(2)}`, t('sleep.correlation')]}
              />
              <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                {moodData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getBarColor(entry.value)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      {stressData.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4">{t('sleep.stressCorrelation')}</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={stressData} margin={{ top: 5, right: 30, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={gridStroke} />
              <XAxis
                dataKey="name"
                stroke={axisStroke}
                tick={{ fill: axisStroke }}
                style={{ fontSize: '12px' }}
              />
              <YAxis
                stroke={axisStroke}
                tick={{ fill: axisStroke }}
                domain={[-1, 1]}
              />
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(value) => [`${value.toFixed(2)}`, t('sleep.correlation')]}
              />
              <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                {stressData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getBarColor(entry.value)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  )
}
