import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  getStats,
  getUsers,
  updateUser,
  getCounselors,
  counselorAction,
  getFeedback,
  getCommunityReports,
  moderateCommunityPost,
  getAuditLogs,
  getMLStatus,
} from '../api/admin'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'
import { LOCALE_MAP } from '../utils/locales'
import ConfirmModal from '../components/ConfirmModal'

export default function AdminPage() {
  const { t } = useLang()
  const [tab, setTab] = useState(0)

  useEffect(() => { document.title = `${t('admin.title')} — ${t('app.name')}` }, [t])

  // Counselors admin tab hidden pre-launch — the array slot is kept so tab
  // indices below do not shift; the button itself is skipped while hidden=true.
  const TABS = [
    { label: t('admin.tabOverview') },
    { label: t('admin.tabUsers') },
    { label: t('admin.tabCounselors'), hidden: true },
    { label: t('admin.tabFeedback') },
    { label: t('admin.tabReports') },
    { label: t('admin.tabAuditLog') },
    { label: t('admin.tabMLStatus') },
  ]

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold">{t('admin.title')}</h2>
      <div className="flex gap-2 flex-wrap">
        {TABS.map((entry, i) => entry.hidden ? null : (
          <button
            key={entry.label}
            onClick={() => setTab(i)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors cursor-pointer ${
              tab === i
                ? 'bg-orange-600 text-white'
                : 'glass opacity-70 hover:opacity-100'
            }`}
          >
            {entry.label}
          </button>
        ))}
      </div>

      {tab === 0 && <StatsTab />}
      {tab === 1 && <UsersTab />}
      {/* tab === 2 (CounselorsTab) hidden pre-launch */}
      {tab === 3 && <FeedbackTab />}
      {tab === 4 && <ReportsTab />}
      {tab === 5 && <AuditLogTab />}
      {tab === 6 && <MLStatusTab />}
    </div>
  )
}

/* ==================== Tab 7: ML Status ==================== */

function MLStatusTab() {
  const { t } = useLang()
  const toast = useToast()
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMLStatus()
      .then((r) => setStatus(r.data))
      .catch(() => toast?.error(t('common.operationFailed')))
      .finally(() => setLoading(false))
  }, [toast, t])

  if (loading) return <p className="opacity-60">{t('common.loading')}</p>
  if (!status) return null

  return (
    <div className="space-y-4">
      <p className="text-sm text-[var(--text-secondary)]">{t('admin.ml.headerHint')}</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <MLModelCard label={t('admin.ml.moodPrediction')} info={status.mood_prediction} t={t} />
        <MLModelCard label={t('admin.ml.stressSpike')} info={status.stress_spike} t={t} />
      </div>
      <details className="glass-card p-4 rounded-xl">
        <summary className="text-sm cursor-pointer text-[var(--text-secondary)]">
          {t('admin.ml.howToRetrain')}
        </summary>
        <pre className="text-xs font-mono text-[var(--text-tertiary)] mt-3 overflow-x-auto whitespace-pre-wrap">
{`# Export data from prod DB
python manage.py export_ml_training_data --task=mood_prediction --days=180
python manage.py export_ml_training_data --task=stress_spike   --days=180

# Train models
python -m ml.scripts.train_mood_prediction --input ml/datasets/mood_prediction_<date>.csv --output ml/models/mood_prediction_v2.joblib
python -m ml.scripts.train_stress_spike   --input ml/datasets/stress_spike_<date>.csv   --output ml/models/stress_spike_v2.joblib

# Predictor auto-picks the highest-versioned joblib on next process start.`}
        </pre>
      </details>
    </div>
  )
}

/* ==================== Tab 6: Audit Log ==================== */

function AuditLogTab() {
  const { t, lang } = useLang()
  const toast = useToast()
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionFilter, setActionFilter] = useState('')
  const [userFilter, setUserFilter] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    const params = {}
    if (actionFilter) params.action = actionFilter
    if (userFilter) params.user = userFilter
    getAuditLogs(params)
      .then((r) => setLogs(r.data.results || []))
      .catch(() => toast?.error(t('common.operationFailed')))
      .finally(() => setLoading(false))
  }, [actionFilter, userFilter, toast, t])

  useEffect(() => {
    const timer = setTimeout(load, 300)
    return () => clearTimeout(timer)
  }, [load])

  const ACTION_GROUPS = [
    { value: '', label: t('admin.audit.allActions') },
    { value: 'admin.', label: t('admin.audit.adminActions') },
    { value: 'auth.', label: t('admin.audit.authActions') },
    { value: 'note', label: t('admin.audit.noteActions') },
    { value: 'password', label: t('admin.audit.passwordActions') },
  ]

  // Color-code by action namespace for quick scanning
  const actionBadge = (action) => {
    let cls = 'bg-gray-500/20 text-[var(--text-secondary)]'
    if (action.startsWith('admin.')) cls = 'bg-red-500/20 text-red-500'
    else if (action.startsWith('auth.')) cls = 'bg-orange-500/20 text-[var(--text-accent)]'
    else if (action.includes('password')) cls = 'bg-amber-500/20 text-amber-500'
    else if (action.includes('account_delete')) cls = 'bg-red-500/20 text-red-500'
    else if (action.startsWith('note')) cls = 'bg-blue-500/20 text-blue-500'
    return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>{action}</span>
  }

  return (
    <div className="space-y-4">
      <div className="flex gap-2 flex-wrap">
        {ACTION_GROUPS.map((g) => (
          <button
            key={g.value || 'all'}
            onClick={() => setActionFilter(g.value)}
            className={`px-3 py-1.5 rounded-full text-sm transition-colors duration-100 ${
              actionFilter === g.value
                ? 'bg-orange-500/20 text-[var(--text-accent)] border border-orange-500/50'
                : 'border border-[var(--border-primary)] text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)]'
            }`}
          >
            {g.label}
          </button>
        ))}
        <input
          type="text"
          placeholder={t('admin.audit.userPlaceholder')}
          value={userFilter}
          onChange={(e) => setUserFilter(e.target.value)}
          className="glass-input px-3 py-1.5 rounded-full text-sm w-48"
        />
      </div>

      {loading ? (
        <p className="opacity-60">{t('common.loading')}</p>
      ) : logs.length === 0 ? (
        <p className="text-center py-8 opacity-50">{t('admin.audit.empty')}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border-primary)] text-left text-[var(--text-secondary)]">
                <th className="pb-2 pr-4">{t('admin.audit.when')}</th>
                <th className="pb-2 pr-4">{t('admin.audit.who')}</th>
                <th className="pb-2 pr-4">{t('admin.audit.action')}</th>
                <th className="pb-2 pr-4">{t('admin.audit.target')}</th>
                <th className="pb-2 pr-4">{t('admin.audit.ip')}</th>
                <th className="pb-2">{t('admin.audit.details')}</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((l) => (
                <tr key={l.id} className="border-b border-white/5 hover:bg-white/5 align-top">
                  <td className="py-2 pr-4 text-[var(--text-tertiary)] whitespace-nowrap">
                    {new Date(l.created_at).toLocaleString(LOCALE_MAP[lang] || lang)}
                  </td>
                  <td className="py-2 pr-4 font-medium">{l.user || '—'}</td>
                  <td className="py-2 pr-4">{actionBadge(l.action)}</td>
                  <td className="py-2 pr-4 text-[var(--text-secondary)]">
                    {l.target_type ? `${l.target_type}#${l.target_id ?? '?'}` : '—'}
                  </td>
                  <td className="py-2 pr-4 text-[var(--text-tertiary)] font-mono text-xs">{l.ip_address || '—'}</td>
                  <td className="py-2 text-xs text-[var(--text-secondary)]">
                    {l.details && Object.keys(l.details).length > 0 ? (
                      <code className="text-[var(--text-tertiary)]">{JSON.stringify(l.details)}</code>
                    ) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="text-xs text-[var(--text-tertiary)] mt-3">
            {t('admin.audit.showingCount', { count: logs.length })}
          </p>
        </div>
      )}
    </div>
  )
}

/* ==================== Tab 5: Community Reports ==================== */

function ReportsTab() {
  const { t } = useLang()
  const toast = useToast()
  const [reports, setReports] = useState([])
  const [statusFilter, setStatusFilter] = useState('open')
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState(null)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const res = await getCommunityReports(statusFilter)
      setReports(res.data || [])
    } catch {
      toast?.error(t('common.operationFailed'))
    } finally {
      setLoading(false)
    }
  }, [statusFilter, toast, t])

  useEffect(() => { load() }, [load])

  const handleAction = async (postId, action) => {
    try {
      setActing(postId)
      await moderateCommunityPost(postId, action)
      toast?.success(t('admin.reports.actionDone'))
      load()
    } catch {
      toast?.error(t('common.operationFailed'))
    } finally {
      setActing(null)
    }
  }

  const STATUS_OPTIONS = [
    { value: 'open', label: t('admin.reports.statusOpen') },
    { value: 'reviewed_removed', label: t('admin.reports.statusRemoved') },
    { value: 'reviewed_kept', label: t('admin.reports.statusKept') },
    { value: 'dismissed', label: t('admin.reports.statusDismissed') },
  ]

  return (
    <div className="space-y-4">
      <div className="flex gap-2 flex-wrap">
        {STATUS_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setStatusFilter(opt.value)}
            className={`px-3 py-1.5 rounded-full text-sm transition-colors duration-100 ${
              statusFilter === opt.value
                ? 'bg-orange-500/20 text-[var(--text-accent)] border border-orange-500/50'
                : 'border border-[var(--border-primary)] text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)]'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm opacity-70">{t('common.loading')}</p>
      ) : reports.length === 0 ? (
        <p className="text-sm opacity-70">{t('admin.reports.empty')}</p>
      ) : (
        <div className="space-y-3">
          {reports.map((r) => (
            <div key={r.id} className="glass-card p-4 rounded-xl">
              <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
                <div className="flex items-center gap-2 text-sm">
                  <span className="px-2 py-0.5 rounded-full bg-red-500/15 text-red-500 font-medium">
                    {t(`community.reportReason.${r.reason}`, { defaultValue: r.reason })}
                  </span>
                  <span className="text-[var(--text-tertiary)]">·</span>
                  <span className="text-[var(--text-secondary)]">
                    {t('admin.reports.reporter')}: {r.reporter}
                  </span>
                  <span className="text-[var(--text-tertiary)]">·</span>
                  <span className="text-[var(--text-tertiary)]">
                    {new Date(r.created_at).toLocaleString()}
                  </span>
                </div>
                <span className="text-xs px-2 py-0.5 rounded-full bg-orange-500/10 text-[var(--text-accent)]">
                  {r.post.open_report_count} {t('admin.reports.openCount')}
                </span>
              </div>
              {r.note && (
                <p className="text-sm text-[var(--text-secondary)] mb-3 italic">
                  &ldquo;{r.note}&rdquo;
                </p>
              )}
              <div className="border-t border-[var(--border-primary)] pt-3 mb-3">
                <p className="text-xs text-[var(--text-tertiary)] mb-1">
                  {t('admin.reports.postBy')} <strong>{r.post.author}</strong>
                  {!r.post.is_active && (
                    <span className="ml-2 px-2 py-0.5 rounded-full bg-gray-500/15 text-[var(--text-tertiary)]">
                      {t('admin.reports.autoHidden')}
                    </span>
                  )}
                </p>
                <p className="text-sm text-[var(--text-primary)] whitespace-pre-wrap">{r.post.content}</p>
              </div>
              {r.status === 'open' && (
                <div className="flex gap-2 flex-wrap">
                  <button
                    onClick={() => handleAction(r.post.id, 'remove')}
                    disabled={acting === r.post.id}
                    className="px-3 py-1.5 rounded-lg bg-red-500/20 text-red-500 hover:bg-red-500/30 transition-colors disabled:opacity-50 text-sm"
                  >
                    {t('admin.reports.remove')}
                  </button>
                  <button
                    onClick={() => handleAction(r.post.id, 'keep')}
                    disabled={acting === r.post.id}
                    className="px-3 py-1.5 rounded-lg bg-green-500/20 text-green-600 hover:bg-green-500/30 transition-colors disabled:opacity-50 text-sm"
                  >
                    {t('admin.reports.keep')}
                  </button>
                  <button
                    onClick={() => handleAction(r.post.id, 'dismiss')}
                    disabled={acting === r.post.id}
                    className="px-3 py-1.5 rounded-lg border border-[var(--border-primary)] text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)] transition-colors disabled:opacity-50 text-sm"
                  >
                    {t('admin.reports.dismiss')}
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

/* ==================== Tab 1: Stats ==================== */

function StatCard({ label, value, hint, accent }) {
  return (
    <div className="glass-card p-5 rounded-xl">
      <p className="text-sm text-[var(--text-secondary)] mb-1">{label}</p>
      <p className={`text-3xl font-bold ${accent || 'text-[var(--text-primary)]'}`}>{value}</p>
      {hint && <p className="text-xs text-[var(--text-tertiary)] mt-1">{hint}</p>}
    </div>
  )
}

function MLModelCard({ label, info, t }) {
  if (!info?.loaded) {
    return (
      <div className="glass-card p-5 rounded-xl">
        <p className="text-sm text-[var(--text-secondary)] mb-1">{label}</p>
        <p className="text-lg font-medium text-red-500">{t('admin.ml.notLoaded')}</p>
        <p className="text-xs text-[var(--text-tertiary)] mt-2">{t('admin.ml.notLoadedHint')}</p>
      </div>
    )
  }
  return (
    <div className="glass-card p-5 rounded-xl space-y-2">
      <div className="flex items-center justify-between">
        <p className="text-sm font-semibold">{label}</p>
        <span className="text-xs px-2 py-0.5 rounded-full bg-green-500/15 text-green-600 dark:text-green-400">
          {t('admin.ml.loaded')}
        </span>
      </div>
      <div className="text-xs text-[var(--text-tertiary)] font-mono">{info.version}</div>
      <div className="text-xs text-[var(--text-secondary)]">
        {t('admin.ml.trainedAt')}: {info.trained_at ? new Date(info.trained_at).toLocaleString() : '—'}
      </div>
      <div className="text-xs text-[var(--text-secondary)]">
        {t('admin.ml.trainSize')}: <strong>{info.n_train_rows}</strong> {t('admin.ml.rows')}
      </div>
      {info.cv_metrics && (
        <div className="text-xs text-[var(--text-secondary)] border-t border-[var(--border-primary)] pt-2 space-y-0.5">
          <p className="font-medium text-[var(--text-primary)] mb-1">{t('admin.ml.cvMetrics')}</p>
          {Object.entries(info.cv_metrics).map(([k, v]) => (
            <div key={k} className="flex justify-between font-mono">
              <span>{k}</span>
              <span>{v ?? '—'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function StatsTab() {
  const { t } = useLang()
  const toast = useToast()
  const [stats, setStats] = useState(null)

  useEffect(() => {
    getStats()
      .then((r) => setStats(r.data))
      .catch(() => toast?.error(t('common.operationFailed')))
  }, [toast, t])

  // Build a 30-day series with zero-fill so the chart doesn't have gaps.
  // Hooks must be called unconditionally — pass undefined when stats not loaded.
  const series = useMemo(() => {
    if (!stats?.growth) return []
    const userByDate = new Map((stats.growth.daily_users || []).map((r) => [r.date, r.count]))
    const noteByDate = new Map((stats.growth.daily_notes || []).map((r) => [r.date, r.count]))
    const out = []
    const today = new Date()
    for (let i = 29; i >= 0; i--) {
      const d = new Date(today)
      d.setDate(d.getDate() - i)
      const key = d.toISOString().slice(0, 10)
      out.push({
        date: key,
        users: userByDate.get(key) || 0,
        notes: noteByDate.get(key) || 0,
      })
    }
    return out
  }, [stats])

  if (!stats) return <p className="opacity-60">{t('common.loading')}</p>

  const userPct = stats.total_users
    ? Math.round((stats.verified_users / stats.total_users) * 100)
    : 0
  const activePct = stats.total_users
    ? Math.round((stats.active_users / stats.total_users) * 100)
    : 0

  return (
    <div className="space-y-6">
      {/* Top-level KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          label={t('admin.totalUsers')}
          value={stats.total_users}
          hint={`+${stats.week_new_users || 0} ${t('admin.thisWeek')}`}
          accent="text-[var(--text-accent)]"
        />
        <StatCard
          label={t('admin.totalNotes')}
          value={stats.total_notes}
          hint={`+${stats.week_new_notes || 0} ${t('admin.thisWeek')}`}
          accent="text-rose-600 dark:text-rose-400"
        />
        <StatCard
          label={t('admin.activeUsers')}
          value={stats.active_users}
          hint={`${activePct}% ${t('admin.ofTotal')}`}
          accent="text-green-600 dark:text-green-400"
        />
        <StatCard
          label={t('admin.verifiedUsers')}
          value={stats.verified_users}
          hint={`${userPct}% ${t('admin.ofTotal')}`}
          accent="text-amber-600 dark:text-amber-400"
        />
      </div>

      {/* Action-required + community
          Counselor stat cards hidden pre-launch — re-enable with /counselors. */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard
          label={t('admin.communityPosts')}
          value={stats.total_posts || 0}
        />
        <StatCard
          label={t('admin.openReports')}
          value={stats.open_reports || 0}
          accent={stats.open_reports > 0 ? 'text-red-600 dark:text-red-400' : ''}
        />
      </div>

      {/* Today snapshot */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <StatCard label={t('admin.todayNewUsers')} value={stats.today_new_users} />
        <StatCard label={t('admin.todayNewNotes')} value={stats.today_new_notes} />
      </div>

      {/* 30-day growth sparkline */}
      <div className="glass-card p-5 rounded-xl">
        <h3 className="text-sm font-semibold mb-3 text-[var(--text-secondary)]">
          {t('admin.growth30d')}
        </h3>
        <Sparkline series={series} />
        <div className="flex gap-4 mt-3 text-xs text-[var(--text-tertiary)]">
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-0.5 bg-[var(--text-accent)]" />
            {t('admin.newUsers')}
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-3 h-0.5 bg-rose-500" />
            {t('admin.newNotes')}
          </span>
        </div>
      </div>
    </div>
  )
}

/* Lightweight inline SVG sparkline — avoids pulling in Recharts here. */
function Sparkline({ series }) {
  if (!series || series.length === 0) return null
  const W = 600
  const H = 80
  const maxUsers = Math.max(1, ...series.map((s) => s.users))
  const maxNotes = Math.max(1, ...series.map((s) => s.notes))
  const xStep = W / Math.max(1, series.length - 1)
  const usersPath = series
    .map((s, i) => {
      const x = i * xStep
      const y = H - (s.users / maxUsers) * (H - 10) - 5
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
  const notesPath = series
    .map((s, i) => {
      const x = i * xStep
      const y = H - (s.notes / maxNotes) * (H - 10) - 5
      return `${i === 0 ? 'M' : 'L'}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="w-full h-20" aria-hidden="true">
      <path d={notesPath} fill="none" stroke="#e11d48" strokeWidth="1.5" />
      <path d={usersPath} fill="none" stroke="#fb923c" strokeWidth="1.5" />
    </svg>
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
  const [roleFilter, setRoleFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')

  const fetchUsers = useCallback(() => {
    setLoading(true)
    getUsers(search)
      .then((r) => setUsers(r.data.results ?? r.data))
      .catch(() => toast?.error(t('common.operationFailed')))
      .finally(() => setLoading(false))
  }, [search, toast, t])

  useEffect(() => {
    const timer = setTimeout(fetchUsers, 300)
    return () => clearTimeout(timer)
  }, [fetchUsers])

  // Client-side filter on top of search-backed list. Cheap because the
  // backend already caps the page size and search narrows the result.
  const filteredUsers = useMemo(() => {
    return users.filter((u) => {
      if (statusFilter === 'active' && !u.is_active) return false
      if (statusFilter === 'inactive' && u.is_active) return false
      if (roleFilter === 'staff' && !u.is_staff && !u.is_superuser) return false
      if (roleFilter === 'counselor' && !u.is_counselor) return false
      if (roleFilter === 'user' && (u.is_staff || u.is_superuser || u.is_counselor)) return false
      return true
    })
  }, [users, statusFilter, roleFilter])

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
    if (u.is_staff) return <span className="px-2 py-0.5 rounded-full text-xs bg-orange-500/20 text-orange-400">{t('admin.roleAdmin')}</span>
    if (u.is_counselor) return <span className="px-2 py-0.5 rounded-full text-xs bg-emerald-500/20 text-emerald-400">{t('admin.roleCounselor')}</span>
    return <span className="px-2 py-0.5 rounded-full text-xs bg-gray-500/20 opacity-60">{t('admin.roleUser')}</span>
  }

  const ROLE_OPTIONS = [
    { value: 'all', label: t('admin.filterAll') },
    { value: 'user', label: t('admin.roleUser') },
    { value: 'counselor', label: t('admin.roleCounselor') },
    { value: 'staff', label: t('admin.roleAdmin') },
  ]
  const STATUS_OPTIONS = [
    { value: 'all', label: t('admin.filterAll') },
    { value: 'active', label: t('admin.statusActive') },
    { value: 'inactive', label: t('admin.statusInactive') },
  ]

  return (
    <div className="space-y-4">
      <div className="flex gap-3 flex-wrap items-center">
        <input
          type="text"
          placeholder={t('admin.searchPlaceholder')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="glass-input w-full md:w-80 px-4 py-2 rounded-lg outline-none focus:ring-2 focus:ring-orange-500"
        />
        <div className="flex gap-1">
          {ROLE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setRoleFilter(opt.value)}
              className={`px-3 py-1.5 rounded-full text-xs transition-colors duration-100 ${
                roleFilter === opt.value
                  ? 'bg-orange-500/20 text-[var(--text-accent)] border border-orange-500/50'
                  : 'border border-[var(--border-primary)] text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)]'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              onClick={() => setStatusFilter(opt.value)}
              className={`px-3 py-1.5 rounded-full text-xs transition-colors duration-100 ${
                statusFilter === opt.value
                  ? 'bg-orange-500/20 text-[var(--text-accent)] border border-orange-500/50'
                  : 'border border-[var(--border-primary)] text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)]'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <span className="text-xs text-[var(--text-tertiary)] ml-auto">
          {t('admin.audit.showingCount', { count: filteredUsers.length })}
        </span>
      </div>

      {loading ? (
        <p className="opacity-60">{t('common.loading')}</p>
      ) : (
        <>
        {/* Desktop table */}
        <div className="hidden md:block overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border-primary)] text-left text-[var(--text-secondary)]">
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
              {filteredUsers.map((u) => (
                <tr key={u.id} className="border-b border-white/5 hover:bg-white/5">
                  <td className="py-2 pr-4">{u.id}</td>
                  <td className="py-2 pr-4 font-medium">{u.username}</td>
                  <td className="py-2 pr-4 text-slate-400">{u.email}</td>
                  <td className="py-2 pr-4">{roleBadge(u)}</td>
                  <td className="py-2 pr-4">
                    <span className={`px-2 py-0.5 rounded-full text-xs ${u.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                      {u.is_active ? t('admin.statusActive') : t('admin.statusInactive')}
                    </span>
                  </td>
                  <td className="py-2 pr-4 text-slate-400">{new Date(u.date_joined).toLocaleDateString(LOCALE_MAP[lang] || lang)}</td>
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
                          className={`px-2 py-1 rounded text-xs cursor-pointer ${u.is_staff ? 'bg-gray-500/20 opacity-70 hover:bg-gray-500/30' : 'bg-orange-500/20 text-orange-400 hover:bg-orange-500/30'}`}
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
          {filteredUsers.length === 0 && <p className="text-center py-8 opacity-50">{t('admin.noUsers')}</p>}
        </div>

        {/* Mobile cards */}
        <div className="md:hidden space-y-3">
          {filteredUsers.map((u) => (
            <div key={u.id} className="glass-card p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-medium">{u.username}</span>
                {roleBadge(u)}
              </div>
              <p className="text-xs text-slate-400">{u.email}</p>
              <div className="flex items-center gap-2 text-xs">
                <span className={`px-2 py-0.5 rounded-full ${u.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                  {u.is_active ? t('admin.statusActive') : t('admin.statusInactive')}
                </span>
                <span className="text-slate-400">{new Date(u.date_joined).toLocaleDateString(LOCALE_MAP[lang] || lang)}</span>
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
                    className={`px-2 py-1 rounded text-xs cursor-pointer ${u.is_staff ? 'bg-gray-500/20 opacity-70' : 'bg-orange-500/20 text-orange-400'}`}
                  >
                    {u.is_staff ? t('admin.actionRemoveAdmin') : t('admin.actionMakeAdmin')}
                  </button>
                </div>
              )}
            </div>
          ))}
          {filteredUsers.length === 0 && <p className="text-center py-8 opacity-50">{t('admin.noUsers')}</p>}
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
                ? 'bg-orange-600 text-white'
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
              <p className="text-sm text-slate-400">{c.email}</p>
              <div className="text-sm space-y-1">
                <p><span className="text-slate-400">{t('admin.licenseNumber')}</span>{c.license_number}</p>
                <p><span className="text-slate-400">{t('admin.specialty')}</span>{c.specialty}</p>
                <p><span className="text-slate-400">{t('admin.introduction')}</span>{c.introduction}</p>
                <p><span className="text-slate-400">{t('admin.appliedDate')}</span>{new Date(c.created_at).toLocaleDateString(LOCALE_MAP[lang] || lang)}</p>
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
  const [ratingFilter, setRatingFilter] = useState(0)  // 0 = all

  useEffect(() => {
    getFeedback()
      .then((r) => setFeedbacks(r.data.results ?? r.data))
      .catch(() => toast?.error(t('common.operationFailed')))
      .finally(() => setLoading(false))
  }, [toast, t])

  if (loading) return <p className="opacity-60">{t('common.loading')}</p>

  if (feedbacks.length === 0) {
    return <p className="text-center py-8 opacity-50">{t('admin.feedbackEmpty')}</p>
  }

  const avg = (feedbacks.reduce((s, f) => s + f.rating, 0) / feedbacks.length).toFixed(1)
  const filtered = ratingFilter === 0 ? feedbacks : feedbacks.filter((f) => f.rating === ratingFilter)
  // Per-rating breakdown for histogram
  const byRating = [5, 4, 3, 2, 1].map((r) => ({
    rating: r,
    count: feedbacks.filter((f) => f.rating === r).length,
    pct: feedbacks.length ? Math.round((feedbacks.filter((f) => f.rating === r).length / feedbacks.length) * 100) : 0,
  }))

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="glass-card p-5 rounded-xl">
          <p className="text-sm text-[var(--text-secondary)] mb-1">{t('admin.feedbackAvg')}</p>
          <p className="text-3xl font-bold text-amber-600 dark:text-amber-400">
            {avg} <span className="text-lg text-[var(--text-tertiary)]">/ 5</span>
          </p>
        </div>
        <div className="glass-card p-5 rounded-xl">
          <p className="text-sm text-[var(--text-secondary)] mb-1">{t('admin.feedbackTotal', { count: feedbacks.length })}</p>
          <p className="text-3xl font-bold text-[var(--text-accent)]">{feedbacks.length}</p>
        </div>
        <div className="glass-card p-5 rounded-xl col-span-1 md:col-span-1">
          <p className="text-sm text-[var(--text-secondary)] mb-2">{t('admin.feedbackBreakdown')}</p>
          <div className="space-y-1">
            {byRating.map((b) => (
              <div key={b.rating} className="flex items-center gap-2 text-xs">
                <span className="w-8 text-[var(--text-tertiary)]">{b.rating}★</span>
                <div className="flex-1 h-1.5 bg-[var(--surface-secondary)] rounded-full overflow-hidden">
                  <div
                    className="h-full bg-amber-500/70 transition-all"
                    style={{ width: `${b.pct}%` }}
                  />
                </div>
                <span className="w-8 text-right text-[var(--text-tertiary)]">{b.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Rating filter pills */}
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={() => setRatingFilter(0)}
          className={`px-3 py-1.5 rounded-full text-xs transition-colors duration-100 ${
            ratingFilter === 0
              ? 'bg-orange-500/20 text-[var(--text-accent)] border border-orange-500/50'
              : 'border border-[var(--border-primary)] text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)]'
          }`}
        >
          {t('admin.filterAll')} ({feedbacks.length})
        </button>
        {[5, 4, 3, 2, 1].map((r) => (
          <button
            key={r}
            onClick={() => setRatingFilter(r)}
            className={`px-3 py-1.5 rounded-full text-xs transition-colors duration-100 ${
              ratingFilter === r
                ? 'bg-orange-500/20 text-[var(--text-accent)] border border-orange-500/50'
                : 'border border-[var(--border-primary)] text-[var(--text-secondary)] hover:bg-[var(--surface-secondary)]'
            }`}
          >
            {r}★ ({byRating.find((b) => b.rating === r)?.count || 0})
          </button>
        ))}
      </div>

      <div className="space-y-3">
        {filtered.length === 0 ? (
          <p className="text-center py-8 opacity-50">{t('admin.feedbackEmpty')}</p>
        ) : filtered.map((f) => (
          <div key={f.id} className="glass-card p-4 rounded-xl space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-medium">{f.username}</span>
                <span className="text-amber-500">
                  {'★'.repeat(f.rating)}<span className="opacity-30">{'★'.repeat(5 - f.rating)}</span>
                </span>
              </div>
              <span className="text-xs text-[var(--text-tertiary)]">
                {new Date(f.created_at).toLocaleDateString(LOCALE_MAP[lang] || lang)}
              </span>
            </div>
            <p className="text-sm text-[var(--text-primary)] whitespace-pre-wrap">{f.content}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
