import { useState, useEffect, useRef } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLang } from '../context/LanguageContext'
import PasswordField from '../components/PasswordField'
import { useToast } from '../context/ToastContext'
import { googleLogin } from '../api/auth'
import { setAuthTokens } from '../utils/tokenStorage'
import { Card, Button, Input, Alert, Badge } from '../components/ui'
import { loadGsiClient } from '../utils/loadGsiClient'

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
  const googleBtnRef = useRef(null)
  const googleCallbackRef = useRef()

  googleCallbackRef.current = async (response) => {
    try {
      const { data } = await googleLogin(response.credential)
      setAuthTokens(data.access, data.refresh, true)
      window.location.href = '/'
    } catch {
      setError(t('oauth.failed'))
      toast?.error(t('oauth.failed'))
    }
  }

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
          text: 'signup_with',
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
      <Card variant="default" padding="lg" className="w-full max-w-md" animate staggerDelay={0.1}>
        <div className="flex justify-end mb-4 gap-2">
          {LANG_OPTIONS.map((opt, index) => (
            <Badge
              key={opt.code}
              variant={lang === opt.code ? 'primary' : 'outline'}
              size="sm"
              className="cursor-pointer"
              onClick={() => setLang(opt.code)}
            >
              {opt.label}
            </Badge>
          ))}
        </div>
        <div className="flex justify-center mb-3">
          <img src="/logo-icon.png" alt="HeartBox" decoding="async" className="w-36 h-36 object-contain" />
        </div>
        <h1 className="text-2xl font-bold text-center mb-2 bg-gradient-to-r from-orange-500 to-rose-500 bg-clip-text text-transparent">
          {t('app.displayName')}
        </h1>
        <p className="text-center text-slate-400 text-sm mb-6">{t('register.title')}</p>

        {error && (
          <Alert
            variant="danger"
            dismissible
            onClose={() => setError('')}
            className="mb-4"
          >
            {error}
          </Alert>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="register-username" className="sr-only">{t('register.username')}</label>
            <Input
              id="register-username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder={t('register.username')}
              autoComplete="username"
              required
            />
          </div>
          <div>
            <label htmlFor="register-email" className="sr-only">{t('register.email')}</label>
            <Input
              id="register-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onBlur={() => setEmailTouched(true)}
              placeholder={t('register.email')}
              error={emailTouched && !emailValid}
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
          <Button type="submit" disabled={loading} loading={loading} fullWidth>
            {loading ? t('register.loading') : t('register.submit')}
          </Button>
        </form>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-white/10" /></div>
          <div className="relative flex justify-center text-xs"><span className="px-2 bg-[var(--card-bg)] opacity-50">{t('oauth.or')}</span></div>
        </div>

        <div ref={googleBtnRef} className="w-full flex justify-center" />

        <p className="mt-4 text-center text-sm text-slate-400">
          {t('register.hasAccount')}{' '}
          <Link to="/login" className="text-orange-500 hover:text-orange-400 opacity-100">
            {t('register.login')}
          </Link>
        </p>
      </Card>
      <div className="mt-6 text-center text-xs opacity-40 space-x-3">
        <Link to="/privacy" className="hover:opacity-70">{t('legal.privacy')}</Link>
        <span>|</span>
        <Link to="/terms" className="hover:opacity-70">{t('legal.terms')}</Link>
      </div>
    </div>
  )
}
