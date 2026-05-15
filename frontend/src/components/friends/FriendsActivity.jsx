import { useState, useEffect } from 'react'
import { useLang } from '../../context/LanguageContext'
import { useToast } from '../../context/ToastContext'
import { getFriendActivity } from '../../api/friends'
import LoadingSpinner from '../LoadingSpinner'
import EmptyState from '../EmptyState'
import { timeAgo } from '../../utils/dateUtils'

export default function FriendsActivity() {
  const { t } = useLang()
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [activities, setActivities] = useState([])
  const [hours, setHours] = useState(24)

  const loadActivity = async (selectedHours = 24) => {
    try {
      setLoading(true)
      const res = await getFriendActivity(selectedHours)
      setActivities(res.data.activities || [])
      setHours(selectedHours)
    } catch (error) {
      console.error('Failed to load activity:', error)
      toast?.error(t('friends.activity.loadFailed'))
    } finally {
      setLoading(false)
    }
  }

  // Mount-only initial fetch. User-driven changes to `hours` come through
  // the click handler that calls loadActivity(h) directly, so we don't want
  // this effect to re-fire on hours change.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadActivity(hours) }, [])

  const getActivityIcon = (type) => {
    switch (type) {
      case 'new_entry':
        return <NoteIcon />
      case 'streak_update':
        return <FireIcon />
      default:
        return <ActivityIcon />
    }
  }

  const getActivityDescription = (activity) => {
    switch (activity.activity_type) {
      case 'new_entry':
        return t('friends.activity.newEntry', {
          username: activity.friend_username,
          days: activity.streak_days,
        })
      case 'streak_update':
        return t('friends.activity.streakUpdate', {
          username: activity.friend_username,
          days: activity.streak_days,
        })
      default:
        return t('friends.activity.unknown')
    }
  }

  if (loading) {
    return <LoadingSpinner />
  }

  return (
    <>
      {/* Time Filter */}
      <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
        <span className="text-sm text-slate-400 flex-shrink-0">
          {t('friends.activity.timeFilter')}
        </span>
        {[24, 48, 72, 168].map((h) => (
          <button
            key={h}
            onClick={() => loadActivity(h)}
            className={`
              px-4 py-2 rounded-lg text-sm font-medium transition-all flex-shrink-0
              ${hours === h
                ? 'bg-orange-500/20 text-[var(--text-accent)]'
                : 'bg-white/5 text-[var(--text-secondary)] hover:bg-white/10'
              }
            `}
          >
            {h === 24 ? t('friends.activity.last24h') :
             h === 48 ? t('friends.activity.last48h') :
             h === 72 ? t('friends.activity.last3d') :
             t('friends.activity.lastWeek')}
          </button>
        ))}
      </div>

      {/* Activity Timeline */}
      {activities.length === 0 ? (
        <EmptyState
          title={t('friends.activity.emptyActivity')}
          description={t('friends.activity.emptyActivityDesc')}
          icon={ActivityIconLarge}
          variant="warm"
        />
      ) : (
        <div className="space-y-3">
          {activities.map((activity, index) => (
            <div
              key={`${activity.friend_id}-${activity.timestamp}-${index}`}
              className="flex gap-3 items-start glass p-4 rounded-xl hover:bg-white/10 transition-colors"
            >
              {/* Icon */}
              <div className="flex-shrink-0 w-10 h-10 rounded-full bg-orange-500/20 flex items-center justify-center text-[var(--text-accent)]">
                {getActivityIcon(activity.activity_type)}
              </div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <p className="text-sm text-[var(--text-primary)]">
                  <span className="font-medium text-[var(--text-accent)]">
                    {activity.friend_username}
                  </span>
                  {' '}
                  {getActivityDescription(activity)}
                </p>
                <span className="text-xs text-slate-400 mt-1 block">
                  {timeAgo(activity.timestamp, t)}
                </span>
              </div>

              {/* Streak Badge (for new_entry) */}
              {activity.activity_type === 'new_entry' && activity.streak_days > 0 && (
                <div className="flex-shrink-0 flex items-center gap-1 bg-orange-500/20 text-orange-400 px-3 py-1 rounded-full text-xs font-semibold">
                  <FireIconSmall />
                  {activity.streak_days}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  )
}

// SVG Icons
function NoteIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
      <polyline points="14 2 14 8 20 8"/>
    </svg>
  )
}

function FireIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
      <path d="M8.5 18.5c0-1.5.5-3 2-4.5 0 0 .5 1.5 2 1.5s2-1.5 2-1.5c1.5 1.5 2 3 2 4.5a4.5 4.5 0 1 1-9 0z"/>
      <path d="M12 2s-4 4-4 8c0 0-2-1-2-4 0 0-2 4-2 7a8 8 0 0 0 16 0c0-3-2-7-2-7 0 3-2 4-2 4 0-4-4-8-4-8z"/>
    </svg>
  )
}

function FireIconSmall() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
      <path d="M8.5 18.5c0-1.5.5-3 2-4.5 0 0 .5 1.5 2 1.5s2-1.5 2-1.5c1.5 1.5 2 3 2 4.5a4.5 4.5 0 1 1-9 0z"/>
      <path d="M12 2s-4 4-4 8c0 0-2-1-2-4 0 0-2 4-2 7a8 8 0 0 0 16 0c0-3-2-7-2-7 0 3-2 4-2 4 0-4-4-8-4-8z"/>
    </svg>
  )
}

function ActivityIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  )
}

function ActivityIconLarge() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
    </svg>
  )
}
