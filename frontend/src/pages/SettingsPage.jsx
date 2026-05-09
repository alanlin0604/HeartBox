import { useState, useEffect, useRef } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLang } from '../context/LanguageContext'
import { useTheme } from '../context/ThemeContext'
import { LOCALE_MAP } from '../utils/locales'
import { logoutOtherDevices, updateProfile, deleteAccount } from '../api/auth'
import PasswordField from '../components/PasswordField'
import ImportModal from '../components/ImportModal'
import { useToast } from '../context/ToastContext'
import { isRememberedLogin, setAuthTokens } from '../utils/tokenStorage'
import { subscribeToPush, unsubscribePush } from '../utils/pushNotifications'
import useHealthSync from '../hooks/useHealthSync'
import { getLastHealthBreadcrumbs, clearHealthBreadcrumbs, _crumb as crumb } from '../services/healthKit'
import { Card, Button, Input } from '../components/ui'
export default function SettingsPage() {
  const location = useLocation()
  const { user, refreshUser } = useAuth()
  const { t, lang } = useLang()
  const { theme } = useTheme()
  const toast = useToast()

  const [email, setEmail] = useState(user?.email || '')
  const [bio, setBio] = useState(user?.bio || '')
  const [avatar, setAvatar] = useState(null)
  const [saving, setSaving] = useState(false)
  const [fontScale, setFontScale] = useState(() => parseFloat(localStorage.getItem('heartbox_font_scale') || '1'))

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
  const [importOpen, setImportOpen] = useState(false)
  const [idleTimeout, setIdleTimeout] = useState(() => localStorage.getItem('heartbox_idle_timeout') || '30')
  const [pushEnabled, setPushEnabled] = useState(false)
  const [notifPrefs, setNotifPrefs] = useState([])
  const [twoFAEnabled, setTwoFAEnabled] = useState(false)
  const [setupQR, setSetupQR] = useState(null)
  const [totpCode, setTotpCode] = useState('')
  const [disablePassword, setDisablePassword] = useState('')
  const [currentSub, setCurrentSub] = useState(null)
  const [userTimezone, setUserTimezone] = useState(user?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone)
  const health = useHealthSync()
  const [activeTab, setActiveTab] = useState('profile')

  // Handle tab navigation from other pages
  useEffect(() => {
    if (location.state?.tab) {
      setActiveTab(location.state.tab)
    }
  }, [location.state?.tab])

  useEffect(() => {
    // Notification preferences
    import('../api/axios').then(({ default: api }) => {
      api.get('/notifications/preferences/').then(r => setNotifPrefs(r.data)).catch(() => {})
      api.get('/auth/2fa/setup/').then(r => setTwoFAEnabled(r.data.enabled)).catch(() => {})
      api.get('/subscriptions/me/').then(r => setCurrentSub(r.data)).catch(() => {})
    })
  }, [user])

  const handleSaveProfile = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const formData = new FormData()
      formData.append('email', email)
      formData.append('bio', bio)
      if (avatar) formData.append('avatar', avatar)
      await updateProfile(formData)
      await refreshUser()
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

  const handleDeleteAccount = async () => {
    if (!deletePassword) return
    setDeleting(true)
    try {
      await deleteAccount(deletePassword)
      window.location.href = '/login'
    } catch (err) {
      const msg = err.response?.data?.detail || t('settings.deleteFailed')
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

  const tabs = [
    { id: 'profile', label: t('settings.tabProfile') },
    { id: 'preferences', label: t('settings.tabPreferences') },
    { id: 'health', label: t('settings.tabHealth') },
    { id: 'data', label: t('settings.tabData') },
    { id: 'security', label: t('settings.tabSecurity') },
  ]

  return (
    <div className="space-y-6 mt-4 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold">{t('settings.title')}</h1>

      {/* Tab Navigation */}
      <Card variant="default" padding="sm" className="flex gap-2 flex-wrap">
        {tabs.map((tab) => (
          <Button
            key={tab.id}
            variant={activeTab === tab.id ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </Button>
        ))}
      </Card>

      {/* === Profile Tab === */}
      {activeTab === 'profile' && (
        <Card variant="default" padding="lg" className="space-y-6" animate staggerDelay={0.1}>
          {/* Profile Section */}
          <form onSubmit={handleSaveProfile} className="space-y-4">
            <h2 className="text-lg font-semibold">{t('settings.profile')}</h2>

            <div>
              <label htmlFor="settings-username" className="block text-sm font-medium text-slate-400 mb-1">
                {t('settings.username')}
              </label>
              <Input
                id="settings-username"
                type="text"
                value={user?.username || ''}
                disabled
                className="opacity-60 cursor-not-allowed"
              />
            </div>

            <div>
              <label htmlFor="settings-email" className="block text-sm font-medium text-slate-400 mb-1">
                {t('settings.email')}
              </label>
              <Input
                id="settings-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div>
              <label htmlFor="settings-bio" className="block text-sm font-medium text-slate-400 mb-1">
                {t('settings.bio')}
              </label>
              <textarea
                id="settings-bio"
                value={bio}
                onChange={(e) => setBio(e.target.value)}
                placeholder={t('settings.bioPlaceholder')}
                className="glass-input min-h-[100px] resize-y"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-400 mb-1">
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

            <Button type="submit" disabled={saving} loading={saving}>
              {saving ? t('settings.saving') : t('settings.save')}
            </Button>
          </form>

          <div className="border-t border-[var(--card-border)]" />

          {/* Password Section */}
          <form onSubmit={handleChangePassword} className="space-y-4">
            <h2 className="text-lg font-semibold">{t('settings.changePassword')}</h2>

            <div>
              <label htmlFor="settings-old-password" className="block text-sm font-medium text-slate-400 mb-1">
                {t('settings.oldPassword')}
              </label>
              <PasswordField
                id="settings-old-password"
                value={oldPassword}
                onChange={(e) => setOldPassword(e.target.value)}
                required
              />
            </div>

            <div>
              <label htmlFor="settings-new-password" className="block text-sm font-medium text-slate-400 mb-1">
                {t('settings.newPassword')}
              </label>
              <PasswordField
                id="settings-new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                showStrength
              />
            </div>

            <div>
              <label htmlFor="settings-confirm-password" className="block text-sm font-medium text-slate-400 mb-1">
                {t('settings.confirmPassword')}
              </label>
              <PasswordField
                id="settings-confirm-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
              />
            </div>

            <div className="flex flex-col sm:flex-row gap-2">
              <Button type="submit" disabled={pwSaving} loading={pwSaving}>
                {pwSaving ? t('settings.saving') : t('settings.changePassword')}
              </Button>
              <Button type="button" variant="secondary" onClick={handleLogoutOthers} disabled={logoutOthersLoading} loading={logoutOthersLoading}>
                {logoutOthersLoading ? t('common.loading') : t('settings.logoutOtherDevices')}
              </Button>
            </div>
          </form>
        </Card>
      )}

      {/* === Preferences Tab === */}
      {activeTab === 'preferences' && (
        <Card variant="default" padding="lg" className="space-y-6" animate staggerDelay={0.1}>
          {/* Font Size */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t('settings.fontSize')}</h2>
            <div className="flex gap-3 flex-wrap">
              {[
                { label: t('settings.fontSmall'), scale: 0.875 },
                { label: t('settings.fontMedium'), scale: 1 },
                { label: t('settings.fontLarge'), scale: 1.125 },
              ].map((opt) => (
                  <button
                    key={opt.scale}
                    type="button"
                    onClick={() => {
                      localStorage.setItem('heartbox_font_scale', String(opt.scale))
                      document.documentElement.style.fontSize = opt.scale * 16 + 'px'
                      setFontScale(opt.scale)
                    }}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
                      fontScale === opt.scale
                        ? 'bg-orange-500/30 text-orange-400'
                        : 'opacity-60 hover:opacity-100 border border-[var(--card-border)]'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
            </div>
          </div>

          <div className="border-t border-[var(--card-border)]" />

          {/* Timezone */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t('settings.timezone')}</h2>
            <select
              value={userTimezone}
              onChange={async (e) => {
                const tz = e.target.value
                setUserTimezone(tz)
                try {
                  await updateProfile({ timezone: tz })
                  await refreshUser()
                  toast?.success(t('settings.saveSuccess'))
                } catch { toast?.error(t('settings.saveFailed')) }
              }}
              className="glass-input"
            >
              {(() => {
                const COMMON_TIMEZONES = [
                  { id: 'Asia/Taipei', 'zh-TW': '台北', en: 'Taipei', ja: '台北' },
                  { id: 'Asia/Tokyo', 'zh-TW': '東京', en: 'Tokyo', ja: '東京' },
                  { id: 'Asia/Shanghai', 'zh-TW': '上海', en: 'Shanghai', ja: '上海' },
                  { id: 'Asia/Hong_Kong', 'zh-TW': '香港', en: 'Hong Kong', ja: '香港' },
                  { id: 'Asia/Singapore', 'zh-TW': '新加坡', en: 'Singapore', ja: 'シンガポール' },
                  { id: 'Asia/Seoul', 'zh-TW': '首爾', en: 'Seoul', ja: 'ソウル' },
                  { id: 'Asia/Bangkok', 'zh-TW': '曼谷', en: 'Bangkok', ja: 'バンコク' },
                  { id: 'Asia/Kolkata', 'zh-TW': '加爾各答', en: 'Kolkata', ja: 'コルカタ' },
                  { id: 'Asia/Dubai', 'zh-TW': '杜拜', en: 'Dubai', ja: 'ドバイ' },
                  { id: 'Asia/Jakarta', 'zh-TW': '雅加達', en: 'Jakarta', ja: 'ジャカルタ' },
                  { id: 'Australia/Sydney', 'zh-TW': '雪梨', en: 'Sydney', ja: 'シドニー' },
                  { id: 'Australia/Melbourne', 'zh-TW': '墨爾本', en: 'Melbourne', ja: 'メルボルン' },
                  { id: 'Pacific/Auckland', 'zh-TW': '奧克蘭', en: 'Auckland', ja: 'オークランド' },
                  { id: 'Europe/London', 'zh-TW': '倫敦', en: 'London', ja: 'ロンドン' },
                  { id: 'Europe/Paris', 'zh-TW': '巴黎', en: 'Paris', ja: 'パリ' },
                  { id: 'Europe/Berlin', 'zh-TW': '柏林', en: 'Berlin', ja: 'ベルリン' },
                  { id: 'Europe/Moscow', 'zh-TW': '莫斯科', en: 'Moscow', ja: 'モスクワ' },
                  { id: 'Europe/Istanbul', 'zh-TW': '伊斯坦堡', en: 'Istanbul', ja: 'イスタンブール' },
                  { id: 'America/New_York', 'zh-TW': '紐約', en: 'New York', ja: 'ニューヨーク' },
                  { id: 'America/Chicago', 'zh-TW': '芝加哥', en: 'Chicago', ja: 'シカゴ' },
                  { id: 'America/Denver', 'zh-TW': '丹佛', en: 'Denver', ja: 'デンバー' },
                  { id: 'America/Los_Angeles', 'zh-TW': '洛杉磯', en: 'Los Angeles', ja: 'ロサンゼルス' },
                  { id: 'America/Sao_Paulo', 'zh-TW': '聖保羅', en: 'São Paulo', ja: 'サンパウロ' },
                  { id: 'America/Vancouver', 'zh-TW': '溫哥華', en: 'Vancouver', ja: 'バンクーバー' },
                  { id: 'Pacific/Honolulu', 'zh-TW': '檀香山', en: 'Honolulu', ja: 'ホノルル' },
                ]
                const isInList = COMMON_TIMEZONES.some(tz => tz.id === userTimezone)
                const items = isInList ? COMMON_TIMEZONES : [{ id: userTimezone, 'zh-TW': userTimezone, en: userTimezone, ja: userTimezone }, ...COMMON_TIMEZONES]
                return items.map(tz => (
                  <option key={tz.id} value={tz.id}>{tz[lang] || tz.en} ({tz.id})</option>
                ))
              })()}
            </select>
          </div>

          <div className="border-t border-[var(--card-border)]" />

          {/* Idle Auto-Logout */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t('idle.settingsTitle')}</h2>
            <div className="flex gap-3 flex-wrap">
              {[
                { label: t('idle.minutes15'), value: '15' },
                { label: t('idle.minutes30'), value: '30' },
                { label: t('idle.minutes60'), value: '60' },
                { label: t('idle.disabled'), value: '0' },
              ].map(opt => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => {
                    localStorage.setItem('heartbox_idle_timeout', opt.value)
                    setIdleTimeout(opt.value)
                  }}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors cursor-pointer ${
                    idleTimeout === opt.value
                      ? 'bg-orange-500/30 text-orange-400'
                      : 'opacity-60 hover:opacity-100 border border-[var(--card-border)]'
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-[var(--card-border)]" />

          {/* Notification Preferences */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t('notifPref.title')}</h2>
            {['message', 'booking', 'share', 'weekly_report', 'achievement', 'system'].map(type => {
              const pref = notifPrefs.find(p => p.notification_type === type)
              const enabled = pref ? pref.enabled : true
              return (
                <label key={type} className="flex items-center justify-between py-1">
                  <span className="text-sm">{t(`notifPref.${type}`)}</span>
                  <input
                    type="checkbox"
                    checked={enabled}
                    onChange={async (e) => {
                      const val = e.target.checked
                      try {
                        const { default: api } = await import('../api/axios')
                        await api.patch('/notifications/preferences/', { notification_type: type, enabled: val })
                        setNotifPrefs(prev => {
                          const idx = prev.findIndex(p => p.notification_type === type)
                          if (idx >= 0) { const n = [...prev]; n[idx] = { ...n[idx], enabled: val }; return n }
                          return [...prev, { notification_type: type, enabled: val }]
                        })
                      } catch { /* network err — preference UI stays in last-known state */ }
                    }}
                    className="w-5 h-5 accent-orange-500"
                  />
                </label>
              )
            })}
          </div>

          <div className="border-t border-[var(--card-border)]" />

          {/* Push Notifications */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t('push.title')}</h2>
            <label className="flex items-center justify-between">
              <span className="text-sm">{t('push.enableDesc')}</span>
              <input
                type="checkbox"
                checked={pushEnabled}
                onChange={async (e) => {
                  if (e.target.checked) {
                    const ok = await subscribeToPush()
                    setPushEnabled(ok)
                    if (!ok) toast?.error(t('push.failed'))
                  } else {
                    await unsubscribePush()
                    setPushEnabled(false)
                  }
                }}
                className="w-5 h-5 accent-orange-500"
              />
            </label>
          </div>
        </Card>
      )}

      {/* === Health Tab === */}
      {activeTab === 'health' && (
        <Card variant="default" padding="lg" className="space-y-6" animate staggerDelay={0.1}>
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t('health.connectionTitle')}</h2>
            <p className="text-sm text-slate-400">{t('health.connectionDesc')}</p>

            {health.available ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-3 h-3 rounded-full ${health.enabled ? 'bg-green-500' : 'bg-gray-400'}`} />
                    <span className="text-sm font-medium">
                      {health.platform === 'ios' ? 'Apple Health' : 'Health Connect'}
                    </span>
                  </div>
                  {health.enabled ? (
                    <button
                      onClick={health.disconnect}
                      className="btn-secondary text-sm"
                    >
                      {t('health.disconnect')}
                    </button>
                  ) : (
                    <button
                      onClick={async () => {
                        crumb('btn:connect:clicked')
                        try {
                          const ok = await health.connect()
                          crumb('btn:connect:returned', ok)
                          if (ok) toast?.success(t('health.connected'))
                          else toast?.error(t('health.connectFailed'))
                        } catch (e) {
                          crumb('btn:connect:threw', String(e?.message || e))
                          toast?.error(t('health.connectFailed'))
                        }
                      }}
                      className="btn-primary text-sm"
                    >
                      {t('health.connect')}
                    </button>
                  )}
                </div>

                {/* Diagnostic breadcrumbs — shows where the last connect attempt died.
                    Survives the native crash via localStorage; helps debug Health
                    Connect issues without needing adb logcat. */}
                {/* HC diagnostic panel — only shown when the user explicitly
                    sets `localStorage.heartbox_health_debug = '1'`. Breadcrumbs
                    are still recorded silently on every connect attempt so the
                    panel has data the moment it's enabled. See
                    docs/health-connect-debug-progress.md. */}
                {(() => {
                  if (typeof window === 'undefined') return null
                  if (window.localStorage?.getItem('heartbox_health_debug') !== '1') return null
                  const crumbs = getLastHealthBreadcrumbs()
                  return (
                    <div className="text-xs bg-amber-500/10 rounded-lg p-3 border border-amber-500/30 space-y-2">
                      <div className="font-bold text-amber-400">Health Connect diagnostic</div>
                      {crumbs.length === 0 ? (
                        <div className="opacity-60">No breadcrumbs yet — try connecting once.</div>
                      ) : (
                        <details open>
                          <summary className="cursor-pointer text-slate-300">
                            {crumbs.length} steps, last: {crumbs[crumbs.length - 1].stage}
                          </summary>
                          <pre className="mt-2 overflow-auto whitespace-pre-wrap text-[11px] leading-relaxed">
                            {crumbs.map(c => `${c.ts.split('T')[1]?.slice(0, 12)} ${c.stage}${c.payload !== undefined ? ' ' + JSON.stringify(c.payload) : ''}`).join('\n')}
                          </pre>
                          <button
                            onClick={() => { clearHealthBreadcrumbs(); window.location.reload() }}
                            className="mt-2 text-[11px] underline opacity-70"
                          >
                            Clear & reload
                          </button>
                        </details>
                      )}
                    </div>
                  )
                })()}

                {health.enabled && (
                  <>
                    <div className="border-t border-[var(--card-border)]" />

                    <div className="space-y-3">
                      <h3 className="text-sm font-medium">{t('health.syncStatus')}</h3>
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-slate-400">{t('health.lastSync')}</span>
                        <span>
                          {health.lastSync
                            ? new Date(health.lastSync).toLocaleString()
                            : t('health.never')}
                        </span>
                      </div>
                      <button
                        onClick={async () => {
                          const ok = await health.syncNow()
                          if (ok) toast?.success(t('health.syncSuccess'))
                          else toast?.error(t('health.syncFailed'))
                        }}
                        disabled={health.syncing}
                        className="btn-secondary text-sm"
                      >
                        {health.syncing ? t('health.syncing') : t('health.syncNow')}
                      </button>
                    </div>

                    <div className="border-t border-[var(--card-border)]" />

                    <div className="space-y-2">
                      <h3 className="text-sm font-medium">{t('health.dataTypes')}</h3>
                      <div className="grid grid-cols-2 gap-2 text-sm opacity-70">
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-blue-400" />
                          {t('health.steps')}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-red-400" />
                          {t('health.heartRate')}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-orange-400" />
                          {t('health.hrv')}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-orange-400" />
                          {t('health.calories')}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-green-400" />
                          {t('health.exerciseMinutes')}
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full bg-indigo-400" />
                          {t('health.sleepData')}
                        </div>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
                <p className="text-sm text-yellow-500">{t('health.notAvailable')}</p>
                <p className="text-xs opacity-60 mt-1">{t('health.notAvailableDesc')}</p>
              </div>
            )}
          </div>
        </Card>
      )}

      {/* === Data Tab === */}
      {activeTab === 'data' && (
        <Card variant="default" padding="lg" className="space-y-6" animate staggerDelay={0.1}>
          {/* Data Import */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t('import.title')}</h2>
            <p className="text-sm text-slate-400">{t('import.settingsDesc')}</p>
            <button onClick={() => setImportOpen(true)} className="btn-secondary">{t('import.button')}</button>
          </div>

          {importOpen && <ImportModal onClose={() => setImportOpen(false)} onSuccess={() => {}} />}

          <div className="border-t border-[var(--card-border)]" />

          {/* Account Info */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t('settings.accountInfo')}</h2>
            <div className="text-sm space-y-2 text-slate-400">
              <p>{t('settings.joined')}: {user?.created_at ? new Date(user.created_at).toLocaleDateString(LOCALE_MAP[lang] || lang) : '-'}</p>
              <p>{t('settings.theme')}: {theme === 'dark' ? t('settings.themeDark') : t('settings.themeLight')}</p>
            </div>
          </div>

          <div className="border-t border-[var(--card-border)]" />

          {/* Subscription */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t('subscription.title')}</h2>
            {currentSub?.plan ? (
              <div className="text-sm space-y-1">
                <p>{t('subscription.currentPlan')}: <span className="font-semibold">{currentSub.plan_name}</span></p>
                <p>{t('subscription.status')}: {currentSub.status}</p>
              </div>
            ) : (
              <p className="text-sm text-slate-400">{t('subscription.noPlan')}</p>
            )}
            <Link to="/pricing" className="btn-secondary inline-block">{t('subscription.viewPlans')}</Link>
          </div>
        </Card>
      )}

      {/* === Security Tab === */}
      {activeTab === 'security' && (
        <Card variant="default" padding="lg" className="space-y-6" animate staggerDelay={0.1}>
          {/* Two-Factor Authentication */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">{t('twofa.title')}</h2>
              {twoFAEnabled && (
                <span className="text-xs font-medium text-green-500 px-2 py-1 rounded-lg bg-green-500/10">{t('twofa.enabled')}</span>
              )}
            </div>
            {twoFAEnabled ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">{t('twofa.passwordToDisable')}</label>
                  <input
                    type="password"
                    value={disablePassword}
                    onChange={e => setDisablePassword(e.target.value)}
                    placeholder={t('twofa.passwordToDisable')}
                    className="glass-input"
                  />
                </div>
                <button
                  onClick={async () => {
                    try {
                      const { default: api } = await import('../api/axios')
                      await api.post('/auth/2fa/disable/', { password: disablePassword })
                      setTwoFAEnabled(false)
                      setDisablePassword('')
                      toast?.success(t('twofa.disabled'))
                    } catch { toast?.error(t('twofa.disableFailed')) }
                  }}
                  disabled={!disablePassword}
                  className="btn-danger"
                >
                  {t('twofa.disable')}
                </button>
              </div>
            ) : setupQR ? (
              <div className="space-y-4">
                <div className="text-sm text-slate-400 space-y-1">
                  <p>{t('twofa.step1')}</p>
                  <p>{t('twofa.step2')}</p>
                  <p>{t('twofa.step3')}</p>
                </div>
                <div className="text-center">
                  <img src={setupQR.qr_code} alt="QR Code" className="mx-auto w-48 h-48" />
                </div>
                <div className="p-3 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-sm">
                  <p className="font-medium text-yellow-500">{t('twofa.secretKey')}: <span className="break-all font-mono">{setupQR.secret}</span></p>
                  <p className="text-xs text-slate-400 mt-1">{t('twofa.backupWarning')}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-400 mb-1">{t('twofa.enterCode')}</label>
                  <input
                    type="text"
                    value={totpCode}
                    onChange={e => setTotpCode(e.target.value)}
                    placeholder={t('twofa.enterCode')}
                    maxLength={6}
                    className="glass-input text-center text-lg tracking-widest"
                  />
                </div>
                <div className="flex gap-3">
                  <button onClick={() => setSetupQR(null)} className="btn-secondary flex-1">{t('common.cancel')}</button>
                  <button
                    onClick={async () => {
                      try {
                        const { default: api } = await import('../api/axios')
                        await api.post('/auth/2fa/verify/', { code: totpCode })
                        setTwoFAEnabled(true)
                        setSetupQR(null)
                        setTotpCode('')
                        toast?.success(t('twofa.enabledSuccess'))
                      } catch { toast?.error(t('twofa.verifyFailed')) }
                    }}
                    disabled={totpCode.length !== 6}
                    className="btn-primary flex-1"
                  >
                    {t('twofa.verify')}
                  </button>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-slate-400">{t('twofa.description')}</p>
                <p className="text-xs text-slate-400">{t('twofa.recommendedApps')}</p>
                <button
                  onClick={async () => {
                    try {
                      const { default: api } = await import('../api/axios')
                      const { data } = await api.post('/auth/2fa/setup/')
                      setSetupQR(data)
                    } catch { toast?.error(t('twofa.setupFailed')) }
                  }}
                  className="btn-primary"
                >
                  {t('twofa.enable')}
                </button>
              </div>
            )}
          </div>

          <div className="border-t border-[var(--card-border)]" />

          {/* Danger Zone - Delete Account */}
          <div className="space-y-3">
            <h2 className="text-lg font-semibold text-red-500">{t('settings.dangerZone')}</h2>
            <p className="text-sm text-slate-400">{t('settings.deleteAccountDesc')}</p>
            <button
              onClick={() => setDeleteModalOpen(true)}
              className="btn-danger"
            >
              {t('settings.deleteAccount')}
            </button>
          </div>
        </Card>
      )}

      {/* Legal — privacy/terms (also helps Google Play reviewers find policy) */}
      <Card variant="default" padding="md">
        <h2 className="text-lg font-semibold mb-3">{t('settings.legal')}</h2>
        <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
          <Link to="/privacy" className="text-orange-400 hover:text-orange-300 underline">
            {t('legal.privacy')}
          </Link>
          <Link to="/privacy#health-data" className="text-orange-400 hover:text-orange-300 underline">
            {t('settings.healthDataPolicy')}
          </Link>
          <Link to="/terms" className="text-orange-400 hover:text-orange-300 underline">
            {t('legal.terms')}
          </Link>
        </div>
      </Card>

      {/* Delete Account Modal */}
      {deleteModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="popup-panel p-4 sm:p-6 w-full max-w-md space-y-4" role="dialog" aria-modal="true">
            <h2 className="text-lg font-semibold text-red-500">{t('settings.deleteAccountConfirm')}</h2>
            <p className="text-sm text-slate-400">{t('settings.deleteAccountDesc')}</p>
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
