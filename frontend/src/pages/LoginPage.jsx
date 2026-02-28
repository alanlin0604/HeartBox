import { useEffect, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLang } from '../context/LanguageContext'
import { LANG_OPTIONS } from '../utils/locales'
import PasswordField from '../components/PasswordField'
import { useToast } from '../context/ToastContext'

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

  useEffect(() => { document.title = `${t('login.title')} — ${t('app.name')}` }, [t])

  if (user) return <Navigate to="/" />

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
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
      setLoading(false)
    }
  }

  const handle2FAVerify = async () => {
    setTwoFALoading(true)
    try {
      const { default: api } = await import('../api/axios')
      const { data } = await api.post('/auth/2fa/login/', { partial_token: partialToken, code: totpCode })
      // Store tokens and redirect
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
      <div className="glass p-8 w-full max-w-md">
        <div className="flex justify-end mb-4 gap-1">
          {LANG_OPTIONS.map((opt) => (
            <button
              key={opt.code}
              onClick={() => setLang(opt.code)}
              className={`px-1.5 py-0.5 text-xs rounded cursor-pointer transition-all ${
                lang === opt.code
                  ? 'bg-purple-500/30 text-purple-500 font-bold'
                  : 'opacity-50 hover:opacity-100'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="flex justify-center mb-3">
          <img src="/logo.png" alt="HeartBox" decoding="async" className="w-36 h-36 object-contain" />
        </div>
        <h1 className="text-2xl font-bold text-center mb-2 bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent">
          {t('app.displayName')}
        </h1>
        <p className="text-center opacity-60 text-sm mb-6">{t('login.title')}</p>

        {error && (
          <div role="alert" className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm">
            {error}
          </div>
        )}

        {requires2FA ? (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-center">{t('twofa.loginTitle')}</h2>
            <input
              type="text"
              value={totpCode}
              onChange={e => setTotpCode(e.target.value)}
              placeholder={t('twofa.enterCode')}
              maxLength={6}
              className="glass-input text-center text-lg tracking-widest"
            />
            <button
              onClick={handle2FAVerify}
              disabled={totpCode.length !== 6 || twoFALoading}
              className="btn-primary w-full"
            >
              {twoFALoading ? t('common.loading') : t('twofa.verify')}
            </button>
          </div>
        ) : (
          <>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label htmlFor="login-username" className="sr-only">{t('login.username')}</label>
                <input
                  id="login-username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder={t('login.username')}
                  className="glass-input"
                  autoComplete="username"
                  required
                />
              </div>
              <PasswordField
                id="login-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t('login.password')}
                label={t('login.password')}
                autoComplete="current-password"
                required
              />
              <label className="flex items-center gap-2 text-sm opacity-75">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                />
                {t('login.rememberMe')}
              </label>
              <button type="submit" disabled={loading} className="btn-primary w-full">
                {loading ? t('login.loading') : t('login.submit')}
              </button>
            </form>
            <div className="text-center my-4">
              <div className="border-t border-[var(--card-border)] relative">
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 px-2 bg-[var(--tooltip-bg)] text-xs opacity-50">{t('oauth.or')}</span>
              </div>
            </div>
            <button
              type="button"
              onClick={async () => {
                if (!window.google?.accounts?.id) {
                  setError(t('oauth.unavailable'))
                  toast?.error(t('oauth.unavailable'))
                  return
                }
                const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
                if (!clientId) {
                  setError(t('oauth.unavailable'))
                  toast?.error(t('oauth.unavailable'))
                  return
                }
                window.google.accounts.id.initialize({
                  client_id: clientId,
                  callback: async (response) => {
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
                })
                window.google.accounts.id.prompt((notification) => {
                  if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
                    setError(t('oauth.popupBlocked'))
                    toast?.error(t('oauth.popupBlocked'))
                  }
                })
              }}
              className="btn-secondary w-full flex items-center justify-center gap-2"
            >
              <svg width="18" height="18" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
              {t('oauth.google')}
            </button>
            <div className="mt-2 text-right">
              <Link to="/forgot-password" className="text-xs text-purple-400 hover:text-purple-300">
                {t('login.forgotPassword')}
              </Link>
            </div>

            <p className="mt-4 text-center text-sm opacity-60">
              {t('login.noAccount')}{' '}
              <Link to="/register" className="text-purple-500 hover:text-purple-400 opacity-100">
                {t('login.register')}
              </Link>
            </p>
          </>
        )}
      </div>
      <div className="mt-6 text-center text-xs opacity-40 space-x-3">
        <Link to="/privacy" className="hover:opacity-70">{t('legal.privacy')}</Link>
        <span>|</span>
        <Link to="/terms" className="hover:opacity-70">{t('legal.terms')}</Link>
      </div>
    </div>
  )
}
