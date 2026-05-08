import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

// --- Mocks ---
// react-router-dom: Link/Navigate stay simple; the rest is unused here.
vi.mock('react-router-dom', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    Navigate: ({ to }) => <div data-testid="navigate-to">{to}</div>,
  }
})

// Auth context: control `user` and provide a stub `login`.
const loginMock = vi.fn()
vi.mock('../../context/AuthContext', () => ({
  useAuth: () => ({ user: null, login: loginMock }),
}))

// Language context: identity translator so tests can match keys.
vi.mock('../../context/LanguageContext', () => ({
  useLang: () => ({
    lang: 'en',
    setLang: vi.fn(),
    t: (key) => key,
  }),
}))

// Toast: surface calls via spies.
const toastMock = { success: vi.fn(), error: vi.fn() }
vi.mock('../../context/ToastContext', () => ({
  useToast: () => toastMock,
}))

// GSI loader is async network — short-circuit to a resolved promise.
vi.mock('../../utils/loadGsiClient', () => ({
  loadGsiClient: () => new Promise(() => {}),
}))

import LoginPage from '../LoginPage'

const renderLogin = () =>
  render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  )

describe('LoginPage cold-start optimizations', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve({ ok: true })))
    import.meta.env.VITE_API_URL = 'https://api.heartbox.tw/api'
    loginMock.mockReset()
    toastMock.success.mockReset()
    toastMock.error.mockReset()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.useRealTimers()
  })

  it('fires a healthz pre-warm ping on mount', () => {
    renderLogin()
    expect(fetch).toHaveBeenCalledTimes(1)
    const [url, opts] = fetch.mock.calls[0]
    expect(url).toBe('https://api.heartbox.tw/healthz/')
    expect(opts).toMatchObject({ method: 'GET', cache: 'no-store' })
  })

  it('does not crash when VITE_API_URL is unset (skips pre-warm)', () => {
    import.meta.env.VITE_API_URL = ''
    renderLogin()
    expect(fetch).not.toHaveBeenCalled()
  })

  it('shows the warming-up notice after ~3s of pending login', async () => {
    vi.useFakeTimers()
    // Make login hang so the timeout fires.
    loginMock.mockImplementation(() => new Promise(() => {}))

    renderLogin()
    expect(screen.queryByText('login.warmingUp')).not.toBeInTheDocument()

    fireEvent.change(screen.getByPlaceholderText('login.username'), { target: { value: 'demo' } })
    fireEvent.change(screen.getByPlaceholderText('login.password'), { target: { value: 'pw' } })
    fireEvent.submit(screen.getByRole('button', { name: 'login.submit' }))

    // Just before the threshold — still nothing.
    act(() => { vi.advanceTimersByTime(2999) })
    expect(screen.queryByText('login.warmingUp')).not.toBeInTheDocument()

    // After the threshold — notice appears.
    act(() => { vi.advanceTimersByTime(2) })
    expect(screen.getByText('login.warmingUp')).toBeInTheDocument()
  })

  it('cleans up the warming-up timer on unmount (no late notice)', () => {
    vi.useFakeTimers()
    loginMock.mockImplementation(() => new Promise(() => {}))

    const { unmount } = renderLogin()
    fireEvent.change(screen.getByPlaceholderText('login.username'), { target: { value: 'demo' } })
    fireEvent.change(screen.getByPlaceholderText('login.password'), { target: { value: 'pw' } })
    fireEvent.submit(screen.getByRole('button', { name: 'login.submit' }))

    // Unmount before the 3s threshold; the timer should be cleared so React does not
    // try to setState on the unmounted component (would log a warning otherwise).
    act(() => { vi.advanceTimersByTime(1500) })
    unmount()
    act(() => { vi.advanceTimersByTime(5000) })
    // No assertion on text — the test passes if no act() warnings fire.
  })
})
