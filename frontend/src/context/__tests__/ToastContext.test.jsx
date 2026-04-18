import { describe, it, expect, vi } from 'vitest'
import { render, renderHook, act } from '@testing-library/react'
import { ToastProvider, useToast } from '../ToastContext'

// Mock LanguageContext
vi.mock('../LanguageContext', () => ({
  useLang: () => ({
    t: (key) => key,
  }),
}))

// Mock ToastContainer
vi.mock('../../components/ui/Toast', () => ({
  ToastContainer: () => null,
}))

describe('ToastContext', () => {
  it('provides toast API through useToast hook', () => {
    const { result } = renderHook(() => useToast(), {
      wrapper: ToastProvider,
    })

    expect(result.current).toBeDefined()
    expect(result.current.success).toBeTypeOf('function')
    expect(result.current.error).toBeTypeOf('function')
    expect(result.current.info).toBeTypeOf('function')
    expect(result.current.warning).toBeTypeOf('function')
    expect(result.current.dismiss).toBeTypeOf('function')
    expect(result.current.dismissAll).toBeTypeOf('function')
  })

  it('success() method works', () => {
    const { result } = renderHook(() => useToast(), {
      wrapper: ToastProvider,
    })

    act(() => {
      const id = result.current.success('Success message')
      expect(id).toBeTypeOf('number')
      expect(id).toBeGreaterThan(0)
    })
  })

  it('error() method works', () => {
    const { result } = renderHook(() => useToast(), {
      wrapper: ToastProvider,
    })

    act(() => {
      const id = result.current.error('Error message')
      expect(id).toBeTypeOf('number')
      expect(id).toBeGreaterThan(0)
    })
  })

  it('info() method works', () => {
    const { result } = renderHook(() => useToast(), {
      wrapper: ToastProvider,
    })

    act(() => {
      const id = result.current.info('Info message')
      expect(id).toBeTypeOf('number')
      expect(id).toBeGreaterThan(0)
    })
  })

  it('warning() method works', () => {
    const { result } = renderHook(() => useToast(), {
      wrapper: ToastProvider,
    })

    act(() => {
      const id = result.current.warning('Warning message')
      expect(id).toBeTypeOf('number')
      expect(id).toBeGreaterThan(0)
    })
  })

  it('generates unique IDs for different toasts', () => {
    const { result } = renderHook(() => useToast(), {
      wrapper: ToastProvider,
    })

    const ids = []
    act(() => {
      ids.push(result.current.success('Message 1'))
      ids.push(result.current.success('Message 2'))
      ids.push(result.current.success('Message 3'))
    })

    expect(new Set(ids).size).toBe(3)
  })

  it('dismissAll() method works', () => {
    const { result } = renderHook(() => useToast(), {
      wrapper: ToastProvider,
    })

    act(() => {
      result.current.success('Message 1')
      result.current.error('Message 2')
      result.current.dismissAll()
    })

    // No errors should be thrown
    expect(result.current).toBeDefined()
  })

  it('dismiss() method works with toast ID', () => {
    const { result } = renderHook(() => useToast(), {
      wrapper: ToastProvider,
    })

    act(() => {
      const id = result.current.success('Message')
      result.current.dismiss(id)
    })

    // No errors should be thrown
    expect(result.current).toBeDefined()
  })

  it('toast API is memoized', () => {
    const { result, rerender } = renderHook(() => useToast(), {
      wrapper: ToastProvider,
    })

    const firstApi = result.current
    rerender()
    const secondApi = result.current

    expect(firstApi).toBe(secondApi)
  })
})
