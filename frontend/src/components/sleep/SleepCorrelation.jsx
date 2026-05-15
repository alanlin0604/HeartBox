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

  // Backend mood_correlation shape:
  //   { sufficient_sleep_avg_mood, insufficient_sleep_avg_mood,
  //     mood_difference, correlation, sample_size }
  // Previously we ran Object.entries over this flat dict, which produced
  // garbage bars including parseFloat('positive') = NaN.
  const moodData = useMemo(() => {
    const mc = data?.mood_correlation
    if (!mc || mc.sufficient_sleep_avg_mood == null || mc.insufficient_sleep_avg_mood == null) {
      return []
    }
    return [
      { name: t('sleep.sufficientSleep'), value: parseFloat(mc.sufficient_sleep_avg_mood) },
      { name: t('sleep.insufficientSleep'), value: parseFloat(mc.insufficient_sleep_avg_mood) },
    ]
  }, [data, t])

  const stressData = useMemo(() => {
    const sc = data?.stress_correlation
    if (!sc || sc.sufficient_sleep_avg_stress == null || sc.insufficient_sleep_avg_stress == null) {
      return []
    }
    return [
      { name: t('sleep.sufficientSleep'), value: parseFloat(sc.sufficient_sleep_avg_stress) },
      { name: t('sleep.insufficientSleep'), value: parseFloat(sc.insufficient_sleep_avg_stress) },
    ]
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

  // Color buckets — sufficient (>=7h sleep) shows orange (brand), insufficient
  // shows rose-red. The 0-10 mood/stress scales make value-based shading
  // less meaningful; keying by index is simpler and consistent.
  const BAR_COLORS = ['#f97316', '#e11d48']
  const getBarColor = (_value, index) => BAR_COLORS[index] || '#9ca3af'

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
                domain={[0, 10]}
              />
              <Tooltip
                contentStyle={tooltipStyle}
                formatter={(value) => [`${value.toFixed(1)} / 10`, t('sleep.avgScore')]}
              />
              <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                {moodData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getBarColor(entry.value, index)} />
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
                  <Cell key={`cell-${index}`} fill={getBarColor(entry.value, index)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  )
}
