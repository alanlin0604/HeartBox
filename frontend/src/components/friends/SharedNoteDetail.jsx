import { useState, useEffect } from 'react'
import { useLang } from '../../context/LanguageContext'
import { useAuth } from '../../context/AuthContext'
import { useToast } from '../../context/ToastContext'
import { getSharedNoteDetail } from '../../api/friends'
import LoadingSpinner from '../LoadingSpinner'
import CommentSection from './CommentSection'
import MoodBadge from '../MoodBadge'
import { timeAgo } from '../../utils/dateUtils'

export default function SharedNoteDetail({ shareId, onClose, onUpdate }) {
  const { t } = useLang()
  const { user } = useAuth()
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [shareData, setShareData] = useState(null)
  const [refetchCounter, setRefetchCounter] = useState(0)

  // Cancel-on-shareId-change so a slow earlier fetch can't overwrite the
  // newer detail when the user clicks between shared notes. Bumping
  // refetchCounter triggers a fresh load (used by onCommentAdded below).
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getSharedNoteDetail(shareId)
      .then((res) => {
        if (cancelled) return
        setShareData(res.data)
      })
      .catch((error) => {
        if (cancelled) return
        console.error('Failed to load share detail:', error)
        toast?.error(t('friends.share.detailFailed'))
        onClose()
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shareId, refetchCounter])

  if (loading) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
        <LoadingSpinner />
      </div>
    )
  }

  if (!shareData) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 overflow-y-auto">
      <div className="popup-panel w-full max-w-3xl my-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-4 pb-4 border-b border-[var(--card-border)]">
          <div className="flex items-center gap-3">
            {shareData.shared_by_avatar ? (
              <img
                src={shareData.shared_by_avatar}
                alt={shareData.shared_by_username}
                className="w-10 h-10 rounded-full object-cover border border-white/20"
              />
            ) : (
              <div className="w-10 h-10 rounded-full bg-orange-500/25 flex items-center justify-center text-orange-400 font-semibold">
                {shareData.shared_by_username.slice(0, 1).toUpperCase()}
              </div>
            )}
            <div>
              <h2 className="text-lg font-semibold">{shareData.shared_by_username}</h2>
              <p className="text-xs text-slate-400">
                {t('friends.share.sharedAt')} {timeAgo(shareData.shared_at, t)}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-300 transition-colors"
          >
            <CloseIcon />
          </button>
        </div>

        {/* Note Metadata */}
        <div className="flex items-center gap-4 mb-4 text-sm">
          <div className="flex items-center gap-2">
            <CalendarIcon />
            <span className="text-slate-400">
              {new Date(shareData.created_at).toLocaleDateString()}
            </span>
          </div>
          <MoodBadge score={shareData.sentiment_score} />
        </div>

        {/* Tags */}
        {shareData.tags && shareData.tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {shareData.tags.map((tag) => (
              <span
                key={tag.id}
                className="text-xs px-3 py-1 rounded-full border"
                style={{
                  backgroundColor: `${tag.color}15`,
                  borderColor: `${tag.color}40`,
                  color: tag.color,
                }}
              >
                #{tag.name}
              </span>
            ))}
          </div>
        )}

        {/* Note Content */}
        <div className="glass p-6 rounded-xl mb-6">
          <p className="text-sm leading-relaxed whitespace-pre-wrap text-slate-200">
            {shareData.decrypted_content || shareData.content_preview}
          </p>
        </div>

        {/* Comments Section */}
        <CommentSection
          shareId={shareId}
          currentUserId={user.id}
          onCommentAdded={() => {
            setRefetchCounter((n) => n + 1)
            if (onUpdate) onUpdate()
          }}
        />
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

function CalendarIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2"/>
      <line x1="16" y1="2" x2="16" y2="6"/>
      <line x1="8" y1="2" x2="8" y2="6"/>
      <line x1="3" y1="10" x2="21" y2="10"/>
    </svg>
  )
}
