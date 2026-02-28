import { useState, useEffect, useCallback } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLang } from '../context/LanguageContext'
import PasswordField from '../components/PasswordField'
import { useToast } from '../context/ToastContext'
import { googleLogin } from '../api/auth'
import { setAuthTokens } from '../utils/tokenStorage'

const LANG_OPTIONS = [
  { code: 'zh-TW', label: 'ZH' },
  { code: 'en', label: 'EN' },
  { code: 'ja', label: 'JA' },
]

export default function RegisterPage() {
  const { user, register } = useAuth()
  const { lang, setLang, t } = useLang()
  const toast = useToast()
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [emailTouched, setEmailTouched] = useState(false)
  const emailValid = !email || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)

  if (user) return <Navigate to="/" />

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await register(username, email, password)
      toast?.success(t('register.success'))
    } catch (err) {
      const data = err.response?.data
      if (data) {
        // Map Django field errors to i18n keys
        const errorMap = {
          username: { 'already exists': 'register.usernameTaken' },
          password: {
            'too short': 'register.passwordTooShort',
            'too common': 'register.passwordTooCommon',
            'entirely numeric': 'register.passwordAllNumeric',
          },
          email: { 'valid email': 'register.emailInvalid' },
        }
        const translated = []
        for (const [field, msgs] of Object.entries(data)) {
          for (const msg of [msgs].flat()) {
            const fieldMap = errorMap[field] || {}
            const key = Object.entries(fieldMap).find(([k]) => msg.toLowerCase().includes(k))?.[1]
            translated.push(key ? t(key) : msg)
          }
        }
        const message = translated.join(', ') || t('register.failed')
        setError(message)
        toast?.error(message)
      } else {
        setError(t('common.serverUnreachable'))
        toast?.error(t('common.serverUnreachable'))
      }
    } finally {
      setLoading(false)
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
        <p className="text-center opacity-60 text-sm mb-6">{t('register.title')}</p>

        {error && (
          <div role="alert" className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="register-username" className="sr-only">{t('register.username')}</label>
            <input
              id="register-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder={t('register.username')}
              className="glass-input"
              autoComplete="username"
              required
            />
          </div>
          <div>
            <label htmlFor="register-email" className="sr-only">{t('register.email')}</label>
            <input
              id="register-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onBlur={() => setEmailTouched(true)}
              placeholder={t('register.email')}
              className={`glass-input ${emailTouched && !emailValid ? 'border-red-500/60' : ''}`}
              autoComplete="email"
              required
            />
            {emailTouched && !emailValid && (
              <p className="text-xs text-red-500 mt-1">{t('register.emailInvalid')}</p>
            )}
          </div>
          <PasswordField
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t('register.password')}
            required
            minLength={8}
            showStrength
          />
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? t('register.loading') : t('register.submit')}
          </button>
        </form>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-white/10" /></div>
          <div className="relative flex justify-center text-xs"><span className="px-2 bg-[var(--card-bg)] opacity-50">{t('oauth.or')}</span></div>
        </div>

        <button
          type="button"
          onClick={() => {
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
                  const { data } = await googleLogin(response.credential)
                  setAuthTokens(data.access, data.refresh, true)
                  window.location.href = '/'
                } catch {
                  setError(t('oauth.failed'))
                  toast?.error(t('oauth.failed'))
                }
              },
            })
            window.google.accounts.id.prompt((notification) => {
              if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
                setError(t('oauth.popupBlocked'))
                toast?.error(t('oauth.popupBlocked'))
              }
            })
          }}
          className="w-full py-2.5 px-4 rounded-xl border border-white/10 hover:border-white/20 transition-all flex items-center justify-center gap-2 cursor-pointer"
        >
          <svg className="w-5 h-5" viewBox="0 0 24 24"><path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/><path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/><path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/><path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/></svg>
          {t('oauth.googleLogin')}
        </button>

        <p className="mt-4 text-center text-sm opacity-60">
          {t('register.hasAccount')}{' '}
          <Link to="/login" className="text-purple-500 hover:text-purple-400 opacity-100">
            {t('register.login')}
          </Link>
        </p>
      </div>
      <div className="mt-6 text-center text-xs opacity-40 space-x-3">
        <Link to="/privacy" className="hover:opacity-70">{t('legal.privacy')}</Link>
        <span>|</span>
        <Link to="/terms" className="hover:opacity-70">{t('legal.terms')}</Link>
      </div>
    </div>
  )
}
