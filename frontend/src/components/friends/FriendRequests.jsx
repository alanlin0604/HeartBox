import { useState, useEffect } from 'react'
import { useLang } from '../../context/LanguageContext'
import { useToast } from '../../context/ToastContext'
import {
  getReceivedRequests,
  getSentRequests,
  acceptFriendRequest,
  rejectFriendRequest,
  cancelFriendRequest,
} from '../../api/friends'
import LoadingSpinner from '../LoadingSpinner'
import { timeAgo } from '../../utils/dateUtils'

export default function FriendRequests({ onClose, onUpdate }) {
  const { t } = useLang()
  const toast = useToast()
  const [activeTab, setActiveTab] = useState('received')
  const [loading, setLoading] = useState(true)
  const [receivedRequests, setReceivedRequests] = useState([])
  const [sentRequests, setSentRequests] = useState([])
  const [processing, setProcessing] = useState(null)

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        const [received, sent] = await Promise.all([
          getReceivedRequests(),
          getSentRequests(),
        ])
        if (cancelled) return
        setReceivedRequests(received.data.results || [])
        setSentRequests(sent.data.results || [])
      } catch (error) {
        if (cancelled) return
        console.error('Failed to load requests:', error)
        toast?.error(t('friends.requests.loadFailed'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [toast, t])

  const handleAccept = async (id) => {
    try {
      setProcessing(id)
      await acceptFriendRequest(id)
      toast?.success(t('friends.requests.accepted'))
      setReceivedRequests(receivedRequests.filter(r => r.id !== id))
      if (onUpdate) onUpdate()
    } catch (error) {
      console.error('Failed to accept request:', error)
      toast?.error(t('friends.requests.acceptFailed'))
    } finally {
      setProcessing(null)
    }
  }

  const handleReject = async (id) => {
    try {
      setProcessing(id)
      await rejectFriendRequest(id)
      toast?.success(t('friends.requests.rejected'))
      setReceivedRequests(receivedRequests.filter(r => r.id !== id))
    } catch (error) {
      console.error('Failed to reject request:', error)
      toast?.error(t('friends.requests.rejectFailed'))
    } finally {
      setProcessing(null)
    }
  }

  const handleCancel = async (id) => {
    try {
      setProcessing(id)
      await cancelFriendRequest(id)
      toast?.success(t('friends.requests.cancelled'))
      setSentRequests(prev => prev.filter(r => r.id !== id))
    } catch (error) {
      console.error('Failed to cancel request:', error)
      toast?.error(t('friends.requests.cancelFailed'))
    } finally {
      setProcessing(null)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="popup-panel w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between mb-4 pb-4 border-b border-[var(--card-border)]">
          <h2 className="text-xl font-semibold truncate pr-2">{t('friends.requests')}</h2>
          <button
            onClick={onClose}
            className="shrink-0 p-2 -m-2 rounded-lg text-[var(--text-secondary)] hover:bg-white/5 transition-colors"
            aria-label={t('common.close')}
          >
            <CloseIcon />
          </button>
        </div>

        {/* Tabs — flex-1 with min-w-0 + truncate so long CJK labels + count
            badges don't get clipped on narrow viewports. Brand orange to
            match the rest of the app. */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setActiveTab('received')}
            className={`
              flex-1 min-w-0 px-3 py-3 rounded-lg font-medium text-sm transition-all truncate
              ${activeTab === 'received'
                ? 'bg-orange-500/20 text-orange-400'
                : 'text-[var(--text-secondary)] hover:bg-white/5'
              }
            `}
          >
            {t('friends.requests.received')} ({receivedRequests.length})
          </button>
          <button
            onClick={() => setActiveTab('sent')}
            className={`
              flex-1 min-w-0 px-3 py-3 rounded-lg font-medium text-sm transition-all truncate
              ${activeTab === 'sent'
                ? 'bg-orange-500/20 text-orange-400'
                : 'text-[var(--text-secondary)] hover:bg-white/5'
              }
            `}
          >
            {t('friends.requests.sent')} ({sentRequests.length})
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto space-y-3">
          {loading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner />
            </div>
          ) : activeTab === 'received' ? (
            receivedRequests.length === 0 ? (
              <div className="text-center py-8 text-slate-400">
                {t('friends.requests.noReceived')}
              </div>
            ) : (
              receivedRequests.map((request) => (
                <div key={request.id} className="glass p-4 rounded-xl">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      {request.from_user_avatar ? (
                        <img
                          src={request.from_user_avatar}
                          alt={request.from_user_username}
                          className="w-12 h-12 rounded-full object-cover border border-white/20"
                        />
                      ) : (
                        <div className="w-12 h-12 rounded-full bg-orange-500/25 flex items-center justify-center text-[var(--text-accent)] font-semibold text-lg">
                          {request.from_user_username.slice(0, 1).toUpperCase()}
                        </div>
                      )}
                      <div>
                        <h3 className="font-semibold">{request.from_user_username}</h3>
                        <p className="text-xs text-slate-400">
                          {timeAgo(request.created_at, t)}
                        </p>
                      </div>
                    </div>
                  </div>

                  {request.message && (
                    <p className="text-sm text-slate-300 mb-3 bg-white/5 p-3 rounded-lg">
                      {request.message}
                    </p>
                  )}

                  <div className="flex gap-2">
                    <button
                      onClick={() => handleAccept(request.id)}
                      disabled={processing === request.id}
                      className="btn-primary flex-1 text-sm"
                    >
                      {processing === request.id ? t('common.loading') : t('friends.acceptRequest')}
                    </button>
                    <button
                      onClick={() => handleReject(request.id)}
                      disabled={processing === request.id}
                      className="btn-secondary text-sm"
                    >
                      {t('friends.rejectRequest')}
                    </button>
                  </div>
                </div>
              ))
            )
          ) : (
            sentRequests.length === 0 ? (
              <div className="text-center py-8 text-slate-400">
                {t('friends.requests.noSent')}
              </div>
            ) : (
              sentRequests.map((request) => (
                <div key={request.id} className="glass p-4 rounded-xl">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      {request.to_user_avatar ? (
                        <img
                          src={request.to_user_avatar}
                          alt={request.to_user_username}
                          className="w-12 h-12 rounded-full object-cover border border-white/20 flex-shrink-0"
                        />
                      ) : (
                        <div className="w-12 h-12 rounded-full bg-orange-500/25 flex items-center justify-center text-[var(--text-accent)] font-semibold text-lg flex-shrink-0">
                          {request.to_user_username.slice(0, 1).toUpperCase()}
                        </div>
                      )}
                      <div className="min-w-0">
                        <h3 className="font-semibold truncate">{request.to_user_username}</h3>
                        <p className="text-xs text-[var(--text-tertiary)]">
                          {timeAgo(request.created_at, t)}
                        </p>
                      </div>
                    </div>
                    <div className="flex-shrink-0 flex flex-col items-end gap-2">
                      <span
                        className={`text-xs px-3 py-1 rounded-full ${
                          request.status === 'pending'
                            ? 'bg-orange-500/10 text-[var(--text-accent)]'
                            : request.status === 'accepted'
                            ? 'bg-green-500/10 text-green-500'
                            : 'bg-red-500/10 text-red-500'
                        }`}
                      >
                        {t(`friends.requests.status.${request.status}`)}
                      </span>
                      {request.status === 'pending' && (
                        <button
                          onClick={() => handleCancel(request.id)}
                          disabled={processing === request.id}
                          className="text-xs text-red-500 hover:text-red-400 transition-colors disabled:opacity-50"
                        >
                          {processing === request.id ? t('common.loading') : t('friends.requests.cancel')}
                        </button>
                      )}
                    </div>
                  </div>
                  {request.message && (
                    <p className="text-sm text-[var(--text-secondary)] mt-3 ml-[60px]">
                      {request.message}
                    </p>
                  )}
                </div>
              ))
            )
          )}
        </div>
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
