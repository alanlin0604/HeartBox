import { useState, useEffect, lazy, Suspense } from 'react'
import { useLang } from '../../context/LanguageContext'
import { useToast } from '../../context/ToastContext'
import { getFriends, removeFriend } from '../../api/friends'
import LoadingSpinner from '../LoadingSpinner'
import EmptyState from '../EmptyState'
import { formatDistanceToNow } from '../../utils/dateUtils'

// Modals are only mounted on user action — keep them out of the FriendsPage
// chunk so the page itself stays small.
const ConfirmModal = lazy(() => import('../ConfirmModal'))
const FriendSearch = lazy(() => import('./FriendSearch'))
const FriendRequests = lazy(() => import('./FriendRequests'))

export default function FriendsList() {
  const { t } = useLang()
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [friends, setFriends] = useState([])
  const [showSearch, setShowSearch] = useState(false)
  const [showRequests, setShowRequests] = useState(false)
  const [removingId, setRemovingId] = useState(null)
  const [confirmRemove, setConfirmRemove] = useState(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        const res = await getFriends()
        if (!cancelled) setFriends(res.data.results || [])
      } catch (error) {
        if (cancelled) return
        console.error('Failed to load friends:', error)
        toast?.error(t('friends.loadFailed'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [toast, t])

  const reloadFriends = async () => {
    try {
      const res = await getFriends()
      setFriends(res.data.results || [])
    } catch {
      // silent — toast already fired on initial load if it failed
    }
  }

  // Critical: `friend.user_id` is the User pk; `friend.id` is the Friendship
  // row pk. The backend's DELETE /friends/{friend_id}/ resolves the URL
  // segment as a User id (`User.objects.get(id=friend_id)`), so passing
  // friend.id removes the wrong account (or 404s when the friendship pk
  // doesn't map to any user). Always send user_id.
  const handleRemoveFriend = async (friend) => {
    try {
      setRemovingId(friend.id)
      await removeFriend(friend.user_id)
      toast?.success(t('friends.unfriendSuccess'))
      setFriends(prev => prev.filter(f => f.id !== friend.id))
      setConfirmRemove(null)
    } catch (error) {
      console.error('Failed to remove friend:', error)
      toast?.error(t('friends.unfriendFailed'))
    } finally {
      setRemovingId(null)
    }
  }

  if (loading) {
    return <LoadingSpinner />
  }

  return (
    <>
      {/* Action Buttons */}
      <div className="flex gap-3 mb-6">
        <button
          onClick={() => setShowSearch(true)}
          className="btn-primary flex items-center gap-2"
        >
          <SearchIcon />
          {t('friends.search')}
        </button>
        <button
          onClick={() => setShowRequests(true)}
          className="btn-secondary flex items-center gap-2"
        >
          <BellIcon />
          {t('friends.requests')}
        </button>
      </div>

      {/* Friends Grid */}
      {friends.length === 0 ? (
        <EmptyState
          title={t('friends.emptyState')}
          description={t('friends.emptyStateDesc')}
          actionText={t('friends.search')}
          onAction={() => setShowSearch(true)}
          icon={UsersIcon}
          variant="calm"
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {friends.map((friend) => (
            <div key={friend.id} className="glass p-4 rounded-xl hover:bg-white/10 transition-colors">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    {friend.avatar ? (
                      <img
                        src={friend.avatar}
                        alt={friend.username}
                        className="w-10 h-10 rounded-full object-cover border border-white/20"
                      />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-orange-500/25 flex items-center justify-center text-[var(--text-accent)] font-semibold">
                        {friend.username.slice(0, 1).toUpperCase()}
                      </div>
                    )}
                    <h3 className="font-semibold text-lg">{friend.username}</h3>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-[var(--text-secondary)]">
                    <span className="flex items-center gap-1">
                      <FireIcon />
                      {friend.streak_days} {t('streak.days')}
                    </span>
                    <span>{friend.total_entries} {t('friends.entries')}</span>
                  </div>
                  <p className="text-xs text-[var(--text-tertiary)] mt-2">
                    {t('friends.friendsSince')} {formatDistanceToNow(friend.friendship_since)}
                  </p>
                </div>
                <button
                  onClick={() => setConfirmRemove(friend)}
                  disabled={removingId === friend.id}
                  aria-label={t('friends.unfriend')}
                  title={t('friends.unfriend')}
                  className="flex-shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-lg text-sm border border-red-500/30 text-red-500 hover:bg-red-500/10 transition-colors disabled:opacity-50 min-h-[36px]"
                >
                  <UnfriendIcon />
                  <span className="hidden sm:inline">
                    {removingId === friend.id ? t('common.loading') : t('friends.unfriend')}
                  </span>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modals (lazy — only loaded when first opened) */}
      <Suspense fallback={null}>
        {showSearch && (
          <FriendSearch
            onClose={() => setShowSearch(false)}
            onRequestSent={() => {
              setShowSearch(false)
              toast?.success(t('friends.requestSent'))
            }}
          />
        )}

        {showRequests && (
          <FriendRequests
            onClose={() => setShowRequests(false)}
            onUpdate={reloadFriends}
          />
        )}

        {confirmRemove && (
          <ConfirmModal
            title={t('friends.unfriendConfirm')}
            message={t('friends.unfriendConfirmDesc', { username: confirmRemove.username })}
            confirmText={t('friends.unfriend')}
            cancelText={t('common.cancel')}
            onConfirm={() => handleRemoveFriend(confirmRemove)}
            onCancel={() => setConfirmRemove(null)}
            variant="danger"
          />
        )}
      </Suspense>
    </>
  )
}

// SVG Icons
function SearchIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8"/>
      <path d="m21 21-4.35-4.35"/>
    </svg>
  )
}

function BellIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
      <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
    </svg>
  )
}

function FireIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" className="text-orange-500">
      <path d="M8.5 18.5c0-1.5.5-3 2-4.5 0 0 .5 1.5 2 1.5s2-1.5 2-1.5c1.5 1.5 2 3 2 4.5a4.5 4.5 0 1 1-9 0z"/>
      <path d="M12 2s-4 4-4 8c0 0-2-1-2-4 0 0-2 4-2 7a8 8 0 0 0 16 0c0-3-2-7-2-7 0 3-2 4-2 4 0-4-4-8-4-8z"/>
    </svg>
  )
}

function UnfriendIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
      <circle cx="8.5" cy="7" r="4"/>
      <line x1="18" y1="8" x2="23" y2="13"/>
      <line x1="23" y1="8" x2="18" y2="13"/>
    </svg>
  )
}

function UsersIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
      <circle cx="9" cy="7" r="4"/>
      <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
      <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
    </svg>
  )
}
