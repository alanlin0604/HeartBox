import { useState, useEffect } from 'react'
import { useLang } from '../../context/LanguageContext'
import { useToast } from '../../context/ToastContext'
import { getComments, addComment, deleteComment } from '../../api/friends'
import ConfirmModal from '../ConfirmModal'
import { timeAgo } from '../../utils/dateUtils'

export default function CommentSection({ shareId, currentUserId, onCommentAdded }) {
  const { t } = useLang()
  const toast = useToast()
  const [comments, setComments] = useState([])
  const [loading, setLoading] = useState(true)
  const [newComment, setNewComment] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [deletingId, setDeletingId] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(null)

  const loadComments = async () => {
    try {
      setLoading(true)
      const res = await getComments(shareId)
      setComments(res.data.results || [])
    } catch (error) {
      console.error('Failed to load comments:', error)
      toast?.error(t('friends.comment.loadFailed'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadComments()
  }, [shareId])

  const handleAddComment = async (e) => {
    e.preventDefault()
    if (!newComment.trim()) return

    try {
      setSubmitting(true)
      const res = await addComment(shareId, newComment)
      setComments([...comments, res.data])
      setNewComment('')
      toast?.success(t('friends.comment.addSuccess'))
      if (onCommentAdded) onCommentAdded()
    } catch (error) {
      console.error('Failed to add comment:', error)
      toast?.error(t('friends.comment.addFailed'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleDeleteComment = async (commentId) => {
    try {
      setDeletingId(commentId)
      await deleteComment(commentId)
      setComments(comments.filter(c => c.id !== commentId))
      toast?.success(t('friends.comment.deleteSuccess'))
      setConfirmDelete(null)
      if (onCommentAdded) onCommentAdded()
    } catch (error) {
      console.error('Failed to delete comment:', error)
      toast?.error(t('friends.comment.deleteFailed'))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="space-y-4">
      {/* Comments Header */}
      <div className="flex items-center gap-2 text-sm">
        <CommentIcon />
        <h3 className="font-semibold">
          {t('friends.comment.title')} ({comments.length})
        </h3>
      </div>

      {/* Comments List */}
      <div className="space-y-3">
        {loading ? (
          <div className="text-center py-4 text-slate-400 text-sm">
            {t('common.loading')}
          </div>
        ) : comments.length === 0 ? (
          <div className="text-center py-4 text-slate-400 text-sm">
            {t('friends.comment.empty')}
          </div>
        ) : (
          comments.map((comment) => (
            <div key={comment.id} className="flex gap-3 p-3 bg-white/5 rounded-lg">
              {/* Avatar */}
              {comment.commenter_avatar ? (
                <img
                  src={comment.commenter_avatar}
                  alt={comment.commenter_username}
                  className="w-10 h-10 rounded-full object-cover border border-white/20 flex-shrink-0"
                />
              ) : (
                <div className="w-10 h-10 rounded-full bg-rose-500/25 flex items-center justify-center text-rose-400 text-sm font-semibold flex-shrink-0">
                  {comment.commenter_username.slice(0, 1).toUpperCase()}
                </div>
              )}

              {/* Comment Content */}
              <div className="flex-1 min-w-0">
                <div className="flex justify-between items-start mb-1">
                  <span className="text-sm font-medium">{comment.commenter_username}</span>
                  <span className="text-xs text-slate-400">
                    {timeAgo(comment.created_at, t)}
                  </span>
                </div>
                <p className="text-sm text-slate-300 whitespace-pre-wrap break-words">
                  {comment.content}
                </p>
              </div>

              {/* Delete Button (only for own comments) */}
              {comment.commenter_id === currentUserId && (
                <button
                  onClick={() => setConfirmDelete(comment)}
                  disabled={deletingId === comment.id}
                  className="text-red-400 hover:text-red-500 text-xs transition-colors flex-shrink-0 disabled:opacity-50"
                >
                  {deletingId === comment.id ? '...' : <TrashIcon />}
                </button>
              )}
            </div>
          ))
        )}
      </div>

      {/* Add Comment Form */}
      <form onSubmit={handleAddComment} className="space-y-2">
        <textarea
          value={newComment}
          onChange={(e) => setNewComment(e.target.value)}
          placeholder={t('friends.comment.placeholder')}
          className="input-field w-full resize-none"
          rows="3"
          disabled={submitting}
        />
        <button
          type="submit"
          disabled={submitting || !newComment.trim()}
          className="btn-primary w-full disabled:opacity-50"
        >
          {submitting ? t('common.sending') : t('friends.comment.add')}
        </button>
      </form>

      {/* Delete Confirmation */}
      {confirmDelete && (
        <ConfirmModal
          title={t('friends.comment.deleteConfirm')}
          message={t('friends.comment.deleteConfirmDesc')}
          confirmText={t('friends.comment.delete')}
          cancelText={t('common.cancel')}
          onConfirm={() => handleDeleteComment(confirmDelete.id)}
          onCancel={() => setConfirmDelete(null)}
          variant="danger"
        />
      )}
    </div>
  )
}

function CommentIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6"/>
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
    </svg>
  )
}
