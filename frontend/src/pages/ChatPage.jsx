import { useEffect, useRef, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLang } from '../context/LanguageContext'
import { getMessages, getConversations, sendMessage } from '../api/counselors'
import LoadingSpinner from '../components/LoadingSpinner'

import { LOCALE_MAP, TZ_MAP } from '../utils/locales'

export default function ChatPage() {
  const { id } = useParams()
  const { user } = useAuth()
  const { lang, t } = useLang()
  const navigate = useNavigate()
  const [messages, setMessages] = useState([])
  const [otherUser, setOtherUser] = useState(null)
  const [newMsg, setNewMsg] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [wsConnected, setWsConnected] = useState(false)
  const bottomRef = useRef(null)
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)
  const reconnectDelay = useRef(3000)

  const connectWs = useCallback(() => {
    const token = localStorage.getItem('access_token')
    if (!token) return

    const wsBase = import.meta.env.VITE_WS_URL
    const wsUrl = wsBase
      ? `${wsBase}/ws/chat/${id}/?token=${token}`
      : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/chat/${id}/?token=${token}`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      setWsConnected(true)
      reconnectDelay.current = 3000 // Reset on success
    }

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)
      setMessages((prev) => {
        // Prevent duplicates
        if (prev.some((m) => m.id === data.id)) return prev
        return [...prev, data]
      })
    }

    ws.onclose = () => {
      setWsConnected(false)
      reconnectTimer.current = setTimeout(connectWs, reconnectDelay.current)
      reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000)
    }

    ws.onerror = () => ws.close()

    wsRef.current = ws
  }, [id])

  useEffect(() => {
    loadConversationInfo()
    loadMessages()
    connectWs()

    return () => {
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
      console.error('Failed to load conversation info', err)
    }
  }

  const loadMessages = async () => {
    try {
      const res = await getMessages(id)
      setMessages(res.data)
    } catch (err) {
      console.error('Failed to load messages', err)
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
        .catch(() => alert(t('chat.sendFailed')))
        .finally(() => setSending(false))
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
                <img src={otherUser.avatar} alt={otherUser.username} className="w-7 h-7 rounded-full object-cover border border-white/20" />
              ) : (
                <span className="w-7 h-7 rounded-full bg-purple-500/25 text-xs flex items-center justify-center">
                  {otherUser.username?.slice(0, 1).toUpperCase()}
                </span>
              )}
              {otherUser.username}
            </span>
          ) : t('chat.conversation')}
        </h2>
        <span className={`ml-auto text-xs px-2 py-0.5 rounded-full ${wsConnected ? 'bg-green-500/20 text-green-500' : 'bg-yellow-500/20 text-yellow-500'}`}>
          {wsConnected ? t('chat.connected') : t('chat.reconnecting')}
        </span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-3 px-2 pb-4">
        {messages.length === 0 ? (
          <div className="text-center opacity-40 mt-12">
            {t('chat.empty')}
          </div>
        ) : (
          messages.map((msg) => {
            const isMine = msg.sender === user?.id
            return (
              <div
                key={msg.id}
                className={`flex ${isMine ? 'justify-end' : 'justify-start'}`}
              >
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
                        <img src={msg.sender_avatar} alt={msg.sender_name} className="w-5 h-5 rounded-full object-cover border border-white/20" />
                      ) : null}
                      <p className="text-xs font-semibold opacity-60">{msg.sender_name}</p>
                    </div>
                  )}
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  <p className="text-xs opacity-40 mt-1 text-right">
                    {new Date(msg.created_at).toLocaleTimeString(LOCALE_MAP[lang] || lang, {
                      timeZone: TZ_MAP[lang] || 'Asia/Taipei',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
              </div>
            )
          })
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSend} className="glass p-3 flex gap-3">
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
