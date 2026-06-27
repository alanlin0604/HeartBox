import { useEffect, useState, useRef } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLang } from '../context/LanguageContext'
import { LANG_OPTIONS } from '../utils/locales'
import PasswordField from '../components/PasswordField'
import { useToast } from '../context/ToastContext'
import { Button, Card, Input } from '../components/ui'
import { loadGsiClient } from '../utils/loadGsiClient'

export default function LoginPage() {
  const { user, login } = useAuth()
  const { lang, setLang, t } = useLang()
  const toast = useToast()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [rememberMe, setRememberMe] = useState(true)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [requires2FA, setRequires2FA] = useState(false)
  const [partialToken, setPartialToken] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [twoFALoading, setTwoFALoading] = useState(false)
  const [warmingUp, setWarmingUp] = useState(false)
  const [warmElapsed, setWarmElapsed] = useState(0)
  const googleBtnRef = useRef(null)
  const googleCallbackRef = useRef()

  // Refresh the ref each time `t` / `toast` change so the latest copy is
  // available when Google's GSI library invokes the callback (which it
  // does outside React's lifecycle). Writing to ref.current from inside
  // an effect avoids the React 19 "cannot access refs during render" rule.
  useEffect(() => {
    googleCallbackRef.current = async (response) => {
      try {
        const { default: api } = await import('../api/axios')
        const { data } = await api.post('/auth/google/', { credential: response.credential })
        const { setAuthTokens } = await import('../utils/tokenStorage')
        setAuthTokens(data.access, data.refresh, true)
        window.location.href = '/'
      } catch {
        setError(t('oauth.failed'))
        toast?.error(t('oauth.failed'))
      }
    }
  }, [t, toast])

  useEffect(() => { document.title = `${t('login.title')} — ${t('app.name')}` }, [t])

  // Pre-warm backend (Cloud Run cold start can be ~30s)
  useEffect(() => {
    const apiUrl = import.meta.env.VITE_API_URL
    if (!apiUrl) return
    const healthUrl = apiUrl.replace(/\/api\/?$/, '') + '/healthz/'
    fetch(healthUrl, { method: 'GET', cache: 'no-store' }).catch(() => {})
  }, [])

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
    if (!clientId) return

    let cancelled = false
    loadGsiClient()
      .then(() => {
        if (cancelled || !window.google?.accounts?.id || !googleBtnRef.current) return
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (res) => googleCallbackRef.current(res),
        })
        window.google.accounts.id.renderButton(googleBtnRef.current, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          text: 'signin_with',
          shape: 'pill',
          width: Math.min(googleBtnRef.current.offsetWidth || 384, 400),
        })
      })
      .catch(() => {})
    return () => { cancelled = true }
  }, [])

  if (user) return <Navigate to="/" />

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    setWarmingUp(false)
    setWarmElapsed(0)
    // Show the "waking server" banner after 3s. Once shown, tick an
    // elapsed-seconds counter every second so the user can see progress
    // is being made — silent spinners over 10s read as "broken".
    const startedAt = Date.now()
    let elapsedTimer
    const warmTimer = setTimeout(() => {
      setWarmingUp(true)
      setWarmElapsed(Math.floor((Date.now() - startedAt) / 1000))
      elapsedTimer = setInterval(() => {
        setWarmElapsed(Math.floor((Date.now() - startedAt) / 1000))
      }, 1000)
    }, 3000)
    try {
      const data = await login(username, password, rememberMe)
      if (data?.requires_2fa) {
        setRequires2FA(true)
        setPartialToken(data.partial_token)
        return
      }
      toast?.success(t('login.success'))
    } catch (err) {
      if (err.response?.data?.requires_2fa) {
        setRequires2FA(true)
        setPartialToken(err.response.data.partial_token)
        return
      }
      const message = !err.response ? t('common.serverUnreachable') : t('login.failed')
      setError(message)
    } finally {
      clearTimeout(warmTimer)
      if (elapsedTimer) clearInterval(elapsedTimer)
      setWarmingUp(false)
      setWarmElapsed(0)
      setLoading(false)
    }
  }

  const handle2FAVerify = async () => {
    setTwoFALoading(true)
    try {
      const { default: api } = await import('../api/axios')
      const { data } = await api.post('/auth/2fa/login/', { partial_token: partialToken, code: totpCode })
      const { setAuthTokens } = await import('../utils/tokenStorage')
      setAuthTokens(data.access, data.refresh, rememberMe)
      window.location.href = '/'
    } catch {
      setError(t('twofa.verifyFailed'))
    } finally {
      setTwoFALoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4">
      {/* Decorative gradient orbs */}
      <div className="absolute top-0 left-1/4 w-96 h-96 bg-gradient-to-br from-orange-500/10 to-rose-500/10 rounded-full blur-3xl -z-10" />
      <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-gradient-to-br from-blue-500/10 to-orange-500/10 rounded-full blur-3xl -z-10" />

      <Card padding="lg" className="w-full max-w-md">
        {/* Language Selector */}
        <div className="flex justify-end mb-6 gap-1">
          {LANG_OPTIONS.map((opt) => (
            <button
              key={opt.code}
              onClick={() => setLang(opt.code)}
              aria-label={`Switch to ${opt.name}`}
              aria-pressed={lang === opt.code}
              className={`
                px-3 py-1 text-xs rounded-lg cursor-pointer transition-all
                ${lang === opt.code
                  ? 'bg-[var(--color-primary-500)]/20 text-[var(--color-primary-400)] font-semibold border border-[var(--color-primary-500)]/30'
                  : 'opacity-50 hover:opacity-100 hover:bg-[var(--surface-primary)]'
                }
              `.trim().replace(/\s+/g, ' ')}
            >
              {opt.label}
            </button>
          ))}
        </div>

        {/* Logo */}
        <div className="flex justify-center mb-4">
          <img
            src="/logo-icon.png"
            alt="HeartBox"
            decoding="async"
            className="w-32 h-32 object-contain drop-shadow-[0_0_20px_rgba(251, 146, 60,0.2)]"
          />
        </div>

        {/* Title */}
        <h1 className="text-3xl font-bold text-center mb-2">
          <span className="gradient-text">{t('app.displayName')}</span>
        </h1>
        <p className="text-center text-[var(--text-secondary)] text-sm mb-8">
          {t('login.title')}
        </p>

        {/* Error Alert */}
        {error && (
          <div
            role="alert"
            className="mb-6 p-4 rounded-lg bg-[var(--color-secondary-600)]/10 border border-[var(--color-secondary-600)]/20 text-[var(--color-secondary-600)]"
          >
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <span className="text-sm">{error}</span>
            </div>
          </div>
        )}

        {/* Warming up notice (shown after 3s while login still pending — explains Cloud Run cold start).
            Elapsed counter + indeterminate progress bar reassure the user that the request is alive. */}
        {warmingUp && !error && (
          <div
            role="status"
            aria-live="polite"
            className="mb-6 p-4 rounded-lg bg-[var(--color-primary-500)]/10 border border-[var(--color-primary-500)]/20 text-[var(--color-primary-400)]"
          >
            <div className="flex items-start gap-3">
              <svg className="w-5 h-5 shrink-0 mt-0.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              <div className="flex-1 min-w-0">
                <p className="text-sm">{t('login.warmingUp')}</p>
                <p className="text-xs opacity-80 mt-1">
                  {t('login.warmingUpElapsed', { seconds: warmElapsed })}
                </p>
                <div className="mt-2 h-1 rounded-full overflow-hidden bg-[var(--color-primary-500)]/20">
                  <div className="h-full bg-[var(--color-primary-500)]/60 animate-pulse" style={{ width: `${Math.min(100, (warmElapsed / 30) * 100)}%`, transition: 'width 0.5s linear' }} />
                </div>
              </div>
            </div>
          </div>
        )}

        {/* 2FA Form */}
        {requires2FA ? (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-center text-[var(--text-primary)]">
              {t('twofa.loginTitle')}
            </h2>
            <Input
              type="text"
              value={totpCode}
              onChange={e => setTotpCode(e.target.value)}
              placeholder={t('twofa.enterCode')}
              maxLength={6}
              className="text-center text-lg tracking-widest"
            />
            <Button
              onClick={handle2FAVerify}
              disabled={totpCode.length !== 6 || twoFALoading}
              loading={twoFALoading}
              fullWidth
            >
              {t('twofa.verify')}
            </Button>
          </div>
        ) : (
          <>
            {/* Login Form */}
            <form onSubmit={handleSubmit} className="space-y-5">
              <Input
                id="login-username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={t('login.username')}
                label={t('login.username')}
                autoComplete="username"
                required
              />

              <PasswordField
                id="login-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('login.password')}
                label={t('login.password')}
                autoComplete="current-password"
                required
              />

              <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)] cursor-pointer">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  className="w-4 h-4 rounded border-[var(--border-primary)] accent-[var(--color-primary-500)]"
                />
                {t('login.rememberMe')}
              </label>

              <Button
                type="submit"
                disabled={loading}
                loading={loading}
                fullWidth
                size="lg"
              >
                {t('login.submit')}
              </Button>
            </form>

            {/* Divider */}
            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-[var(--border-primary)]" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="px-3 bg-[var(--glass-bg)] text-[var(--text-tertiary)]">
                  {t('oauth.or')}
                </span>
              </div>
            </div>

            {/* Google Sign In */}
            <div ref={googleBtnRef} className="w-full flex justify-center" />

            {/* Forgot Password Link */}
            <div className="mt-4 text-right">
              <Link
                to="/forgot-password"
                className="text-sm text-[var(--color-primary-400)] hover:text-[var(--color-primary-300)] transition-colors"
              >
                {t('login.forgotPassword')}
              </Link>
            </div>

            {/* Register Link */}
            <p className="mt-6 text-center text-sm text-[var(--text-secondary)]">
              {t('login.noAccount')}{' '}
              <Link
                to="/register"
                className="text-[var(--color-primary-400)] hover:text-[var(--color-primary-300)] font-medium transition-colors"
              >
                {t('login.register')}
              </Link>
            </p>
          </>
        )}
      </Card>

      {/* Footer Links */}
      <div className="mt-8 text-center">
        <div className="flex items-center justify-center gap-4 text-xs text-[var(--text-tertiary)]">
          <Link to="/privacy" className="hover:text-[var(--color-primary-400)] transition-colors">
            {t('legal.privacy')}
          </Link>
          <span>•</span>
          <Link to="/terms" className="hover:text-[var(--color-primary-400)] transition-colors">
            {t('legal.terms')}
          </Link>
        </div>
      </div>
    </div>
  )
}
