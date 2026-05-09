import { useEffect, useState } from 'react'
import { useLang } from '../../context/LanguageContext'
import { useToast } from '../../context/ToastContext'
import { getLeaderboard } from '../../api/friends'
import LoadingSpinner from '../LoadingSpinner'
import EmptyState from '../EmptyState'

/**
 * Side-by-side streak comparison of the user and their friends. Renders as a
 * ranked list where each row shows current streak as a horizontal bar
 * normalized against the top streak; the user's own row is highlighted.
 *
 * Mounted as the "Leaderboard" tab in FriendsPage.
 */
export default function FriendsLeaderboard() {
  const { t } = useLang()
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [rows, setRows] = useState([])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getLeaderboard()
      .then(res => {
        if (cancelled) return
        setRows(res.data?.leaderboard || [])
      })
      .catch(() => {
        if (!cancelled) toast?.error(t('common.operationFailed'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [t, toast])

  if (loading) return <LoadingSpinner />

  if (rows.length === 0) {
    return (
      <EmptyState
        title={t('friends.leaderboardEmptyTitle') || 'No leaderboard yet'}
        description={t('friends.leaderboardEmptyDesc') || 'Add a friend to start comparing streaks.'}
        icon={TrophyIcon}
        variant="calm"
      />
    )
  }

  // Top streak drives the bar width normalization. Cap the divisor at 1 so a
  // table of zeros doesn't blow up.
  const topStreak = Math.max(rows[0]?.current_streak || 0, 1)

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold flex items-center gap-2">
        <TrophyIcon />
        {t('friends.leaderboardTitle') || 'Streak leaderboard'}
      </h2>
      <p className="text-sm text-slate-400">
        {t('friends.leaderboardDesc') || 'Friendly competition — see who keeps the longest journaling streak.'}
      </p>

      <div className="space-y-2 mt-4">
        {rows.map((row) => {
          const widthPct = Math.max(2, (row.current_streak / topStreak) * 100)
          return (
            <div
              key={row.user_id}
              className={`glass p-4 rounded-xl ${
                row.is_self ? 'ring-1 ring-orange-400/60 bg-orange-500/10' : ''
              }`}
            >
              <div className="flex items-center gap-3 mb-2">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                  row.rank === 1 ? 'bg-yellow-500/30 text-yellow-300' :
                  row.rank === 2 ? 'bg-slate-400/30 text-slate-200' :
                  row.rank === 3 ? 'bg-orange-700/30 text-orange-300' :
                  'bg-white/5 text-slate-400'
                }`}>
                  {row.rank}
                </div>
                {row.avatar ? (
                  <img
                    src={row.avatar}
                    alt={row.username}
                    className="w-10 h-10 rounded-full object-cover border border-white/20"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-orange-500/25 flex items-center justify-center text-orange-400 font-semibold">
                    {row.username.slice(0, 1).toUpperCase()}
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-base flex items-center gap-2">
                    <span className="truncate">{row.username}</span>
                    {row.is_self && (
                      <span className="text-[10px] px-2 py-0.5 rounded bg-orange-500/30 text-orange-300 font-medium">
                        {t('friends.you') || 'You'}
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-slate-400">
                    {row.total_entries} {t('friends.entries')} · {t('streak.best') || 'Best'} {row.longest_streak}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xl font-bold text-orange-400 flex items-center gap-1 justify-end">
                    <FireIcon />
                    {row.current_streak}
                  </div>
                  <div className="text-[10px] text-slate-500 uppercase tracking-wide">
                    {t('streak.days')}
                  </div>
                </div>
              </div>
              <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-orange-500 to-rose-500 transition-all"
                  style={{ width: `${widthPct}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function TrophyIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6"/>
      <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18"/>
      <path d="M4 22h16"/>
      <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22"/>
      <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22"/>
      <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z"/>
    </svg>
  )
}

function FireIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="text-orange-500">
      <path d="M8.5 18.5c0-1.5.5-3 2-4.5 0 0 .5 1.5 2 1.5s2-1.5 2-1.5c1.5 1.5 2 3 2 4.5a4.5 4.5 0 1 1-9 0z"/>
      <path d="M12 2s-4 4-4 8c0 0-2-1-2-4 0 0-2 4-2 7a8 8 0 0 0 16 0c0-3-2-7-2-7 0 3-2 4-2 4 0-4-4-8-4-8z"/>
    </svg>
  )
}
