import { useState, useEffect, useRef } from 'react'
import { getPosts, createPost, toggleReaction, getMyPosts } from '../api/community'
import { useTheme } from '../context/ThemeContext'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'
import { Card, Button, Modal } from '../components/ui'
import SkeletonCard from '../components/SkeletonCard'

export default function CommunityPage() {
  const { theme } = useTheme()
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
        toast?.error(t('common.operationFailed'))
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
      console.error('Failed to create post:', err)
      toast?.error(t('common.operationFailed'))
    } finally {
      setCreating(false)
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
          <p className="text-gray-600 dark:text-gray-400 mt-2">
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
          <p className="text-gray-600 dark:text-gray-400 mb-6">
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
                <p className="text-gray-800 dark:text-gray-200 whitespace-pre-wrap">
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
              <div className="flex items-center gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
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
                          : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'
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

              {/* Timestamp */}
              <div className="mt-3 text-xs text-gray-500 dark:text-gray-400">
                {new Date(post.created_at).toLocaleString()}
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
              className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-orange-500 focus:border-transparent resize-none"
              rows={6}
              maxLength={5000}
            />
            <div className="text-right text-xs text-gray-500 dark:text-gray-400 mt-1">
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
    </div>
  )
}
