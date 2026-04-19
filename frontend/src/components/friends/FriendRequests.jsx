import { useState, useEffect } from 'react'
import { useLang } from '../../context/LanguageContext'
import { useToast } from '../../context/ToastContext'
import {
  getReceivedRequests,
  getSentRequests,
  acceptFriendRequest,
  rejectFriendRequest,
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

  const loadRequests = async () => {
    try {
      setLoading(true)
      const [received, sent] = await Promise.all([
        getReceivedRequests(),
        getSentRequests(),
      ])
      setReceivedRequests(received.data.results || [])
      setSentRequests(sent.data.results || [])
    } catch (error) {
      console.error('Failed to load requests:', error)
      toast?.error(t('friends.requests.loadFailed'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRequests()
  }, [])

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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="popup-panel w-full max-w-2xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between mb-4 pb-4 border-b border-[var(--card-border)]">
          <h2 className="text-xl font-semibold">{t('friends.requests')}</h2>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-300 transition-colors"
          >
            <CloseIcon />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-2 mb-4">
          <button
            onClick={() => setActiveTab('received')}
            className={`
              flex-1 px-4 py-2 rounded-lg font-medium text-sm transition-all
              ${activeTab === 'received'
                ? 'bg-blue-500/20 text-blue-400'
                : 'text-slate-400 hover:text-slate-300 hover:bg-white/5'
              }
            `}
          >
            {t('friends.requests.received')} ({receivedRequests.length})
          </button>
          <button
            onClick={() => setActiveTab('sent')}
            className={`
              flex-1 px-4 py-2 rounded-lg font-medium text-sm transition-all
              ${activeTab === 'sent'
                ? 'bg-blue-500/20 text-blue-400'
                : 'text-slate-400 hover:text-slate-300 hover:bg-white/5'
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
                        <div className="w-12 h-12 rounded-full bg-blue-500/25 flex items-center justify-center text-blue-400 font-semibold text-lg">
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
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      {request.to_user_avatar ? (
                        <img
                          src={request.to_user_avatar}
                          alt={request.to_user_username}
                          className="w-12 h-12 rounded-full object-cover border border-white/20"
                        />
                      ) : (
                        <div className="w-12 h-12 rounded-full bg-blue-500/25 flex items-center justify-center text-blue-400 font-semibold text-lg">
                          {request.to_user_username.slice(0, 1).toUpperCase()}
                        </div>
                      )}
                      <div>
                        <h3 className="font-semibold">{request.to_user_username}</h3>
                        <p className="text-xs text-slate-400">
                          {timeAgo(request.created_at, t)}
                        </p>
                      </div>
                    </div>
                    <span
                      className={`text-xs px-3 py-1 rounded-full ${
                        request.status === 'pending'
                          ? 'bg-yellow-500/10 text-yellow-400'
                          : request.status === 'accepted'
                          ? 'bg-green-500/10 text-green-400'
                          : 'bg-red-500/10 text-red-400'
                      }`}
                    >
                      {t(`friends.requests.status.${request.status}`)}
                    </span>
                  </div>
                  {request.message && (
                    <p className="text-sm text-slate-400 mt-3 ml-15">
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
