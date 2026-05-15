import { useState, useEffect } from 'react'
import { useLang } from '../../context/LanguageContext'
import { useToast } from '../../context/ToastContext'
import { getFriends, shareNoteWithFriends, getSharedByMe } from '../../api/friends'
import LoadingSpinner from '../LoadingSpinner'

export default function ShareNoteToFriends({ noteId, onClose, onShared }) {
  const { t } = useLang()
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [friends, setFriends] = useState([])
  const [selectedFriends, setSelectedFriends] = useState([])
  const [sharing, setSharing] = useState(false)
  const [alreadySharedWith, setAlreadySharedWith] = useState([])

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await getFriends()
        if (!cancelled) setFriends(res.data.results || [])
      } catch (error) {
        if (cancelled) return
        console.error('Failed to load friends:', error)
        toast?.error(t('friends.loadFailed'))
      } finally {
        if (!cancelled) setLoading(false)
      }
      try {
        const res = await getSharedByMe()
        if (cancelled) return
        const sharedWithForThisNote = res.data.results
          .filter(share => share.note === noteId)
          .map(share => share.shared_with_id)
        setAlreadySharedWith(sharedWithForThisNote)
      } catch (error) {
        if (!cancelled) console.error('Failed to load shared notes:', error)
      }
    })()
    return () => { cancelled = true }
  }, [noteId, toast, t])

  const toggleFriend = (friendId) => {
    if (selectedFriends.includes(friendId)) {
      setSelectedFriends(selectedFriends.filter(id => id !== friendId))
    } else {
      setSelectedFriends([...selectedFriends, friendId])
    }
  }

  const handleShare = async () => {
    if (selectedFriends.length === 0) {
      toast?.error(t('friends.share.selectAtLeastOne'))
      return
    }

    try {
      setSharing(true)
      await shareNoteWithFriends(noteId, selectedFriends)
      toast?.success(t('friends.share.shareSuccess', { count: selectedFriends.length }))
      if (onShared) onShared()
      onClose()
    } catch (error) {
      console.error('Failed to share note:', error)
      const errorMsg = error.response?.data?.error || t('friends.share.shareFailed')
      toast?.error(errorMsg)
    } finally {
      setSharing(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="popup-panel w-full max-w-md max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between mb-4 pb-4 border-b border-[var(--card-border)]">
          <h2 className="text-xl font-semibold">{t('friends.share.title')}</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-300 transition-colors"
          >
            <CloseIcon />
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex-1 flex items-center justify-center">
            <LoadingSpinner />
          </div>
        ) : friends.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-center">
            <div>
              <p className="text-slate-400 mb-4">{t('friends.share.noFriends')}</p>
              <button onClick={onClose} className="btn-secondary">
                {t('common.close')}
              </button>
            </div>
          </div>
        ) : (
          <>
            <p className="text-sm text-slate-400 mb-4">
              {t('friends.share.selectFriends')}
            </p>

            {/* Friends List */}
            <div className="flex-1 overflow-y-auto space-y-2 mb-4">
              {friends.map((friend) => {
                const isAlreadyShared = alreadySharedWith.includes(friend.user_id)
                const isSelected = selectedFriends.includes(friend.user_id)

                return (
                  <label
                    key={friend.id}
                    className={`
                      flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors
                      ${isAlreadyShared
                        ? 'bg-green-500/10 border border-green-500/30 opacity-60'
                        : isSelected
                        ? 'bg-orange-500/20 border border-orange-500/50'
                        : 'bg-white/5 hover:bg-white/10'
                      }
                    `}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleFriend(friend.user_id)}
                      disabled={isAlreadyShared}
                      className="w-5 h-5 rounded accent-orange-500 disabled:opacity-50"
                    />
                    {friend.avatar ? (
                      <img
                        src={friend.avatar}
                        alt={friend.username}
                        className="w-10 h-10 rounded-full object-cover border border-white/20"
                      />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-orange-500/25 flex items-center justify-center text-orange-400 font-semibold">
                        {friend.username.slice(0, 1).toUpperCase()}
                      </div>
                    )}
                    <div className="flex-1">
                      <h3 className="font-medium text-sm">{friend.username}</h3>
                      {isAlreadyShared && (
                        <p className="text-xs text-green-400 mt-0.5">
                          {t('friends.share.alreadyShared')}
                        </p>
                      )}
                    </div>
                  </label>
                )
              })}
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3">
              <button
                onClick={handleShare}
                disabled={sharing || selectedFriends.length === 0}
                className="btn-primary flex-1 disabled:opacity-50"
              >
                {sharing
                  ? t('common.sharing')
                  : t('friends.share.shareNote', { count: selectedFriends.length })
                }
              </button>
              <button onClick={onClose} className="btn-secondary">
                {t('common.cancel')}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

function CloseIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="18" y1="6" x2="6" y2="18"/>
      <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>
  )
}
