import { useState, useEffect, useCallback } from 'react'
import {
  getStats,
  getUsers,
  updateUser,
  getCounselors,
  counselorAction,
  getFeedback,
} from '../api/admin'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'
import { LOCALE_MAP } from '../utils/locales'
import ConfirmModal from '../components/ConfirmModal'

export default function AdminPage() {
  const { t } = useLang()
  const [tab, setTab] = useState(0)

  useEffect(() => { document.title = `${t('admin.title')} — ${t('app.name')}` }, [t])

  const TABS = [t('admin.tabOverview'), t('admin.tabUsers'), t('admin.tabCounselors'), t('admin.tabFeedback')]

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">{t('admin.title')}</h2>
      <div className="flex gap-2 flex-wrap">
        {TABS.map((label, i) => (
          <button
            key={label}
            onClick={() => setTab(i)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors cursor-pointer ${
              tab === i
                ? 'bg-purple-600 text-white'
                : 'glass opacity-70 hover:opacity-100'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === 0 && <StatsTab />}
      {tab === 1 && <UsersTab />}
      {tab === 2 && <CounselorsTab />}
      {tab === 3 && <FeedbackTab />}
    </div>
  )
}

/* ==================== Tab 1: Stats ==================== */

function StatsTab() {
  const { t } = useLang()
  const toast = useToast()
  const [stats, setStats] = useState(null)

  useEffect(() => {
    getStats()
      .then((r) => setStats(r.data))
      .catch(() => toast?.error(t('common.operationFailed')))
  }, [])

  if (!stats) return <p className="opacity-60">{t('common.loading')}</p>

  const cards = [
    { label: t('admin.totalUsers'), value: stats.total_users, color: 'from-purple-500 to-indigo-500' },
    { label: t('admin.totalNotes'), value: stats.total_notes, color: 'from-pink-500 to-rose-500' },
    { label: t('admin.pendingCounselors'), value: stats.pending_counselors, color: 'from-amber-500 to-orange-500' },
    { label: t('admin.todayNewUsers'), value: stats.today_new_users, color: 'from-emerald-500 to-teal-500' },
    { label: t('admin.todayNewNotes'), value: stats.today_new_notes, color: 'from-cyan-500 to-blue-500' },
    { label: t('admin.activeUsers'), value: stats.active_users, color: 'from-violet-500 to-purple-500' },
  ]

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {cards.map((c) => (
        <div key={c.label} className="glass p-5 rounded-xl">
          <p className="text-sm opacity-60 mb-1">{c.label}</p>
          <p className={`text-3xl font-bold bg-gradient-to-r ${c.color} bg-clip-text text-transparent`}>
            {c.value}
          </p>
        </div>
      ))}
    </div>
  )
}

/* ==================== Tab 2: Users ==================== */

function UsersTab() {
  const { t, lang } = useLang()
  const toast = useToast()
  const [users, setUsers] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)
  const [confirmAction, setConfirmAction] = useState(null)

  const fetchUsers = useCallback(() => {
    setLoading(true)
    getUsers(search)
      .then((r) => setUsers(r.data.results ?? r.data))
      .catch(() => toast?.error(t('common.operationFailed')))
      .finally(() => setLoading(false))
  }, [search])

  useEffect(() => {
    const timer = setTimeout(fetchUsers, 300)
    return () => clearTimeout(timer)
  }, [fetchUsers])

  const requestToggle = (user, field) => {
    const label = field === 'is_active'
      ? (user.is_active ? t('admin.actionDeactivate') : t('admin.actionActivate'))
      : (user.is_staff ? t('admin.actionRemoveAdmin') : t('admin.actionMakeAdmin'))
    setConfirmAction({ user, field, label })
  }

  const executeToggle = async () => {
    if (!confirmAction) return
    const { user, field } = confirmAction
    try {
      await updateUser(user.id, { [field]: !user[field] })
      fetchUsers()
    } catch {
      toast?.error(t('common.operationFailed'))
    } finally {
      setConfirmAction(null)
    }
  }

  const roleBadge = (u) => {
    if (u.is_superuser) return <span className="px-2 py-0.5 rounded-full text-xs bg-red-500/20 text-red-400">{t('admin.roleSuperAdmin')}</span>
    if (u.is_staff) return <span className="px-2 py-0.5 rounded-full text-xs bg-purple-500/20 text-purple-400">{t('admin.roleAdmin')}</span>
    if (u.is_counselor) return <span className="px-2 py-0.5 rounded-full text-xs bg-emerald-500/20 text-emerald-400">{t('admin.roleCounselor')}</span>
    return <span className="px-2 py-0.5 rounded-full text-xs bg-gray-500/20 opacity-60">{t('admin.roleUser')}</span>
  }

  return (
    <div className="space-y-4">
      <input
        type="text"
        placeholder={t('admin.searchPlaceholder')}
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="glass w-full md:w-80 px-4 py-2 rounded-lg outline-none focus:ring-2 focus:ring-purple-500"
      />

      {loading ? (
        <p className="opacity-60">{t('common.loading')}</p>
      ) : (
        <>
        {/* Desktop table */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-left opacity-60">
                <th className="pb-2 pr-4">{t('admin.colId')}</th>
                <th className="pb-2 pr-4">{t('admin.colUsername')}</th>
                <th className="pb-2 pr-4">{t('admin.colEmail')}</th>
                <th className="pb-2 pr-4">{t('admin.colRole')}</th>
                <th className="pb-2 pr-4">{t('admin.colStatus')}</th>
                <th className="pb-2 pr-4">{t('admin.colJoined')}</th>
                <th className="pb-2">{t('admin.colActions')}</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className="border-b border-white/5 hover:bg-white/5">
                  <td className="py-2 pr-4">{u.id}</td>
                  <td className="py-2 pr-4 font-medium">{u.username}</td>
                  <td className="py-2 pr-4 opacity-70">{u.email}</td>
                  <td className="py-2 pr-4">{roleBadge(u)}</td>
                  <td className="py-2 pr-4">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${u.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                      {u.is_active ? t('admin.statusActive') : t('admin.statusInactive')}
                    </span>
                  </td>
                  <td className="py-2 pr-4 opacity-70">{new Date(u.date_joined).toLocaleDateString(LOCALE_MAP[lang] || lang)}</td>
                  <td className="py-2 space-x-2">
                    {!u.is_superuser && (
                      <>
                        <button
                          onClick={() => requestToggle(u, 'is_active')}
                          className={`px-2 py-1 rounded text-xs cursor-pointer ${u.is_active ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30' : 'bg-green-500/20 text-green-400 hover:bg-green-500/30'}`}
                        >
                          {u.is_active ? t('admin.actionDeactivate') : t('admin.actionActivate')}
                        </button>
                        <button
                          onClick={() => requestToggle(u, 'is_staff')}
                          className={`px-2 py-1 rounded text-xs cursor-pointer ${u.is_staff ? 'bg-gray-500/20 opacity-70 hover:bg-gray-500/30' : 'bg-purple-500/20 text-purple-400 hover:bg-purple-500/30'}`}
                        >
                          {u.is_staff ? t('admin.actionRemoveAdmin') : t('admin.actionMakeAdmin')}
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {users.length === 0 && <p className="text-center py-8 opacity-50">{t('admin.noUsers')}</p>}
        </div>

        {/* Mobile cards */}
        <div className="md:hidden space-y-3">
          {users.map((u) => (
            <div key={u.id} className="glass-card p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium">{u.username}</span>
                {roleBadge(u)}
              </div>
              <p className="text-xs opacity-60">{u.email}</p>
              <div className="flex items-center gap-2 text-xs">
                <span className={`px-2 py-0.5 rounded-full ${u.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                  {u.is_active ? t('admin.statusActive') : t('admin.statusInactive')}
                </span>
                <span className="opacity-50">{new Date(u.date_joined).toLocaleDateString(LOCALE_MAP[lang] || lang)}</span>
              </div>
              {!u.is_superuser && (
                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => requestToggle(u, 'is_active')}
                    className={`px-2 py-1 rounded text-xs cursor-pointer ${u.is_active ? 'bg-red-500/20 text-red-400' : 'bg-green-500/20 text-green-400'}`}
                  >
                    {u.is_active ? t('admin.actionDeactivate') : t('admin.actionActivate')}
                  </button>
                  <button
                    onClick={() => requestToggle(u, 'is_staff')}
                    className={`px-2 py-1 rounded text-xs cursor-pointer ${u.is_staff ? 'bg-gray-500/20 opacity-70' : 'bg-purple-500/20 text-purple-400'}`}
                  >
                    {u.is_staff ? t('admin.actionRemoveAdmin') : t('admin.actionMakeAdmin')}
                  </button>
                </div>
              )}
            </div>
          ))}
          {users.length === 0 && <p className="text-center py-8 opacity-50">{t('admin.noUsers')}</p>}
        </div>
        </>
      )}
      <ConfirmModal
        open={!!confirmAction}
        title={confirmAction?.label || ''}
        message={`${confirmAction?.label} ${confirmAction?.user?.username}?`}
        confirmText={t('common.confirm')}
        cancelText={t('common.cancel')}
        onConfirm={executeToggle}
        onCancel={() => setConfirmAction(null)}
      />
    </div>
  )
}

/* ==================== Tab 3: Counselors ==================== */

function CounselorsTab() {
  const { t, lang } = useLang()
  const toast = useToast()
  const [counselors, setCounselors] = useState([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(false)

  const STATUS_FILTERS = [
    { label: t('admin.filterAll'), value: '' },
    { label: t('admin.filterPending'), value: 'pending' },
    { label: t('admin.filterApproved'), value: 'approved' },
    { label: t('admin.filterRejected'), value: 'rejected' },
  ]

  const fetchCounselors = useCallback(() => {
    setLoading(true)
    getCounselors(filter)
      .then((r) => setCounselors(r.data.results ?? r.data))
      .finally(() => setLoading(false))
  }, [filter])

  useEffect(() => { fetchCounselors() }, [fetchCounselors])

  const handleAction = async (id, action) => {
    try {
      await counselorAction(id, action)
      fetchCounselors()
    } catch {
      toast?.error(t('common.operationFailed'))
    }
  }

  const statusBadge = (s) => {
    const map = {
      pending: 'bg-amber-500/20 text-amber-400',
      approved: 'bg-green-500/20 text-green-400',
      rejected: 'bg-red-500/20 text-red-400',
    }
    const labels = {
      pending: t('admin.filterPending'),
      approved: t('admin.filterApproved'),
      rejected: t('admin.filterRejected'),
    }
    return <span className={`px-2 py-0.5 rounded-full text-xs ${map[s]}`}>{labels[s]}</span>
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 rounded-lg text-sm cursor-pointer transition-colors ${
              filter === f.value
                ? 'bg-purple-600 text-white'
                : 'glass opacity-70 hover:opacity-100'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="opacity-60">{t('common.loading')}</p>
      ) : counselors.length === 0 ? (
        <p className="text-center py-8 opacity-50">{t('admin.noCounselors')}</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {counselors.map((c) => (
            <div key={c.id} className="glass p-5 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-bold text-lg">{c.username}</span>
                {statusBadge(c.status)}
              </div>
              <p className="text-sm opacity-70">{c.email}</p>
              <div className="text-sm space-y-1">
                <p><span className="opacity-60">{t('admin.licenseNumber')}</span>{c.license_number}</p>
                <p><span className="opacity-60">{t('admin.specialty')}</span>{c.specialty}</p>
                <p><span className="opacity-60">{t('admin.introduction')}</span>{c.introduction}</p>
                <p><span className="opacity-60">{t('admin.appliedDate')}</span>{new Date(c.created_at).toLocaleDateString(LOCALE_MAP[lang] || lang)}</p>
              </div>
              {c.status === 'pending' && (
                <div className="flex gap-2 pt-1">
                  <button
                    onClick={() => handleAction(c.id, 'approve')}
                    className="px-4 py-1.5 rounded-lg text-sm bg-green-500/20 text-green-400 hover:bg-green-500/30 cursor-pointer"
                  >
                    {t('admin.actionApprove')}
                  </button>
                  <button
                    onClick={() => handleAction(c.id, 'reject')}
                    className="px-4 py-1.5 rounded-lg text-sm bg-red-500/20 text-red-400 hover:bg-red-500/30 cursor-pointer"
                  >
                    {t('admin.actionReject')}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/* ==================== Tab 4: Feedback ==================== */

function FeedbackTab() {
  const { t, lang } = useLang()
  const toast = useToast()
  const [feedbacks, setFeedbacks] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getFeedback()
      .then((r) => setFeedbacks(r.data.results ?? r.data))
      .catch(() => toast?.error(t('common.operationFailed')))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <p className="opacity-60">{t('common.loading')}</p>

  if (feedbacks.length === 0) {
    return <p className="text-center py-8 opacity-50">{t('admin.feedbackEmpty')}</p>
  }

  const avg = (feedbacks.reduce((s, f) => s + f.rating, 0) / feedbacks.length).toFixed(1)

  return (
    <div className="space-y-4">
      <div className="flex gap-4 flex-wrap">
        <div className="glass p-5 rounded-xl">
          <p className="text-sm opacity-60 mb-1">{t('admin.feedbackAvg')}</p>
          <p className="text-3xl font-bold bg-gradient-to-r from-amber-500 to-orange-500 bg-clip-text text-transparent">
            {avg} <span className="text-lg">/ 5</span>
          </p>
        </div>
        <div className="glass p-5 rounded-xl">
          <p className="text-sm opacity-60 mb-1">{t('admin.feedbackTotal', { count: feedbacks.length })}</p>
          <p className="text-3xl font-bold bg-gradient-to-r from-purple-500 to-indigo-500 bg-clip-text text-transparent">
            {feedbacks.length}
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {feedbacks.map((f) => (
          <div key={f.id} className="glass p-4 rounded-xl space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-medium">{f.username}</span>
                <span className="text-amber-400">
                  {'★'.repeat(f.rating)}{'☆'.repeat(5 - f.rating)}
                </span>
              </div>
              <span className="text-xs opacity-50">{new Date(f.created_at).toLocaleDateString(LOCALE_MAP[lang] || lang)}</span>
            </div>
            <p className="text-sm opacity-80">{f.content}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
