import { memo } from 'react'
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer, Tooltip,
} from 'recharts'
import { useTheme } from '../context/ThemeContext'
import { useLang } from '../context/LanguageContext'

export default memo(function StressRadarChart({ data, bare = false }) {
  const { theme } = useTheme()
  const { t } = useLang()

  // ``bare`` mode renders only the chart body (no outer card / heading)
  // so a parent grid can place the radar next to another widget without
  // doubled card backgrounds or duplicate titles. See DashboardPage's
  // 標籤分析 section.
  if (!data || data.length === 0) {
    if (bare) {
      return (
        <p className="text-slate-400 text-sm">{t('dashboard.noStressRadar')}</p>
      )
    }
    return (
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('dashboard.stressRadar')}</h2>
        <p className="text-slate-400 text-sm">{t('dashboard.noStressRadar')}</p>
      </div>
    )
  }

  const tooltipStyle = {
    background: theme === 'dark' ? 'rgba(30,20,60,0.9)' : 'rgba(255,255,255,0.95)',
    border: `1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)'}`,
    borderRadius: '8px',
    color: theme === 'dark' ? '#e2e8f0' : '#1e293b',
  }

  const radar = (
    <ResponsiveContainer width="100%" height={bare ? 280 : 350}>
      <RadarChart data={data} outerRadius="70%" cx="50%" cy="50%">
        <PolarGrid stroke={theme === 'dark' ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'} />
        <PolarAngleAxis
          dataKey="tag"
          tick={{ fill: theme === 'dark' ? '#9ca3af' : '#475569', fontSize: 13 }}
        />
        <PolarRadiusAxis
          angle={90}
          domain={[0, 10]}
          tick={false}
        />
        <Tooltip contentStyle={tooltipStyle} />
        <Radar
          name={t('dashboard.avgStress')}
          dataKey="avg_stress"
          stroke="#f87171"
          fill="#f87171"
          fillOpacity={0.3}
        />
      </RadarChart>
    </ResponsiveContainer>
  )

  if (bare) return radar

  return (
    <div className="glass p-6">
      <h2 className="text-lg font-semibold mb-4">{t('dashboard.stressRadar')}</h2>
      {radar}
    </div>
  )
})
