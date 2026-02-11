import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import PasswordField from '../components/PasswordField'
import { resetPassword } from '../api/auth'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'

export default function ResetPasswordPage() {
  const { t } = useLang()
  const toast = useToast()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const uid = useMemo(() => searchParams.get('uid') || '', [searchParams])
  const token = useMemo(() => searchParams.get('token') || '', [searchParams])
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (password !== confirm) {
      toast?.error(t('settings.passwordMismatch'))
      return
    }
    if (!uid || !token) {
      toast?.error(t('password.invalidResetLink'))
      return
    }
    setLoading(true)
    try {
      await resetPassword(uid, token, password)
      toast?.success(t('password.resetSuccess'))
      navigate('/login')
    } catch {
      toast?.error(t('password.resetFailed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="glass p-8 w-full max-w-md space-y-5">
        <h1 className="text-xl font-semibold">{t('password.resetTitle')}</h1>
        <form onSubmit={handleSubmit} className="space-y-4">
          <PasswordField
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={t('settings.newPassword')}
            required
            minLength={8}
            showStrength
          />
          <PasswordField
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            placeholder={t('settings.confirmPassword')}
            required
            minLength={8}
          />
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? t('common.loading') : t('password.resetNow')}
          </button>
        </form>
      </div>
    </div>
  )
}
