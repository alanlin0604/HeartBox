import { memo, useState, useEffect, useMemo } from 'react'
import { ResponsiveContainer } from 'recharts'

/**
 * Responsive chart wrapper with mobile-optimized configurations
 * Automatically adjusts chart settings based on screen size
 *
 * @param {ReactNode} children - Chart component (LineChart, BarChart, etc.)
 * @param {number} height - Chart height (default: 300)
 * @param {Object} mobileConfig - Override config for mobile
 * @param {Object} tabletConfig - Override config for tablet
 * @param {Object} desktopConfig - Override config for desktop
 * @param {number} mobileBreakpoint - Mobile breakpoint (default: 640)
 * @param {number} tabletBreakpoint - Tablet breakpoint (default: 1024)
 */
export const ResponsiveChart = memo(function ResponsiveChart({
  children,
  height = 300,
  mobileConfig = {},
  tabletConfig = {},
  desktopConfig = {},
  mobileBreakpoint = 640,
  tabletBreakpoint = 1024,
}) {
  const [screenWidth, setScreenWidth] = useState(
    typeof window !== 'undefined' ? window.innerWidth : 1024
  )

  useEffect(() => {
    const handleResize = () => setScreenWidth(window.innerWidth)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Determine device type
  const deviceType = useMemo(() => {
    if (screenWidth < mobileBreakpoint) return 'mobile'
    if (screenWidth < tabletBreakpoint) return 'tablet'
    return 'desktop'
  }, [screenWidth, mobileBreakpoint, tabletBreakpoint])

  // Get responsive height
  const responsiveHeight = useMemo(() => {
    if (deviceType === 'mobile') return height * 0.8 // 20% smaller on mobile
    if (deviceType === 'tablet') return height * 0.9 // 10% smaller on tablet
    return height
  }, [height, deviceType])

  // Merge configs
  const config = useMemo(() => {
    const baseConfig = {
      fontSize: deviceType === 'mobile' ? 10 : deviceType === 'tablet' ? 11 : 12,
      strokeWidth: deviceType === 'mobile' ? 1.5 : 2,
      margin: deviceType === 'mobile'
        ? { top: 5, right: 5, left: -20, bottom: 5 }
        : { top: 5, right: 10, left: 0, bottom: 5 },
    }

    if (deviceType === 'mobile') return { ...baseConfig, ...mobileConfig }
    if (deviceType === 'tablet') return { ...baseConfig, ...tabletConfig }
    return { ...baseConfig, ...desktopConfig }
  }, [deviceType, mobileConfig, tabletConfig, desktopConfig])

  return (
    <ResponsiveContainer width="100%" height={responsiveHeight}>
      {typeof children === 'function' ? children(config, deviceType) : children}
    </ResponsiveContainer>
  )
})

/**
 * Chart axis helper - returns optimized axis props based on screen size
 */
export function useChartAxisProps(deviceType = 'desktop') {
  return useMemo(() => ({
    xAxis: {
      fontSize: deviceType === 'mobile' ? 10 : 12,
      angle: deviceType === 'mobile' ? -45 : 0,
      textAnchor: deviceType === 'mobile' ? 'end' : 'middle',
      height: deviceType === 'mobile' ? 60 : 30,
    },
    yAxis: {
      fontSize: deviceType === 'mobile' ? 10 : 12,
      width: deviceType === 'mobile' ? 35 : 50,
    },
  }), [deviceType])
}

/**
 * Chart legend helper - returns optimized legend props
 */
export function useChartLegendProps(deviceType = 'desktop') {
  return useMemo(() => ({
    fontSize: deviceType === 'mobile' ? 10 : 12,
    iconSize: deviceType === 'mobile' ? 10 : 14,
    wrapperStyle: {
      fontSize: deviceType === 'mobile' ? '10px' : '12px',
      paddingTop: deviceType === 'mobile' ? '8px' : '10px',
    },
    layout: deviceType === 'mobile' ? 'horizontal' : 'horizontal',
    verticalAlign: deviceType === 'mobile' ? 'bottom' : 'bottom',
    align: 'center',
  }), [deviceType])
}

/**
 * Chart tooltip helper - returns optimized tooltip props
 */
export function useChartTooltipProps(theme = 'dark') {
  return useMemo(() => ({
    contentStyle: {
      background: `var(--tooltip-bg)`,
      border: `1px solid var(--tooltip-border)`,
      borderRadius: '8px',
      fontSize: '12px',
      padding: '8px 12px',
      boxShadow: 'var(--shadow-lg)',
    },
    labelStyle: {
      color: 'var(--text-primary)',
      fontWeight: 600,
      marginBottom: '4px',
    },
    itemStyle: {
      color: 'var(--text-secondary)',
      fontSize: '11px',
    },
  }), [theme])
}

/**
 * Hook to simplify responsive chart configuration
 * Returns all necessary props and helpers for a responsive chart
 *
 * @example
 * const { containerProps, axisProps, legendProps, tooltipProps, deviceType } = useResponsiveChartConfig()
 *
 * <ResponsiveChart {...containerProps}>
 *   <LineChart>
 *     <XAxis {...axisProps.xAxis} />
 *     <YAxis {...axisProps.yAxis} />
 *     <Legend {...legendProps} />
 *     <Tooltip {...tooltipProps} />
 *   </LineChart>
 * </ResponsiveChart>
 */
export function useResponsiveChartConfig(options = {}) {
  const {
    height = 300,
    mobileBreakpoint = 640,
    tabletBreakpoint = 1024,
    theme = 'dark',
  } = options

  const [screenWidth, setScreenWidth] = useState(
    typeof window !== 'undefined' ? window.innerWidth : 1024
  )

  useEffect(() => {
    const handleResize = () => setScreenWidth(window.innerWidth)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  const deviceType = useMemo(() => {
    if (screenWidth < mobileBreakpoint) return 'mobile'
    if (screenWidth < tabletBreakpoint) return 'tablet'
    return 'desktop'
  }, [screenWidth, mobileBreakpoint, tabletBreakpoint])

  const axisProps = useChartAxisProps(deviceType)
  const legendProps = useChartLegendProps(deviceType)
  const tooltipProps = useChartTooltipProps(theme)

  const containerProps = useMemo(() => ({
    height,
    mobileBreakpoint,
    tabletBreakpoint,
  }), [height, mobileBreakpoint, tabletBreakpoint])

  return {
    containerProps,
    axisProps,
    legendProps,
    tooltipProps,
    deviceType,
    screenWidth,
    isMobile: deviceType === 'mobile',
    isTablet: deviceType === 'tablet',
    isDesktop: deviceType === 'desktop',
  }
}

/**
 * Responsive chart colors helper
 * Returns color palette optimized for the current theme
 */
export function useChartColors(theme = 'dark') {
  return useMemo(() => {
    const colors = {
      primary: 'var(--color-primary)',
      success: 'var(--color-success)',
      warning: 'var(--color-warning)',
      error: 'var(--color-error)',
      info: 'var(--color-info)',
      grid: 'var(--chart-grid)',
      axis: 'var(--chart-axis)',
    }

    // Additional chart-specific colors
    const chartPalette = [
      '#8b5cf6', // purple
      '#3b82f6', // blue
      '#10b981', // green
      '#f59e0b', // amber
      '#ef4444', // red
      '#ec4899', // pink
      '#14b8a6', // teal
      '#f97316', // orange
    ]

    return { ...colors, palette: chartPalette }
  }, [theme])
}

export default ResponsiveChart
