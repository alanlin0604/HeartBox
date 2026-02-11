import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLang } from '../context/LanguageContext'
import PasswordField from '../components/PasswordField'
import { useToast } from '../context/ToastContext'

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
        const messages = Object.values(data).flat().join(', ')
        setError(messages || t('register.failed'))
        toast?.error(messages || t('register.failed'))
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
        <h1 className="text-2xl font-bold text-center mb-2 bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent">
          HeartBox-心事盒
        </h1>
        <p className="text-center opacity-60 text-sm mb-6">{t('register.title')}</p>

        {error && (
          <div role="alert" className="mb-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder={t('register.username')}
            className="glass-input"
            required
          />
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t('register.email')}
            className="glass-input"
            required
          />
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
