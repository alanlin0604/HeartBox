import { useEffect, useState, useRef } from 'react'
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
  const googleBtnRef = useRef(null)
  const googleCallbackRef = useRef()

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

  useEffect(() => { document.title = `${t('login.title')} — ${t('app.name')}` }, [t])

  useEffect(() => {
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
    if (!clientId) return

    const initGoogle = () => {
      if (!window.google?.accounts?.id || !googleBtnRef.current) return false
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
      return true
    }

    if (!initGoogle()) {
      const interval = setInterval(() => {
        if (initGoogle()) clearInterval(interval)
      }, 200)
      const timeout = setTimeout(() => clearInterval(interval), 5000)
      return () => { clearInterval(interval); clearTimeout(timeout) }
    }
  }, [])

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
            <div ref={googleBtnRef} className="w-full flex justify-center" />
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
