import { useState, useCallback, useEffect, useRef } from 'react'
import { useLang } from '../../context/LanguageContext'
import { useToast } from '../../context/ToastContext'
import { searchUsers, sendFriendRequest } from '../../api/friends'
import { debounce } from '../../utils/debounce'

export default function FriendSearch({ onClose, onRequestSent }) {
  const { t } = useLang()
  const toast = useToast()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [loading, setLoading] = useState(false)
  const [sendingTo, setSendingTo] = useState(null)
  const [message, setMessage] = useState('')
  const [showMessageFor, setShowMessageFor] = useState(null)
  // Race-condition guard: bumped on every search; only the latest fetch
  // commits to state. Without this, fast typing can let a slow first
  // request land after the latest one.
  const fetchIdRef = useRef(0)

  const performSearch = async (searchQuery) => {
    if (!searchQuery.trim()) {
      setResults([])
      return
    }

    const fetchId = ++fetchIdRef.current
    try {
      setLoading(true)
      const res = await searchUsers(searchQuery)
      if (fetchId !== fetchIdRef.current) return
      setResults(res.data.users || [])
    } catch (error) {
      if (fetchId !== fetchIdRef.current) return
      console.error('Search failed:', error)
      toast?.error(t('friends.search.failed'))
    } finally {
      if (fetchId === fetchIdRef.current) setLoading(false)
    }
  }

  const debouncedSearch = useCallback(
    debounce((q) => performSearch(q), 500),
    []
  )

  useEffect(() => {
    debouncedSearch(query)
  }, [query])

  const handleSendRequest = async (userId) => {
    try {
      setSendingTo(userId)
      await sendFriendRequest(userId, message)
      setResults(results.map(u =>
        u.id === userId ? { ...u, has_pending_request: true } : u
      ))
      setShowMessageFor(null)
      setMessage('')
      toast?.success(t('friends.requestSent'))
      if (onRequestSent) onRequestSent()
    } catch (error) {
      console.error('Failed to send request:', error)
      const errorMsg = error.response?.data?.error || t('friends.sendRequestFailed')
      toast?.error(errorMsg)
    } finally {
      setSendingTo(null)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="popup-panel w-full max-w-lg max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between mb-4 pb-4 border-b border-[var(--card-border)]">
          <h2 className="text-xl font-semibold">{t('friends.search')}</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-300 transition-colors"
          >
            <CloseIcon />
          </button>
        </div>

        {/* Search Input */}
        <div className="mb-4">
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={t('friends.search.placeholder')}
              className="input-field w-full pl-10"
              autoFocus
            />
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">
              <SearchIcon />
            </div>
          </div>
        </div>

        {/* Results */}
        <div className="flex-1 overflow-y-auto space-y-3">
          {loading && (
            <div className="text-center py-8 text-slate-400">
              {t('common.loading')}
            </div>
          )}

          {!loading && query && results.length === 0 && (
            <div className="text-center py-8 text-slate-400">
              {t('friends.search.noResults')}
            </div>
          )}

          {!loading && !query && (
            <div className="text-center py-8 text-slate-400">
              {t('friends.search.hint')}
            </div>
          )}

          {results.map((user) => (
            <div key={user.id} className="glass p-4 rounded-xl">
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-3">
                  {user.avatar ? (
                    <img
                      src={user.avatar}
                      alt={user.username}
                      className="w-12 h-12 rounded-full object-cover border border-white/20"
                    />
                  ) : (
                    <div className="w-12 h-12 rounded-full bg-blue-500/25 flex items-center justify-center text-blue-400 font-semibold text-lg">
                      {user.username.slice(0, 1).toUpperCase()}
                    </div>
                  )}
                  <div>
                    <h3 className="font-semibold">{user.username}</h3>
                    {user.bio && (
                      <p className="text-xs text-slate-400 mt-0.5">{user.bio}</p>
                    )}
                  </div>
                </div>

                {/* Action Button */}
                <div>
                  {user.is_friend ? (
                    <span className="text-xs text-green-400 bg-green-500/10 px-3 py-1.5 rounded-full">
                      {t('friends.alreadyFriends')}
                    </span>
                  ) : user.has_pending_request ? (
                    <span className="text-xs text-blue-400 bg-blue-500/10 px-3 py-1.5 rounded-full">
                      {t('friends.requestPending')}
                    </span>
                  ) : (
                    <button
                      onClick={() => setShowMessageFor(user.id)}
                      disabled={sendingTo === user.id}
                      className="text-xs btn-primary text-white px-3 py-1.5"
                    >
                      {sendingTo === user.id ? t('common.sending') : t('friends.sendRequest')}
                    </button>
                  )}
                </div>
              </div>

              {/* Message Input (shown when user clicks send request) */}
              {showMessageFor === user.id && (
                <div className="mt-3 pt-3 border-t border-[var(--card-border)] space-y-2">
                  <textarea
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder={t('friends.search.sendMessage')}
                    className="input-field w-full resize-none"
                    rows="2"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleSendRequest(user.id)}
                      className="btn-primary flex-1"
                    >
                      {t('friends.send')}
                    </button>
                    <button
                      onClick={() => {
                        setShowMessageFor(null)
                        setMessage('')
                      }}
                      className="btn-secondary"
                    >
                      {t('common.cancel')}
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function SearchIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8"/>
      <path d="m21 21-4.35-4.35"/>
    </svg>
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
