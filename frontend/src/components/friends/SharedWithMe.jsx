import { useState, useEffect } from 'react'
import { useLang } from '../../context/LanguageContext'
import { useToast } from '../../context/ToastContext'
import { getSharedWithMe } from '../../api/friends'
import LoadingSpinner from '../LoadingSpinner'
import EmptyState from '../EmptyState'
import SharedNoteDetail from './SharedNoteDetail'
import { timeAgo } from '../../utils/dateUtils'

export default function SharedWithMe() {
  const { t } = useLang()
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [shares, setShares] = useState([])
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [selectedShare, setSelectedShare] = useState(null)

  const loadShares = async (pageNum = 1) => {
    try {
      setLoading(true)
      const res = await getSharedWithMe(pageNum)
      setShares(res.data.results || [])
      setHasMore(!!res.data.next)
      setPage(pageNum)
    } catch (error) {
      console.error('Failed to load shared notes:', error)
      toast?.error(t('friends.share.loadFailed'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadShares()
  }, [])

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

  if (loading) {
    return <LoadingSpinner />
  }

  return (
    <>
      {shares.length === 0 ? (
        <EmptyState
          title={t('friends.share.emptyShared')}
          description={t('friends.share.emptySharedDesc')}
          icon={ShareIcon}
          variant="warm"
        />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {shares.map((share) => (
              <div
                key={share.id}
                onClick={() => setSelectedShare(share)}
                className="glass p-4 rounded-xl cursor-pointer hover:bg-white/10 transition-colors"
              >
                {/* Header */}
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center gap-2">
                    {share.shared_by_avatar ? (
                      <img
                        src={share.shared_by_avatar}
                        alt={share.shared_by_username}
                        className="w-8 h-8 rounded-full object-cover border border-white/20"
                      />
                    ) : (
                      <div className="w-8 h-8 rounded-full bg-purple-500/25 flex items-center justify-center text-purple-400 text-xs font-semibold">
                        {share.shared_by_username.slice(0, 1).toUpperCase()}
                      </div>
                    )}
                    <span className="text-sm font-medium">{share.shared_by_username}</span>
                  </div>
                  <span className="text-xs text-slate-400">
                    {timeAgo(share.shared_at, t)}
                  </span>
                </div>

                {/* Mood Bar */}
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

                {/* Content Preview */}
                <p className="text-sm text-slate-300 line-clamp-3 leading-relaxed mb-3">
                  {share.content_preview}
                </p>

                {/* Footer */}
                <div className="flex items-center justify-between text-xs text-slate-400">
                  <div className="flex items-center gap-1">
                    <CommentIcon />
                    <span>{share.comment_count} {t('friends.comment.count')}</span>
                  </div>
                  <div className="text-xs opacity-60">
                    {new Date(share.created_at).toLocaleDateString()}
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
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

      {/* Detail Modal */}
      {selectedShare && (
        <SharedNoteDetail
          shareId={selectedShare.id}
          onClose={() => setSelectedShare(null)}
          onUpdate={loadShares}
        />
      )}
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
