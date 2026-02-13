import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import { useLang } from '../context/LanguageContext'
import { useTheme } from '../context/ThemeContext'
import { logoutOtherDevices, updateProfile, deleteAccount, exportData } from '../api/auth'
import PasswordField from '../components/PasswordField'
import { useToast } from '../context/ToastContext'
import { isRememberedLogin, setAuthTokens } from '../utils/tokenStorage'

export default function SettingsPage() {
  const { user } = useAuth()
  const { t } = useLang()
  const { theme } = useTheme()
  const toast = useToast()

  const [email, setEmail] = useState(user?.email || '')
  const [bio, setBio] = useState(user?.bio || '')
  const [avatar, setAvatar] = useState(null)
  const [saving, setSaving] = useState(false)

  // Track initial profile values for unsaved-changes detection
  const initialProfile = useRef({ email: user?.email || '', bio: user?.bio || '' })

  useEffect(() => { document.title = `${t('settings.title')} — ${t('app.name')}` }, [t])

  useEffect(() => {
    const handleBeforeUnload = (e) => {
      const hasUnsavedChanges =
        email !== initialProfile.current.email ||
        bio !== initialProfile.current.bio ||
        avatar !== null
      if (hasUnsavedChanges) {
        e.preventDefault()
        e.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [email, bio, avatar])

  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [pwSaving, setPwSaving] = useState(false)
  const [logoutOthersLoading, setLogoutOthersLoading] = useState(false)
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [deletePassword, setDeletePassword] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [exporting, setExporting] = useState(false)

  const handleSaveProfile = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const formData = new FormData()
      formData.append('email', email)
      formData.append('bio', bio)
      if (avatar) formData.append('avatar', avatar)
      await updateProfile(formData)
      // Update initial values so beforeunload guard is cleared
      initialProfile.current = { email, bio }
      setAvatar(null)
      toast?.success(t('settings.saveSuccess'))
    } catch (err) {
      const data = err.response?.data
      if (data) {
        const msg = Object.values(data).flat().join(', ')
        toast?.error(msg || t('settings.saveFailed'))
      } else {
        toast?.error(t('settings.saveFailed'))
      }
    } finally {
      setSaving(false)
    }
  }

  const handleChangePassword = async (e) => {
    e.preventDefault()
    if (newPassword !== confirmPassword) {
      toast?.error(t('settings.passwordMismatch'))
      return
    }
    if (newPassword.length < 8) {
      toast?.error(t('settings.passwordTooShort'))
      return
    }
    setPwSaving(true)
    try {
      await updateProfile({ old_password: oldPassword, new_password: newPassword })
      toast?.success(t('settings.passwordSuccess'))
      setOldPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      const data = err.response?.data
      if (data?.old_password) {
        toast?.error(t('settings.oldPasswordWrong'))
      } else if (data) {
        const msg = Object.values(data).flat().join(', ')
        toast?.error(msg || t('settings.passwordFailed'))
      } else {
        toast?.error(t('settings.passwordFailed'))
      }
    } finally {
      setPwSaving(false)
    }
  }

  const handleExportData = async () => {
    setExporting(true)
    try {
      const res = await exportData()
      const blob = new Blob([res.data], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `heartbox_export_${user?.username || 'data'}.json`
      a.click()
      URL.revokeObjectURL(url)
      toast?.success(t('settings.saveSuccess'))
    } catch {
      toast?.error(t('settings.exportFailed'))
    } finally {
      setExporting(false)
    }
  }

  const handleDeleteAccount = async () => {
    if (!deletePassword) return
    setDeleting(true)
    try {
      await deleteAccount(deletePassword)
      window.location.href = '/login'
    } catch (err) {
      const msg = err.response?.data?.error || t('settings.deleteFailed')
      toast?.error(msg)
    } finally {
      setDeleting(false)
    }
  }

  const handleLogoutOthers = async () => {
    setLogoutOthersLoading(true)
    try {
      const { data } = await logoutOtherDevices()
      if (data?.access && data?.refresh) {
        setAuthTokens(data.access, data.refresh, isRememberedLogin())
      }
      toast?.success(t('settings.logoutOtherDevicesSuccess'))
    } catch {
      toast?.error(t('settings.logoutOtherDevicesFailed'))
    } finally {
      setLogoutOthersLoading(false)
    }
  }

  return (
    <div className="space-y-6 mt-4 max-w-2xl mx-auto overflow-x-hidden">
      <h1 className="text-2xl font-bold">{t('settings.title')}</h1>

      {/* Profile Section */}
      <form onSubmit={handleSaveProfile} className="glass p-4 sm:p-6 space-y-4">
        <h2 className="text-lg font-semibold">{t('settings.profile')}</h2>

        <div>
          <label className="block text-sm font-medium opacity-60 mb-1">
            {t('settings.username')}
          </label>
          <input
            type="text"
            value={user?.username || ''}
            disabled
            className="glass-input opacity-60 cursor-not-allowed"
          />
        </div>

        <div>
          <label className="block text-sm font-medium opacity-60 mb-1">
            {t('settings.email')}
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="glass-input"
          />
        </div>

        <div>
          <label className="block text-sm font-medium opacity-60 mb-1">
            {t('settings.bio')}
          </label>
          <textarea
            value={bio}
            onChange={(e) => setBio(e.target.value)}
            placeholder={t('settings.bioPlaceholder')}
            className="glass-input min-h-[100px] resize-y"
          />
        </div>
        <div>
          <label className="block text-sm font-medium opacity-60 mb-1">
            {t('settings.avatar')}
          </label>
          <input
            type="file"
            accept="image/*"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) {
                if (file.size > 2 * 1024 * 1024) {
                  toast?.error(t('settings.avatarTooLarge'))
                  e.target.value = ''
                  return
                }
                if (!file.type.startsWith('image/')) {
                  toast?.error(t('settings.avatarInvalid'))
                  e.target.value = ''
                  return
                }
              }
              setAvatar(file || null)
            }}
            className="glass-input"
          />
        </div>

        <button type="submit" disabled={saving} className="btn-primary">
          {saving ? t('settings.saving') : t('settings.save')}
        </button>
      </form>

      {/* Password Section */}
      <form onSubmit={handleChangePassword} className="glass p-4 sm:p-6 space-y-4">
        <h2 className="text-lg font-semibold">{t('settings.changePassword')}</h2>

        <div>
          <label className="block text-sm font-medium opacity-60 mb-1">
            {t('settings.oldPassword')}
          </label>
          <PasswordField
            value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium opacity-60 mb-1">
            {t('settings.newPassword')}
          </label>
          <PasswordField
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            showStrength
          />
        </div>

        <div>
          <label className="block text-sm font-medium opacity-60 mb-1">
            {t('settings.confirmPassword')}
          </label>
          <PasswordField
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />
        </div>

        <div className="flex flex-col sm:flex-row gap-2">
          <button type="submit" disabled={pwSaving} className="btn-primary">
            {pwSaving ? t('settings.saving') : t('settings.changePassword')}
          </button>
          <button type="button" onClick={handleLogoutOthers} disabled={logoutOthersLoading} className="btn-secondary">
            {logoutOthersLoading ? t('common.loading') : t('settings.logoutOtherDevices')}
          </button>
        </div>
      </form>

      {/* Account Info */}
      <div className="glass p-4 sm:p-6 space-y-3">
        <h2 className="text-lg font-semibold">{t('settings.accountInfo')}</h2>
        <div className="text-sm space-y-2 opacity-70">
          <p>{t('settings.joined')}: {user?.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}</p>
          <p>{t('settings.theme')}: {theme === 'dark' ? t('settings.themeDark') : t('settings.themeLight')}</p>
        </div>
      </div>

      {/* Data Export */}
      <div className="glass p-4 sm:p-6 space-y-3">
        <h2 className="text-lg font-semibold">{t('settings.exportData')}</h2>
        <p className="text-sm opacity-60">{t('settings.exportDataDesc')}</p>
        <button onClick={handleExportData} disabled={exporting} className="btn-secondary">
          {exporting ? t('settings.exporting') : t('settings.exportButton')}
        </button>
      </div>

      {/* Danger Zone - Delete Account */}
      <div className="glass p-4 sm:p-6 space-y-3 border border-red-500/20">
        <h2 className="text-lg font-semibold text-red-500">{t('settings.dangerZone')}</h2>
        <p className="text-sm opacity-60">{t('settings.deleteAccountDesc')}</p>
        <button
          onClick={() => setDeleteModalOpen(true)}
          className="btn-danger"
        >
          {t('settings.deleteAccount')}
        </button>
      </div>

      {/* Delete Account Modal */}
      {deleteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="popup-panel p-4 sm:p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold text-red-500">{t('settings.deleteAccountConfirm')}</h2>
            <p className="text-sm opacity-70">{t('settings.deleteAccountDesc')}</p>
            <input
              type="password"
              value={deletePassword}
              onChange={(e) => setDeletePassword(e.target.value)}
              placeholder={t('settings.deleteAccountPassword')}
              className="glass-input"
            />
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => { setDeleteModalOpen(false); setDeletePassword('') }}
                className="btn-secondary"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleDeleteAccount}
                disabled={deleting || !deletePassword}
                className="btn-danger"
              >
                {deleting ? t('settings.deleting') : t('settings.deleteAccountButton')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
