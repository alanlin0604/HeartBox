import { useEffect, useRef, useState, memo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'
import { getNotifications, markNotificationsRead } from '../api/notifications'
import { getAccessToken } from '../utils/tokenStorage'
import EmptyState from './EmptyState'

export default memo(function NotificationBell() {
  const { t } = useLang()
  const navigate = useNavigate()
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [open, setOpen] = useState(false)
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)
  const reconnectDelay = useRef(3000)
  const panelRef = useRef(null)

  // Load initial notifications
  useEffect(() => {
    loadNotifications()
    connectWs()

    return () => {
      clearTimeout(reconnectTimer.current)
      if (wsRef.current) wsRef.current.close()
    }
  }, [])

  // Close panel on outside click
  useEffect(() => {
    const handler = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const connectWs = () => {
    const token = getAccessToken()
    if (!token) return

    const wsBase = import.meta.env.VITE_WS_URL
    const wsUrl = wsBase
      ? `${wsBase}/ws/notifications/?token=${token}`
      : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/notifications/?token=${token}`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      reconnectDelay.current = 3000 // Reset on success
    }

    ws.onmessage = (e) => {
      const data = JSON.parse(e.data)
      setNotifications((prev) => [data, ...prev])
      setUnreadCount((c) => c + 1)
    }

    ws.onclose = () => {
      reconnectTimer.current = setTimeout(connectWs, reconnectDelay.current)
      reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000)
    }

    ws.onerror = () => ws.close()
    wsRef.current = ws
  }

  const loadNotifications = async () => {
    try {
      const res = await getNotifications()
      const items = res.data.results || res.data
      setNotifications(items)
      setUnreadCount(items.filter((n) => !n.is_read).length)
    } catch (err) {
      console.error('Failed to load notifications', err)
    }
  }

  const handleOpen = () => {
    setOpen(!open)
  }

  const handleClickItem = async (notif) => {
    // Mark as read
    if (!notif.is_read) {
      await markNotificationsRead([notif.id])
      setNotifications((prev) =>
        prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
      )
      setUnreadCount((c) => Math.max(0, c - 1))
    }

    // Navigate based on type
    if (notif.type === 'message' && notif.data?.conversation_id) {
      navigate(`/chat/${notif.data.conversation_id}`)
    } else if (notif.type === 'booking') {
      navigate('/counselors', { state: { tab: 'bookings' } })
    } else if (notif.type === 'share') {
      navigate('/counselors', { state: { tab: 'received' } })
    } else if (notif.type === 'note' && notif.data?.note_id) {
      navigate(`/notes/${notif.data.note_id}`)
    }

    setOpen(false)
  }

  const handleMarkAllRead = async () => {
    await markNotificationsRead([])
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
    setUnreadCount(0)
  }

  return (
    <div className="relative" ref={panelRef}>
      <button
        onClick={handleOpen}
        className="relative opacity-70 hover:opacity-100 transition-opacity cursor-pointer text-lg"
        title={t('notification.title')}
        aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ''}`}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-1.5 -right-1.5 bg-red-500 text-white text-[10px] font-bold min-w-[16px] h-4 rounded-full flex items-center justify-center px-1">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-8 w-80 max-w-[90vw] max-h-96 overflow-y-auto rounded-xl shadow-xl z-50 border border-[var(--card-border)] bg-[var(--tooltip-bg)]">
          <div className="p-3 border-b border-[var(--card-border)] flex justify-between items-center">
            <span className="font-semibold text-sm">{t('notification.title')}</span>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs text-purple-500 hover:text-purple-400 cursor-pointer"
              >
                {t('notification.markAllRead')}
              </button>
            )}
          </div>

          {notifications.length === 0 ? (
            <div className="p-4">
              <EmptyState
                title={t('notification.empty')}
                description={t('notification.emptyDesc')}
                actionText={t('journal.writeFirst')}
                onAction={() => {
                  navigate('/')
                  setOpen(false)
                }}
              />
            </div>
          ) : (
            notifications.slice(0, 20).map((notif) => (
              <div
                key={notif.id}
                onClick={() => handleClickItem(notif)}
                className={`p-3 cursor-pointer hover:bg-purple-500/10 transition-colors border-b border-[var(--card-border)] ${
                  !notif.is_read ? 'bg-purple-500/10' : ''
                }`}
              >
                <div className="flex items-start gap-2">
                  {!notif.is_read && (
                    <span className="w-2 h-2 rounded-full bg-purple-500 mt-1.5 shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{notif.title}</p>
                    <p className="text-xs opacity-60 truncate">{notif.message}</p>
                    <p className="text-xs opacity-40 mt-1">
                      {new Date(notif.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
})
