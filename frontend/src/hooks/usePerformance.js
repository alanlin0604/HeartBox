import { useEffect, useRef } from 'react'

/**
 * usePerformance - Monitor component render performance
 * Logs slow renders to console in development mode
 *
 * @param {string} componentName - Name of the component
 * @param {number} threshold - Threshold in ms for slow render warning (default: 16ms for 60fps)
 *
 * @example
 * function MyComponent() {
 *   usePerformance('MyComponent', 50)
 *   // ... component code
 * }
 */
export function usePerformance(componentName, threshold = 16) {
  const renderCount = useRef(0)
  const startTime = useRef(null)

  // Record render start time
  if (import.meta.env.DEV) {
    startTime.current = performance.now()
  }

  useEffect(() => {
    if (!import.meta.env.DEV) return

    renderCount.current++
    const endTime = performance.now()
    const renderTime = endTime - (startTime.current || endTime)

    if (renderTime > threshold) {
      console.warn(
        `⚠️ Slow render detected in ${componentName}:`,
        `${renderTime.toFixed(2)}ms (threshold: ${threshold}ms)`,
        `Render count: ${renderCount.current}`
      )
    }

    if (renderCount.current === 1) {
      console.log(`📊 ${componentName} initial render: ${renderTime.toFixed(2)}ms`)
    }
  })
}

/**
 * useRenderCount - Track how many times a component renders
 * Useful for debugging unnecessary re-renders
 *
 * @param {string} componentName - Name of the component
 *
 * @example
 * function MyComponent() {
 *   useRenderCount('MyComponent')
 *   // ... component code
 * }
 */
export function useRenderCount(componentName) {
  const renderCount = useRef(0)

  useEffect(() => {
    renderCount.current++

    if (import.meta.env.DEV) {
      console.log(`🔄 ${componentName} render count: ${renderCount.current}`)
    }
  })

  return renderCount.current
}

/**
 * useWhyDidYouUpdate - Debug why a component re-rendered
 * Compares props and logs which ones changed
 *
 * @param {string} componentName - Name of the component
 * @param {object} props - Component props to track
 *
 * @example
 * function MyComponent({ user, data }) {
 *   useWhyDidYouUpdate('MyComponent', { user, data })
 *   // ... component code
 * }
 */
export function useWhyDidYouUpdate(componentName, props) {
  const previousProps = useRef()

  useEffect(() => {
    if (!import.meta.env.DEV) return

    if (previousProps.current) {
      const allKeys = Object.keys({ ...previousProps.current, ...props })
      const changedProps = {}

      allKeys.forEach((key) => {
        if (previousProps.current[key] !== props[key]) {
          changedProps[key] = {
            from: previousProps.current[key],
            to: props[key],
          }
        }
      })

      if (Object.keys(changedProps).length > 0) {
        console.log(`🔍 ${componentName} re-rendered due to:`, changedProps)
      }
    }

    previousProps.current = props
  })
}

/**
 * measurePageLoad - Measure and report page load performance
 * Uses Navigation Timing API
 */
export function measurePageLoad() {
  if (typeof window === 'undefined' || !window.performance) return

  window.addEventListener('load', () => {
    setTimeout(() => {
      const perfData = window.performance.timing
      const pageLoadTime = perfData.loadEventEnd - perfData.navigationStart
      const connectTime = perfData.responseEnd - perfData.requestStart
      const renderTime = perfData.domComplete - perfData.domLoading

      if (import.meta.env.DEV) {
        console.log('📈 Page Load Performance:')
        console.log(`  Total: ${pageLoadTime}ms`)
        console.log(`  Network: ${connectTime}ms`)
        console.log(`  Render: ${renderTime}ms`)
      }

      // Report to analytics in production
      if (import.meta.env.PROD && window.gtag) {
        window.gtag('event', 'timing_complete', {
          name: 'page_load',
          value: pageLoadTime,
          event_category: 'Performance',
        })
      }
    }, 0)
  })
}

export default usePerformance
