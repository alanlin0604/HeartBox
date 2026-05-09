/* eslint-disable no-console -- test asserts on console.log/warn; spies wired below */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook } from '@testing-library/react'
import { usePerformance, useRenderCount, useWhyDidYouUpdate } from '../usePerformance'

describe('usePerformance', () => {
  let originalPerformance

  beforeEach(() => {
    originalPerformance = global.performance
    vi.spyOn(console, 'warn').mockImplementation(() => {})
    vi.spyOn(console, 'log').mockImplementation(() => {})
  })

  afterEach(() => {
    global.performance = originalPerformance
    vi.restoreAllMocks()
  })

  it('logs initial render time in development', () => {
    let callCount = 0
    global.performance = {
      now: () => {
        callCount++
        return callCount === 1 ? 0 : 10 // 0 for start, 10 for end
      }
    }

    renderHook(() => usePerformance('TestComponent'))

    expect(console.log).toHaveBeenCalledTimes(1)
    expect(console.log).toHaveBeenCalledWith(
      expect.stringContaining('📊 TestComponent initial render:')
    )
  })

  it('warns on slow renders exceeding threshold', () => {
    let callCount = 0
    global.performance = {
      now: () => {
        callCount++
        // Return different values: 0 for first call, 50 for second
        const value = callCount === 1 ? 100 : 150
        return value
      }
    }

    renderHook(() => usePerformance('SlowComponent'))

    // Should log initial render with 50ms time (150 - 100)
    expect(console.log).toHaveBeenCalledTimes(1)
    const logCall = console.log.mock.calls[0][0]
    expect(logCall).toContain('📊 SlowComponent initial render:')
    expect(logCall).toContain('50.00ms')

    // Should also warn because 50ms > 16ms threshold
    expect(console.warn).toHaveBeenCalledTimes(1)
    expect(console.warn).toHaveBeenCalledWith(
      expect.stringContaining('⚠️ Slow render detected in SlowComponent:'),
      expect.any(String),
      expect.stringContaining('Render count: 1')
    )
  })

  it('respects custom threshold', () => {
    let callCount = 0
    global.performance = {
      now: () => {
        callCount++
        return callCount === 1 ? 0 : 30 // 0 for start, 30 for end
      }
    }

    renderHook(() => usePerformance('CustomComponent', 50))

    // Should NOT warn because 30ms < 50ms threshold
    expect(console.warn).not.toHaveBeenCalled()
    // Should still log initial render
    expect(console.log).toHaveBeenCalledTimes(1)
  })

  it('does not log in production mode', () => {
    const originalEnv = import.meta.env.DEV
    import.meta.env.DEV = false

    const { rerender } = renderHook(() => usePerformance('ProdComponent'))
    rerender()

    expect(console.log).not.toHaveBeenCalled()
    expect(console.warn).not.toHaveBeenCalled()

    import.meta.env.DEV = originalEnv
  })
})

describe('useRenderCount', () => {
  beforeEach(() => {
    vi.spyOn(console, 'log').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('tracks render count correctly', () => {
    const { result, rerender } = renderHook(() => useRenderCount('CounterComponent'))

    // Initial render: ref is 0, useEffect hasn't run yet
    expect(result.current).toBe(0)

    rerender()
    // After first rerender: useEffect has run once, ref is 1
    expect(result.current).toBe(1)

    rerender()
    // After second rerender: useEffect has run twice, ref is 2
    expect(result.current).toBe(2)
  })

  it('logs render count in development', () => {
    const { rerender } = renderHook(() => useRenderCount('LogComponent'))

    expect(console.log).toHaveBeenCalledWith(
      expect.stringContaining('LogComponent render count: 1')
    )

    rerender()
    expect(console.log).toHaveBeenCalledWith(
      expect.stringContaining('LogComponent render count: 2')
    )
  })

  it('does not log in production mode', () => {
    const originalEnv = import.meta.env.DEV
    import.meta.env.DEV = false

    renderHook(() => useRenderCount('ProdCounter'))

    expect(console.log).not.toHaveBeenCalled()

    import.meta.env.DEV = originalEnv
  })
})

describe('useWhyDidYouUpdate', () => {
  beforeEach(() => {
    vi.spyOn(console, 'log').mockImplementation(() => {})
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('logs changed props on re-render', () => {
    const { rerender } = renderHook(
      ({ props }) => useWhyDidYouUpdate('UpdateComponent', props),
      { initialProps: { props: { count: 1, name: 'test' } } }
    )

    // First render - no log (no previous props)
    expect(console.log).not.toHaveBeenCalled()

    // Second render with changed count
    rerender({ props: { count: 2, name: 'test' } })

    expect(console.log).toHaveBeenCalledWith(
      expect.stringContaining('UpdateComponent re-rendered due to:'),
      expect.objectContaining({
        count: { from: 1, to: 2 }
      })
    )
  })

  it('does not log when props are unchanged', () => {
    const { rerender } = renderHook(
      ({ props }) => useWhyDidYouUpdate('StableComponent', props),
      { initialProps: { props: { count: 1 } } }
    )

    rerender({ props: { count: 1 } })

    // Should only log once on first re-render (no changes)
    expect(console.log).not.toHaveBeenCalled()
  })

  it('detects multiple changed props', () => {
    const { rerender } = renderHook(
      ({ props }) => useWhyDidYouUpdate('MultiComponent', props),
      { initialProps: { props: { a: 1, b: 2, c: 3 } } }
    )

    rerender({ props: { a: 10, b: 2, c: 30 } })

    expect(console.log).toHaveBeenCalledWith(
      expect.stringContaining('MultiComponent re-rendered due to:'),
      expect.objectContaining({
        a: { from: 1, to: 10 },
        c: { from: 3, to: 30 }
      })
    )
  })

  it('does not log in production mode', () => {
    const originalEnv = import.meta.env.DEV
    import.meta.env.DEV = false

    const { rerender } = renderHook(
      ({ props }) => useWhyDidYouUpdate('ProdUpdate', props),
      { initialProps: { props: { count: 1 } } }
    )

    rerender({ props: { count: 2 } })

    expect(console.log).not.toHaveBeenCalled()

    import.meta.env.DEV = originalEnv
  })
})
