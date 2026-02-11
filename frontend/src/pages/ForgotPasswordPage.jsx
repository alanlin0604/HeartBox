import { useState } from 'react'
import { Link } from 'react-router-dom'
import { forgotPassword } from '../api/auth'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'

export default function ForgotPasswordPage() {
  const { t } = useLang()
  const toast = useToast()
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await forgotPassword(email)
      toast?.success(t('password.resetSent'))
    } catch {
      toast?.error(t('password.resetFailed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="glass p-8 w-full max-w-md space-y-5">
        <h1 className="text-xl font-semibold">{t('password.forgotTitle')}</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder={t('register.email')}
            className="glass-input"
            required
          />
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? t('common.loading') : t('password.sendReset')}
          </button>
        </form>
        <Link to="/login" className="text-sm text-purple-400 hover:text-purple-300">
          {t('password.backToLogin')}
        </Link>
      </div>
    </div>
  )
}
