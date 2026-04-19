import { useState, useEffect } from 'react'
import { useLang } from '../../context/LanguageContext'
import { useToast } from '../../context/ToastContext'
import { getFriends, removeFriend } from '../../api/friends'
import LoadingSpinner from '../LoadingSpinner'
import EmptyState from '../EmptyState'
import ConfirmModal from '../ConfirmModal'
import FriendSearch from './FriendSearch'
import FriendRequests from './FriendRequests'
import { formatDistanceToNow } from '../../utils/dateUtils'

export default function FriendsList() {
  const { t } = useLang()
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [friends, setFriends] = useState([])
  const [showSearch, setShowSearch] = useState(false)
  const [showRequests, setShowRequests] = useState(false)
  const [removingId, setRemovingId] = useState(null)
  const [confirmRemove, setConfirmRemove] = useState(null)

  const loadFriends = async () => {
    try {
      setLoading(true)
      const res = await getFriends()
      setFriends(res.data.results || [])
    } catch (error) {
      console.error('Failed to load friends:', error)
      toast?.error(t('friends.loadFailed'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadFriends()
  }, [])

  const handleRemoveFriend = async (friendId) => {
    try {
      setRemovingId(friendId)
      await removeFriend(friendId)
      toast?.success(t('friends.unfriendSuccess'))
      setFriends(friends.filter(f => f.id !== friendId))
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
                      <div className="w-10 h-10 rounded-full bg-green-500/25 flex items-center justify-center text-green-400 font-semibold">
                        {friend.username.slice(0, 1).toUpperCase()}
                      </div>
                    )}
                    <h3 className="font-semibold text-lg">{friend.username}</h3>
                  </div>
                  <div className="flex items-center gap-4 text-sm text-slate-400">
                    <span className="flex items-center gap-1">
                      <FireIcon />
                      {friend.streak_days} {t('streak.days')}
                    </span>
                    <span>{friend.total_entries} {t('friends.entries')}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-2">
                    {t('friends.friendsSince')} {formatDistanceToNow(friend.friendship_since)}
                  </p>
                </div>
                <button
                  onClick={() => setConfirmRemove(friend)}
                  disabled={removingId === friend.id}
                  className="text-red-400 hover:text-red-500 text-sm transition-colors disabled:opacity-50"
                >
                  {removingId === friend.id ? t('common.loading') : t('friends.unfriend')}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modals */}
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
          onUpdate={loadFriends}
        />
      )}

      {confirmRemove && (
        <ConfirmModal
          title={t('friends.unfriendConfirm')}
          message={t('friends.unfriendConfirmDesc', { username: confirmRemove.username })}
          confirmText={t('friends.unfriend')}
          cancelText={t('common.cancel')}
          onConfirm={() => handleRemoveFriend(confirmRemove.id)}
          onCancel={() => setConfirmRemove(null)}
          variant="danger"
        />
      )}
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
