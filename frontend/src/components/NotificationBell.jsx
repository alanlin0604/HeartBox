import { useEffect, useRef, useState, memo } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'
import { getNotifications, markNotificationsRead } from '../api/notifications'
import {
  getAccessToken,
  getRefreshToken,
  isAccessTokenExpiring,
  setAccessToken,
  setRefreshToken,
} from '../utils/tokenStorage'
import { LOCALE_MAP } from '../utils/locales'

/**
 * Refresh the access token if it's close to expiry, so the WS handshake
 * uses a valid one. Returns the (possibly new) access token, or null if
 * we can't refresh — in which case the caller should not connect.
 */
async function ensureFreshAccessToken() {
  if (!isAccessTokenExpiring(60)) return getAccessToken()
  const refresh = getRefreshToken()
  if (!refresh) return null
  try {
    const apiBase = import.meta.env.VITE_API_URL || '/api'
    const { data } = await axios.post(`${apiBase}/auth/refresh/`, { refresh })
    setAccessToken(data.access)
    if (data.refresh) setRefreshToken(data.refresh)
    return data.access
  } catch {
    return null
  }
}

// Keep this in sync with backend Notification.TYPE_CHOICES (api/models.py).
const NOTIF_TYPE_KEYS = {
  message: 'notification.type.message',
  booking: 'notification.type.booking',
  bookingStatus: 'notification.type.bookingStatus',
  share: 'notification.type.share',
  assessment_share: 'notification.type.assessmentShare',
  system: 'notification.type.system',
  friend_request: 'notification.type.friendRequest',
  friend_accepted: 'notification.type.friendAccepted',
  friend_share: 'notification.type.friendShare',
  friend_comment: 'notification.type.friendComment',
  post_reaction: 'notification.type.postReaction',
  habit_reminder: 'notification.type.habitReminder',
  achievement: 'notification.type.achievement',
}

function getLocalizedMessage(notif, t) {
  const d = notif.data || {}
  if (notif.type === 'booking' && d.action) {
    if (d.action === 'new') {
      return t('notification.booking.new', { username: d.username, date: d.date, time: d.time })
    }
    if (d.action === 'confirmed') {
      return t('notification.booking.confirmed', { counselor: d.counselor_name })
    }
    if (d.action === 'cancelled') {
      return t('notification.booking.cancelled', { counselor: d.counselor_name })
    }
    if (d.action === 'user_cancelled') {
      return t('notification.booking.userCancelled', { username: d.username })
    }
    if (d.action === 'completed') {
      return t('notification.booking.completed', { counselor: d.counselor_name })
    }
  }
  if (notif.type === 'message' && d.sender_name) {
    if (d.message_type === 'quote') {
      return t('notification.quote.from', { name: d.sender_name })
    }
    return t('notification.message.from', { name: d.sender_name })
  }
  if (notif.type === 'share' && d.author_name) {
    return t('notification.share.from', { name: d.author_name })
  }
  if (notif.type === 'assessment_share' && d.username) {
    return t('notification.assessmentShare.from', { name: d.username, type: (d.assessment_type || '').toUpperCase() })
  }
  // Fallback: system notifications that carry assessment data (pre-migration)
  if (d.assessment_id && d.username) {
    return t('notification.assessmentShare.from', { name: d.username, type: (d.assessment_type || '').toUpperCase() })
  }
  if (notif.type === 'achievement') {
    // Backend stores achievement_id in data; message field is the same id as fallback.
    const aid = d.achievement_id || notif.message
    return t(`achievement.${aid}`)
  }
  // Fallback for old notifications without enriched data
  return notif.message
}

