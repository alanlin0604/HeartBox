import { useState, useEffect, useRef } from 'react'
import { getPosts, createPost, toggleReaction, reportPost } from '../api/community'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'
import { Card, Button, Modal } from '../components/ui'
import SkeletonCard from '../components/SkeletonCard'

const REPORT_REASONS = [
  { value: 'spam', icon: '🗑️' },
  { value: 'harassment', icon: '⚠️' },
  { value: 'hate', icon: '🚫' },
  { value: 'self_harm', icon: '🆘' },
  { value: 'sexual', icon: '🔞' },
  { value: 'violence', icon: '💢' },
  { value: 'misinfo', icon: '❓' },
  { value: 'other', icon: '📝' },
]

export default function CommunityPage() {
  const { t } = useLang()
  const toast = useToast()
  const [posts, setPosts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newPostContent, setNewPostContent] = useState('')
  const [creating, setCreating] = useState(false)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(true)
  const fetchIdRef = useRef(0)
  // Report dialog state
  const [reportingPost, setReportingPost] = useState(null)
  const [reportReason, setReportReason] = useState('spam')
  const [reportNote, setReportNote] = useState('')
  const [reportSubmitting, setReportSubmitting] = useState(false)

  useEffect(() => {
    document.title = `${t('community.title')} — ${t('app.name')}`
  }, [t])

  const fetchPosts = async (pageNum = 1, append = false) => {
    const fetchId = ++fetchIdRef.current
    if (!append) setLoading(true)

    try {
      const res = await getPosts(pageNum, 20)
      if (fetchId === fetchIdRef.current) {
        const newPosts = res.data.results || res.data
        if (append) {
          setPosts(prev => [...prev, ...newPosts])
        } else {
          setPosts(newPosts)
        }
        setHasMore(!!res.data.next)
        setPage(pageNum)
      }
    } catch (err) {
      if (fetchId === fetchIdRef.current) {
        console.error('Failed to load posts:', err)
        toast?.error(t('community.loadFailed'))
      }
    } finally {
      if (fetchId === fetchIdRef.current) {
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    fetchPosts()
  }, [])

  const handleCreatePost = async () => {
    if (!newPostContent.trim() || newPostContent.length < 10) {
      toast?.error(t('community.contentTooShort'))
      return
    }

    setCreating(true)
    try {
      await createPost(newPostContent.trim())
      toast?.success(t('community.postCreated'))
      setNewPostContent('')
      setShowCreateModal(false)
      // Refresh posts
      fetchPosts(1, false)
    } catch (err) {
      // Surface the moderation reject reason if backend sent a `code`
      const code = err.response?.data?.code
      const codeMap = {
        'community.content_blocked': t('community.contentBlocked') || 'Your post was blocked by the content filter.',
        'community.content_too_short': t('community.contentTooShort'),
        'community.content_too_long': t('community.contentTooLong') || 'Post is too long.',
        'community.content_empty': t('community.contentTooShort'),
      }
      toast?.error(codeMap[code] || t('common.operationFailed'))
    } finally {
      setCreating(false)
    }
  }

  const openReportDialog = (post) => {
    setReportingPost(post)
    setReportReason('spam')
    setReportNote('')
  }

  const closeReportDialog = () => {
    setReportingPost(null)
    setReportNote('')
  }

  const handleSubmitReport = async () => {
    if (!reportingPost) return
    setReportSubmitting(true)
    try {
      const res = await reportPost(reportingPost.id, reportReason, reportNote.trim())
      toast?.success(t('community.reportSubmitted') || 'Report submitted. Thanks for keeping the community safe.')
      // If the post got auto-hidden by the threshold, drop it from the visible list.
      if (res.data?.auto_hidden) {
        setPosts(prev => prev.filter(p => p.id !== reportingPost.id))
      }
      closeReportDialog()
    } catch (err) {
      const code = err.response?.data?.code
      const codeMap = {
        'community.cannot_report_own': t('community.cannotReportOwn') || 'You cannot report your own post.',
        'community.already_reported': t('community.alreadyReported') || 'You have already reported this post.',
        'community.invalid_reason': t('community.invalidReason') || 'Invalid report reason.',
      }
      toast?.error(codeMap[code] || t('common.operationFailed'))
    } finally {
      setReportSubmitting(false)
    }
  }

  const handleReaction = async (postId, reactionType) => {
    try {
      const res = await toggleReaction(postId, reactionType)
      // Update post in list
      setPosts(prev => prev.map(p =>
        p.id === postId ? res.data.post : p
      ))
    } catch (err) {
      console.error('Failed to toggle reaction:', err)
      toast?.error(t('common.operationFailed'))
    }
  }

  const loadMore = () => {
    if (!loading && hasMore) {
      fetchPosts(page + 1, true)
    }
  }

  if (loading && posts.length === 0) {
    return (
      <div className="space-y-6 mt-4">
        <SkeletonCard lines={2} />
        {[1, 2, 3].map(i => (
          <SkeletonCard key={i} lines={4} />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-6 mt-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-rose-600 to-orange-600 bg-clip-text text-transparent">
            {t('community.title')}
          </h1>
          <p className="text-[var(--text-secondary)] mt-2">
            {t('community.subtitle')}
          </p>
        </div>
        <Button
          onClick={() => setShowCreateModal(true)}
          className="bg-gradient-to-r from-rose-500 to-orange-500 text-white"
        >
          {t('community.createPost')}
        </Button>
      </div>

      {/* Posts List */}
      {posts.length === 0 ? (
        <Card className="p-12 text-center">
          <div className="text-6xl mb-4">💬</div>
          <h3 className="text-xl font-semibold mb-2">{t('community.noPosts')}</h3>
          <p className="text-[var(--text-secondary)] mb-6">
            {t('community.beFirst')}
          </p>
          <Button onClick={() => setShowCreateModal(true)}>
            {t('community.createPost')}
          </Button>
        </Card>
      ) : (
        <div className="space-y-4">
          {posts.map(post => (
            <Card key={post.id} className="p-6 hover:shadow-lg transition-shadow">
              {/* Post Content */}
              <div className="mb-4">
                <p className="text-[var(--text-primary)] whitespace-pre-wrap">
                  {post.content}
                </p>
              </div>

              {/* Category Badge */}
              {post.category && (
                <div className="mb-4">
                  <span className="inline-block px-3 py-1 text-xs font-medium rounded-full bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400">
                    {post.category}
                  </span>
                </div>
              )}

              {/* Reactions */}
              <div className="flex items-center gap-3 pt-4 border-t border-[var(--border-primary)]">
                {['hug', 'support', 'heart'].map(type => {
                  const count = post.reaction_counts?.[type] || 0
                  const hasReacted = post.user_reacted?.includes(type)
                  const emoji = { hug: '🤗', support: '💪', heart: '❤️' }[type]

                  return (
                    <button
                      key={type}
                      onClick={() => handleReaction(post.id, type)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-full transition-all ${
                        hasReacted
                          ? 'bg-gradient-to-r from-rose-500 to-orange-500 text-white shadow-md'
                          : 'bg-[var(--surface-secondary)] text-[var(--text-secondary)] hover:bg-[var(--surface-elevated)]'
                      }`}
                    >
                      <span className="text-xl">{emoji}</span>
                      {count > 0 && (
                        <span className="text-sm font-medium">{count}</span>
                      )}
                    </button>
                  )
                })}
              </div>

              {/* Timestamp + report */}
              <div className="mt-3 flex items-center justify-between text-xs text-[var(--text-tertiary)]">
                <span>{new Date(post.created_at).toLocaleString()}</span>
                <button
                  onClick={() => openReportDialog(post)}
                  className="text-[var(--text-tertiary)] hover:text-red-500 transition-colors flex items-center gap-1"
                  title={t('community.report') || 'Report this post'}
                  aria-label={t('community.report') || 'Report'}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/>
                    <line x1="4" y1="22" x2="4" y2="15"/>
                  </svg>
                  <span className="hidden sm:inline">{t('community.report') || 'Report'}</span>
                </button>
              </div>
            </Card>
          ))}

          {/* Load More */}
          {hasMore && (
            <div className="text-center pt-4">
              <Button
                variant="outline"
                onClick={loadMore}
                disabled={loading}
              >
                {loading ? t('common.loading') : t('community.loadMore')}
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Create Post Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title={t('community.createPost')}
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              {t('community.postContent')}
            </label>
            <textarea
              value={newPostContent}
              onChange={(e) => setNewPostContent(e.target.value)}
              placeholder={t('community.postPlaceholder')}
              className="glass-input w-full px-4 py-3 rounded-lg resize-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              rows={6}
              maxLength={5000}
            />
            <div className="text-right text-xs text-[var(--text-tertiary)] mt-1">
              {newPostContent.length} / 5000
            </div>
          </div>

          <div className="flex gap-3 justify-end">
            <Button
              variant="outline"
              onClick={() => setShowCreateModal(false)}
              disabled={creating}
            >
              {t('common.cancel')}
            </Button>
            <Button
              onClick={handleCreatePost}
              disabled={creating || newPostContent.trim().length < 10}
              className="bg-gradient-to-r from-rose-500 to-orange-500 text-white"
            >
              {creating ? t('common.saving') : t('community.publish')}
            </Button>
          </div>
        </div>
      </Modal>

      {/* Report Post Modal */}
      <Modal
        isOpen={!!reportingPost}
        onClose={closeReportDialog}
        title={t('community.reportPost') || 'Report this post'}
      >
        <div className="space-y-4">
          <p className="text-sm text-[var(--text-secondary)]">
            {t('community.reportIntro') || 'Tell us what’s wrong with this post. We review every report.'}
          </p>
          <div>
            <label className="block text-sm font-medium mb-2">
              {t('community.reportReason') || 'Reason'}
            </label>
            <div className="grid grid-cols-2 gap-2">
              {REPORT_REASONS.map(({ value, icon }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setReportReason(value)}
                  className={`flex items-center gap-2 p-3 rounded-lg border text-sm transition ${
                    reportReason === value
                      ? 'border-rose-500 bg-rose-500/10 text-rose-600 dark:text-rose-400'
                      : 'border-[var(--border-primary)] hover:bg-[var(--surface-secondary)]'
                  }`}
                >
                  <span className="text-lg">{icon}</span>
                  <span>{t(`community.reportReason.${value}`) || value}</span>
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">
              {t('community.reportNote') || 'Additional context (optional)'}
            </label>
            <textarea
              value={reportNote}
              onChange={(e) => setReportNote(e.target.value.slice(0, 500))}
              placeholder={t('community.reportNotePlaceholder') || 'Any details a reviewer should know...'}
              className="glass-input w-full px-4 py-3 rounded-lg resize-none focus:ring-2 focus:ring-orange-500 focus:border-transparent"
              rows={3}
              maxLength={500}
            />
            <div className="text-right text-xs text-[var(--text-tertiary)] mt-1">
              {reportNote.length} / 500
            </div>
          </div>
          <div className="flex gap-3 justify-end">
            <Button variant="outline" onClick={closeReportDialog} disabled={reportSubmitting}>
              {t('common.cancel')}
            </Button>
            <Button
              onClick={handleSubmitReport}
              disabled={reportSubmitting}
              className="bg-rose-600 text-white hover:bg-rose-700"
            >
              {reportSubmitting ? t('common.saving') : (t('community.submitReport') || 'Submit report')}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
