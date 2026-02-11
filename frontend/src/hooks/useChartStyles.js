import { useMemo } from 'react'
import { useTheme } from '../context/ThemeContext'

export function useChartTooltipStyle() {
  const { theme } = useTheme()

  return useMemo(() => ({
    contentStyle: {
      background: theme === 'dark' ? 'rgba(30, 20, 60, 0.9)' : 'rgba(255, 255, 255, 0.95)',
      border: `1px solid ${theme === 'dark' ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)'}`,
      borderRadius: '8px',
      color: theme === 'dark' ? '#e2e8f0' : '#1e293b',
    },
  }), [theme])
}
