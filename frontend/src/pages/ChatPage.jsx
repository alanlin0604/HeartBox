import { useEffect, useRef, useState, useCallback, memo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLang } from '../context/LanguageContext'
import { getMessages, getConversations, sendMessage, sendQuote, quoteAction, deleteConversation } from '../api/counselors'
import { useToast } from '../context/ToastContext'
import { getAccessToken } from '../utils/tokenStorage'
import LoadingSpinner from '../components/LoadingSpinner'

import { LOCALE_MAP, TZ_MAP } from '../utils/locales'

const MessageItem = memo(function MessageItem({ msg, user, lang, t, onQuoteAction }) {
  const isMine = msg.sender === user?.id
  return (
    <div className={`flex ${isMine ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[70%] p-3 rounded-2xl ${
          isMine
            ? 'bg-purple-500/30 rounded-br-md'
            : 'glass-card rounded-bl-md'
        }`}
      >
        {!isMine && (
          <div className="flex items-center gap-1.5 mb-1">
            {msg.sender_avatar ? (
              <img src={msg.sender_avatar} alt={msg.sender_name} loading="lazy" decoding="async" className="w-5 h-5 rounded-full object-cover border border-white/20" />
            ) : null}
            <p className="text-xs font-semibold opacity-60">{msg.sender_name}</p>
          </div>
        )}
        {msg.message_type === 'quote' ? (
          <QuoteCard
            metadata={msg.metadata}
            t={t}
            isMine={isMine}
            onAction={(action) => onQuoteAction(msg.id, action)}
          />
        ) : (
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
        )}
        <p className="text-xs opacity-40 mt-1 text-right flex items-center justify-end gap-1">
          <span>
            {new Date(msg.created_at).toLocaleTimeString(LOCALE_MAP[lang] || lang, {
              timeZone: TZ_MAP[lang] || 'Asia/Taipei',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
          {isMine && (
            <span title={msg.is_read ? t('chat.read') : t('chat.sent')}>
              {msg.is_read ? '✓✓' : '✓'}
            </span>
          )}
        </p>
      </div>
    </div>
  )
})

function QuoteCard({ metadata, t, isMine, onAction }) {
  const { description, price, currency, status: quoteStatus } = metadata || {}
  const formatted = new Intl.NumberFormat(undefined, {
    style: 'currency',
    currency: currency || 'TWD',
    minimumFractionDigits: 0,
  }).format(price || 0)

  const statusColors = {
    accepted: 'bg-green-500/20 text-green-400',
    rejected: 'bg-red-500/20 text-red-400',
  }

  return (
    <div className="border-2 border-purple-500/50 rounded-xl p-3 space-y-2">
      <div className="flex items-center gap-2">
        <span className="text-xs font-bold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-400">
          {t('chat.quoteLabel')}
        </span>
        {quoteStatus && (
          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${statusColors[quoteStatus] || ''}`}>
            {t(`chat.quote${quoteStatus.charAt(0).toUpperCase() + quoteStatus.slice(1)}`)}
          </span>
        )}
      </div>
      <p className="text-sm">{description}</p>
      <p className="text-lg font-bold text-purple-400">{formatted}</p>
      {!isMine && !quoteStatus && onAction && (
        <div className="flex gap-2 pt-1">
          <button
            onClick={() => onAction('accept')}
            className="px-3 py-1 rounded-lg text-xs font-medium bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-colors cursor-pointer"
          >
            {t('chat.quoteAccept')}
          </button>
          <button
            onClick={() => onAction('reject')}
            className="px-3 py-1 rounded-lg text-xs font-medium bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors cursor-pointer"
          >
            {t('chat.quoteReject')}
          </button>
        </div>
      )}
    </div>
  )
}

export default function ChatPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const { lang, t } = useLang()
  const toast = useToast()
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [otherUser, setOtherUser] = useState(null)
  const [newMsg, setNewMsg] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const [showQuoteForm, setShowQuoteForm] = useState(false)
  const [quoteData, setQuoteData] = useState({ description: '', price: '', currency: 'TWD' })
  const [sendingQuote, setSendingQuote] = useState(false)
  const bottomRef = useRef(null)
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)
  const reconnectDelay = useRef(3000)
  const closedIntentionally = useRef(false)

  const connectWs = useCallback(() => {
    const token = getAccessToken()
    if (!token) return

    closedIntentionally.current = false
    const wsBase = import.meta.env.VITE_WS_URL
    const wsUrl = wsBase
      ? `${wsBase}/ws/chat/${id}/`
      : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/chat/${id}/`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      // Send JWT via first message instead of query string
      ws.send(JSON.stringify({ type: 'auth', token }))
    }

    ws.onmessage = (e) => {
      let data
      try { data = JSON.parse(e.data) } catch { return }
      // Handle auth response
      if (data.type === 'auth_ok') {
        setWsConnected(true)
        reconnectDelay.current = 3000
        return
      }
      // Respond to server heartbeat pings
      if (data.type === 'ping') {
        ws.send(JSON.stringify({ type: 'pong' }))
        return
      }
      if (data.error) {
        return
      }
      setMessages((prev) => {
        // Prevent duplicates
        if (prev.some((m) => m.id === data.id)) return prev
        return [...prev, data]
      })
    }

    ws.onclose = () => {
      setWsConnected(false)
      if (!closedIntentionally.current) {
        reconnectTimer.current = setTimeout(connectWs, reconnectDelay.current)
        reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000)
      }
    }

    ws.onerror = () => ws.close()

    wsRef.current = ws
  }, [id])

  useEffect(() => { document.title = `${t('chat.conversation')} — ${t('app.name')}` }, [t])

  useEffect(() => {
    loadConversationInfo()
    loadMessages()
    connectWs()

    return () => {
      closedIntentionally.current = true
      clearTimeout(reconnectTimer.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [id, connectWs])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'auto' })
  }, [messages])

  const loadConversationInfo = async () => {
    try {
      const res = await getConversations()
      const convList = res.data.results || res.data
      const conv = convList.find((c) => c.id === parseInt(id))
      if (conv) setOtherUser(conv.other_user)
    } catch (err) {
      toast?.error(t('common.operationFailed'))
    }
  }

  const loadMessages = async () => {
    try {
      const res = await getMessages(id)
      setMessages(res.data)
    } catch (err) {
      toast?.error(t('common.operationFailed'))
    } finally {
      setLoading(false)
    }
  }

  const handleSend = (e) => {
    e.preventDefault()
    if (!newMsg.trim() || sending) return

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ message: newMsg }))
      setNewMsg('')
    } else {
      // Fallback to HTTP POST
      setSending(true)
      sendMessage(id, newMsg)
        .then((res) => {
          setMessages((prev) => [...prev, res.data])
          setNewMsg('')
        })
        .catch(() => toast?.error(t('chat.sendFailed')))
        .finally(() => setSending(false))
    }
  }

  const handleSendQuote = async (e) => {
    e.preventDefault()
    if (!quoteData.description.trim() || sendingQuote) return
    setSendingQuote(true)
    try {
      const res = await sendQuote(id, quoteData)
      setMessages((prev) => [...prev, res.data])
      setQuoteData({ description: '', price: '', currency: 'TWD' })
      setShowQuoteForm(false)
      toast?.success(t('chat.quoteSent'))
    } catch {
      toast?.error(t('chat.quoteFailed'))
    } finally {
      setSendingQuote(false)
    }
  }

  const handleQuoteAction = async (msgId, action) => {
    try {
      const res = await quoteAction(id, msgId, action)
      setMessages((prev) => prev.map((m) => m.id === msgId ? { ...m, metadata: res.data.metadata } : m))
      toast?.success(action === 'accept' ? t('chat.quoteAccepted') : t('chat.quoteRejected'))
    } catch {
      toast?.error(t('common.operationFailed'))
    }
  }

  const handleDeleteConversation = async () => {
    if (!window.confirm(t('chat.deleteConfirm'))) return
    try {
      await deleteConversation(id)
      toast?.success(t('chat.deleted'))
      navigate('/counselors?tab=chats')
    } catch {
      toast?.error(t('common.operationFailed'))
    }
  }

  if (loading) return <LoadingSpinner />

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Header */}
      <div className="glass p-4 flex items-center gap-3 mb-4">
        <button
          onClick={() => navigate('/counselors')}
          className="opacity-60 hover:opacity-100 transition-opacity cursor-pointer text-lg"
        >
          &larr; {t('chat.back')}
        </button>
        <h2 className="font-semibold text-lg">
          {otherUser ? (
            <span className="flex items-center gap-2">
              {otherUser.avatar ? (
                <img src={otherUser.avatar} alt={otherUser.display_name || otherUser.username} loading="lazy" decoding="async" className="w-7 h-7 rounded-full object-cover border border-white/20" />
              ) : (
                <span className="w-7 h-7 rounded-full bg-purple-500/25 text-xs flex items-center justify-center">
                  {(otherUser.display_name || otherUser.username)?.slice(0, 1).toUpperCase()}
                </span>
              )}
              {otherUser.display_name || otherUser.username}
            </span>
          ) : t('chat.conversation')}
        </h2>
        <div className="ml-auto flex items-center gap-2">
          <span className={`text-xs px-2 py-0.5 rounded-full ${wsConnected ? 'bg-green-500/20 text-green-500' : 'bg-yellow-500/20 text-yellow-500'}`}>
            {wsConnected ? t('chat.connected') : t('chat.reconnecting')}
          </span>
          <button
            onClick={handleDeleteConversation}
            className="text-xs px-2 py-1 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors cursor-pointer"
            title={t('chat.deleteConversation')}
          >
            {t('chat.deleteConversation')}
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 px-2 pb-4">
        {messages.length === 0 ? (
          <div className="text-center opacity-40 mt-12">
            {t('chat.empty')}
          </div>
        ) : (
          messages.map((msg) => (
            <MessageItem key={msg.id} msg={msg} user={user} lang={lang} t={t} onQuoteAction={handleQuoteAction} />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* Quote Form */}
      {showQuoteForm && (
        <form onSubmit={handleSendQuote} className="glass p-3 space-y-2 border-t border-purple-500/30">
          <div className="flex items-center gap-2 text-sm font-medium text-purple-400">
            <span>{t('chat.quoteLabel')}</span>
          </div>
          <textarea
            value={quoteData.description}
            onChange={(e) => setQuoteData({ ...quoteData, description: e.target.value })}
            placeholder={t('chat.quoteDescPlaceholder')}
            className="glass-input w-full resize-none"
            rows={2}
          />
          <div className="flex gap-2">
            <input
              type="number"
              min="0"
              step="any"
              value={quoteData.price}
              onChange={(e) => setQuoteData({ ...quoteData, price: e.target.value })}
              placeholder={t('chat.quotePrice')}
              className="glass-input"
              style={{ width: 'auto', flex: '1 1 0%' }}
            />
            <select
              value={quoteData.currency}
              onChange={(e) => setQuoteData({ ...quoteData, currency: e.target.value })}
              className="glass-input"
              style={{ width: '10rem', flex: 'none' }}
            >
              <option value="TWD">TWD (NT$)</option>
              <option value="USD">USD ($)</option>
              <option value="JPY">JPY (¥)</option>
            </select>
          </div>
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={() => setShowQuoteForm(false)}
              className="px-3 py-1.5 rounded-lg text-sm glass opacity-70 hover:opacity-100 cursor-pointer"
            >
              {t('chat.quoteCancel')}
            </button>
            <button
              type="submit"
              disabled={sendingQuote || !quoteData.description.trim()}
              className="btn-primary text-sm"
            >
              {sendingQuote ? t('chat.sending') : t('chat.sendQuote')}
            </button>
          </div>
        </form>
      )}

      {/* Input */}
      <form onSubmit={handleSend} className="glass p-3 flex gap-3">
        {user?.is_counselor && (
          <button
            type="button"
            onClick={() => setShowQuoteForm(!showQuoteForm)}
            className={`px-2 py-1 rounded-lg text-lg cursor-pointer transition-colors ${
              showQuoteForm ? 'text-purple-400 bg-purple-500/20' : 'opacity-60 hover:opacity-100'
            }`}
            title={t('chat.sendQuote')}
          >
            $
          </button>
        )}
        <input
          type="text"
          value={newMsg}
          onChange={(e) => setNewMsg(e.target.value)}
          placeholder={t('chat.placeholder')}
          className="glass-input flex-1"
          autoFocus
        />
        <button
          type="submit"
          disabled={sending || !newMsg.trim()}
          className="btn-primary whitespace-nowrap"
        >
          {sending ? t('chat.sending') : t('chat.send')}
        </button>
      </form>
    </div>
  )
}
