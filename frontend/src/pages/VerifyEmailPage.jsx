import { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'
import { useAuth } from '../context/AuthContext'
import { verifyEmail } from '../api/auth'
import { getAccessToken } from '../utils/tokenStorage'

export default function VerifyEmailPage() {
  const { t } = useLang()
  const { refreshUser } = useAuth()
  const [params] = useSearchParams()
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    let cancelled = false
    const uid = params.get('uid')
    const token = params.get('token')
    if (!uid || !token) {
      setStatus('error')
      return
    }
    verifyEmail(uid, token)
      .then(async () => {
        if (cancelled) return
        setStatus('success')
        if (getAccessToken()) {
          await refreshUser()
        }
      })
      .catch(() => { if (!cancelled) setStatus('error') })
    return () => { cancelled = true }
  }, [params, refreshUser])

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="glass p-8 max-w-md w-full text-center space-y-4">
        <h1 className="text-2xl font-bold">
          {status === 'loading' && t('common.loading')}
          {status === 'success' && t('email.verifySuccess')}
          {status === 'error' && t('email.verifyFailed')}
        </h1>
        {status !== 'loading' && (
          <Link to="/login" className="btn-primary inline-block">{t('login.submit')}</Link>
        )}
      </div>
    </div>
  )
}
