import { useState, useEffect } from 'react'
import { useLang } from '../../context/LanguageContext'
import { useToast } from '../../context/ToastContext'
import { getSharedByMe, revokeShare } from '../../api/friends'
import LoadingSpinner from '../LoadingSpinner'
import EmptyState from '../EmptyState'
import SharedNoteDetail from './SharedNoteDetail'
import ConfirmModal from '../ConfirmModal'
import { timeAgo } from '../../utils/dateUtils'

// "Notes I've shared" tab. Modeled on SharedWithMe but shows the
// RECIPIENT (shared_with_*) instead of the sender, and offers a
// revoke-share action since the owner is the only one who can undo
// a share. Backend endpoint /api/friends/shared-by-me/ + the
// SharedWithFriendSerializer that now exposes shared_with_* fields.

export default function SharedByMe() {
  const { t } = useLang()
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [shares, setShares] = useState([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [selectedShare, setSelectedShare] = useState(null)
  const [revokeTarget, setRevokeTarget] = useState(null)
  const [revoking, setRevoking] = useState(false)

  const loadShares = async (pageNum = 1) => {
    try {
      setLoading(true)
      const res = await getSharedByMe(pageNum)
      // ListAPIView defaults to DRF pagination; tolerate plain array too.
      const rows = res.data?.results || res.data || []
      setShares(rows)
      setHasMore(!!res.data?.next)
      setPage(pageNum)
    } catch (error) {
      console.error('Failed to load shares-by-me:', error)
      toast?.error(t('friends.share.loadFailed'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadShares() }, [])

  const handleRevoke = async () => {
    if (!revokeTarget) return
    try {
      setRevoking(true)
      await revokeShare(revokeTarget.id)
      toast?.success(t('friends.share.revokeSuccess'))
      setRevokeTarget(null)
      loadShares(page)
    } catch (error) {
      console.error('Failed to revoke share:', error)
      toast?.error(t('friends.share.revokeFailed'))
    } finally {
      setRevoking(false)
    }
  }

  const getMoodColor = (score) => {
    if (score >= 0.3) return 'bg-green-500'
    if (score >= -0.3) return 'bg-yellow-500'
    return 'bg-red-500'
  }

  const getMoodLabel = (score) => {
    if (score >= 0.3) return t('mood.positive')
    if (score >= -0.3) return t('mood.neutral')
    return t('mood.negative')
  }

  if (loading) return <LoadingSpinner />

  return (
    <>
      {shares.length === 0 ? (
        <EmptyState
          title={t('friends.share.emptySharedByMe')}
          description={t('friends.share.emptySharedByMeDesc')}
          icon={ShareIcon}
          variant="warm"
        />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {shares.map((share) => (
              <div
                key={share.id}
                className="glass p-4 rounded-xl hover:bg-white/10 transition-colors"
              >
                {/* Header: recipient identity (this is "I shared to whom"). */}
                <div className="flex justify-between items-start mb-3">
                  <button
                    onClick={() => setSelectedShare(share)}
                    className="flex items-center gap-2 text-left cursor-pointer"
                  >
                    {share.shared_with_avatar ? (
                      <img
                        src={share.shared_with_avatar}
                        alt={share.shared_with_username}
                        className="w-8 h-8 rounded-full object-cover border border-white/20"
                      />
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-orange-500/25 flex items-center justify-center text-orange-400 text-xs font-semibold">
                        {(share.shared_with_username || '?').slice(0, 1).toUpperCase()}
                      </div>
                    )}
                    <div>
                      <div className="text-xs text-slate-400">
                        {t('friends.share.sharedTo')}
                      </div>
                      <div className="text-sm font-medium">
                        {share.shared_with_username}
                      </div>
                    </div>
                  </button>
                  <span className="text-xs text-slate-400">
                    {timeAgo(share.shared_at, t)}
                  </span>
                </div>

                {/* Mood bar */}
                <div className="flex items-center gap-2 mb-3">
                  <div className="h-1.5 flex-1 rounded bg-slate-700">
                    <div
                      className={`h-full rounded ${getMoodColor(share.sentiment_score)}`}
                      style={{ width: `${((share.sentiment_score + 1) / 2) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-slate-400">
                    {getMoodLabel(share.sentiment_score)}
                  </span>
                </div>

                {/* Content preview — clickable to open detail */}
                <button
                  onClick={() => setSelectedShare(share)}
                  className="text-sm text-slate-300 line-clamp-3 leading-relaxed mb-3 text-left w-full cursor-pointer"
                >
                  {share.content_preview}
                </button>

                {/* Footer: comment count + revoke */}
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1 text-slate-400">
                    <CommentIcon />
                    <span>{share.comment_count} {t('friends.comment.count')}</span>
                  </div>
                  <button
                    onClick={() => setRevokeTarget(share)}
                    className="text-red-400 hover:text-red-300 transition-colors px-2 py-1 rounded hover:bg-red-500/10 cursor-pointer"
                  >
                    {t('friends.share.revokeShare')}
                  </button>
                </div>
              </div>
            ))}
          </div>

          {(page > 1 || hasMore) && (
            <div className="flex justify-center gap-3 mt-6">
              <button
                onClick={() => loadShares(page - 1)}
                disabled={page === 1}
                className="btn-secondary disabled:opacity-50"
              >
                {t('journal.prevPage')}
              </button>
              <span className="text-sm text-slate-400 flex items-center">
                {t('journal.page', { page, total: '?' })}
              </span>
              <button
                onClick={() => loadShares(page + 1)}
                disabled={!hasMore}
                className="btn-secondary disabled:opacity-50"
              >
                {t('journal.nextPage')}
              </button>
            </div>
          )}
        </>
      )}

      {selectedShare && (
        <SharedNoteDetail
          shareId={selectedShare.id}
          onClose={() => setSelectedShare(null)}
          onUpdate={() => loadShares(page)}
        />
      )}

      <ConfirmModal
        open={!!revokeTarget}
        title={t('friends.share.revokeShare')}
        message={t('friends.share.revokeConfirm')}
        confirmText={t('friends.share.revokeShare')}
        cancelText={t('common.cancel')}
        loading={revoking}
        onConfirm={handleRevoke}
        onCancel={() => setRevokeTarget(null)}
      />
    </>
  )
}

function ShareIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="18" cy="5" r="3"/>
      <circle cx="6" cy="12" r="3"/>
      <circle cx="18" cy="19" r="3"/>
      <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
      <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
    </svg>
  )
}

function CommentIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  )
}