export default memo(function NotificationBell() {
  const { t, lang } = useLang()
  const toast = useToast()
  const navigate = useNavigate()
  const [notifications, setNotifications] = useState([])
  const [unreadCount, setUnreadCount] = useState(0)
  const [open, setOpen] = useState(false)
  const wsRef = useRef(null)
  const reconnectTimer = useRef(null)
  const reconnectDelay = useRef(3000)
  const closedIntentionally = useRef(false)
  const panelRef = useRef(null)

  const connectWs = async () => {
    // Refresh the access token first if it's about to / has already expired.
    // Without this, a reconnect after >30 min idle authenticates with an
    // expired JWT, the consumer rejects it, and the channel stays dead until
    // the user reloads.
    const token = await ensureFreshAccessToken()
    if (!token) return

    closedIntentionally.current = false
    const wsBase = import.meta.env.VITE_WS_URL
    const wsUrl = wsBase
      ? `${wsBase}/ws/notifications/`
      : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/notifications/`
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
      // `note_analyzed` is a transient event for any open journal / detail
      // page to refresh in place — NOT a user-facing notification. Skip the
      // bell entirely and broadcast via a window CustomEvent so the listener
      // pattern is decoupled (no need for a global store).
      if (data.type === 'note_analyzed') {
        try {
          window.dispatchEvent(new CustomEvent('heartbox:note_analyzed', { detail: data.data }))
        } catch { /* IE/legacy fallback unused */ }
        return
      }
      setNotifications((prev) => [data, ...prev])
      setUnreadCount((c) => c + 1)
      // Surface achievement unlocks as a toast so the user sees them
      // immediately, anywhere in the app — not only on the bell.
      if (data.type === 'achievement') {
        const aid = data.data?.achievement_id || data.message
        toast?.success(`${t('achievement.newUnlock')} ${t(`achievement.${aid}`)}`)
      }
    }

    ws.onclose = () => {
      if (!closedIntentionally.current) {
        if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
        reconnectTimer.current = setTimeout(connectWs, reconnectDelay.current)
        reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000)
      }
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
      console.warn('Failed to load notifications:', err)
    }
  }

  // Load initial notifications. Mount-only by design — connectWs handles its
  // own reconnect loop via setTimeout, so re-running this on every render
  // would double-subscribe.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    loadNotifications()
    connectWs()

    return () => {
      closedIntentionally.current = true
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

    // Navigate based on type — counselor-related deep links removed
    // pre-launch (no counselor UI). Booking/share/assessment notifications
    // will still appear in the bell but won't deep-link anywhere.
    if (notif.type === 'message' && notif.data?.conversation_id) {
      navigate(`/chat/${notif.data.conversation_id}`)
    } else if (notif.type === 'note' && notif.data?.note_id) {
      navigate(`/notes/${notif.data.note_id}`)
    } else if (notif.type === 'achievement') {
      navigate('/achievements')
    } else if (notif.type === 'friend_request' || notif.type === 'friend_accepted') {
      navigate('/friends')
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
        aria-label={unreadCount > 0 ? t('aria.notificationsUnread', { count: unreadCount }) : t('aria.notifications')}
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
        <div className="absolute right-0 top-8 w-80 max-w-[calc(100vw-2rem)] max-h-96 overflow-y-auto rounded-xl shadow-xl z-50 border border-[var(--card-border)] bg-[var(--popup-bg)]">
          <div className="p-3 border-b border-[var(--card-border)] flex justify-between items-center">
            <span className="font-semibold text-sm">{t('notification.title')}</span>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs text-orange-500 hover:text-orange-400 cursor-pointer"
              >
                {t('notification.markAllRead')}
              </button>
            )}
          </div>

          {notifications.length === 0 ? (
            <div className="p-6 text-center space-y-2">
              <p className="text-2xl">🔔</p>
              <p className="text-sm font-medium opacity-70">{t('notification.empty')}</p>
              <p className="text-xs text-[var(--text-secondary)]">{t('notification.emptyDesc')}</p>
            </div>
          ) : (
            notifications.slice(0, 20).map((notif) => (
              <div
                key={notif.id}
                onClick={() => handleClickItem(notif)}
                className={`p-3 cursor-pointer hover:bg-orange-500/10 transition-colors border-b border-[var(--card-border)] ${
                  !notif.is_read ? 'bg-orange-500/10' : ''
                }`}
              >
                <div className="flex items-start gap-2">
                  {!notif.is_read && (
                    <span className="w-2 h-2 rounded-full bg-orange-500 mt-1.5 shrink-0" />
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{NOTIF_TYPE_KEYS[notif.type] ? t(NOTIF_TYPE_KEYS[notif.type]) : notif.data?.assessment_id ? t('notification.type.assessmentShare') : notif.title}</p>
                    <p className="text-xs text-[var(--text-secondary)] truncate">{getLocalizedMessage(notif, t)}</p>
                    <p className="text-xs text-[var(--text-secondary)] mt-1">
                      {new Date(notif.created_at).toLocaleString(LOCALE_MAP[lang] || lang)}
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
