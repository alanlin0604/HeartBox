import { useEffect, useRef, useState, useCallback } from 'react'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'
import {
  getAIChatSessions,
  createAIChatSession,
  getAIChatSession,
  deleteAIChatSession,
  updateAIChatSession,
  sendAIChatMessage,
} from '../api/aiChat'
import EmptyState from '../components/EmptyState'
import LoadingSpinner from '../components/LoadingSpinner'
import ConfirmModal from '../components/ConfirmModal'
import { LOCALE_MAP, TZ_MAP } from '../utils/locales'

export default function AIChatPage() {
  const { lang, t } = useLang()
  const toast = useToast()

  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [showSidebar, setShowSidebar] = useState(true)
  const bottomRef = useRef(null)

  // Context menu state
  const [contextMenu, setContextMenu] = useState(null) // { x, y, sessionId }
  // Rename modal state
  const [renameModalId, setRenameModalId] = useState(null)
  const [renameValue, setRenameValue] = useState('')
  // Delete confirm modal state
  const [deleteConfirmId, setDeleteConfirmId] = useState(null)
  const [deleteLoading, setDeleteLoading] = useState(false)

  useEffect(() => {
    document.title = `${t('aiChat.title')} — ${t('app.name')}`
  }, [t])

  // Load sessions on mount
  useEffect(() => {
    loadSessions()
  }, [])

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Close context menu on click anywhere
  useEffect(() => {
    if (!contextMenu) return
    const handler = () => setContextMenu(null)
    window.addEventListener('click', handler)
    return () => window.removeEventListener('click', handler)
  }, [contextMenu])

  const loadSessions = async () => {
    try {
      const res = await getAIChatSessions()
      setSessions(res.data)
    } catch {
      toast?.error(t('common.operationFailed'))
    } finally {
      setLoading(false)
    }
  }

  const handleSelectSession = async (sessionId) => {
    setActiveSessionId(sessionId)
    setShowSidebar(false)
    try {
      const res = await getAIChatSession(sessionId)
      setMessages(res.data.messages || [])
    } catch {
      toast?.error(t('common.operationFailed'))
    }
  }

  const handleNewChat = async () => {
    try {
      const res = await createAIChatSession()
      setSessions((prev) => [res.data, ...prev])
      setActiveSessionId(res.data.id)
      setMessages([])
      setShowSidebar(false)
    } catch {
      toast?.error(t('common.operationFailed'))
    }
  }

  const handleDeleteSession = async (sessionId) => {
    setDeleteLoading(true)
    try {
      await deleteAIChatSession(sessionId)
      setSessions((prev) => prev.filter((s) => s.id !== sessionId))
      if (activeSessionId === sessionId) {
        setActiveSessionId(null)
        setMessages([])
        setShowSidebar(true)
      }
      toast?.success(t('aiChat.deleted'))
    } catch {
      toast?.error(t('common.operationFailed'))
    } finally {
      setDeleteLoading(false)
      setDeleteConfirmId(null)
    }
  }

  const handleContextMenu = (e, sessionId) => {
    e.preventDefault()
    e.stopPropagation()
    // Position menu, clamping to viewport
    const x = Math.min(e.clientX, window.innerWidth - 180)
    const y = Math.min(e.clientY, window.innerHeight - 140)
    setContextMenu({ x, y, sessionId })
  }

  const handleRenameStart = (sessionId) => {
    const session = sessions.find((s) => s.id === sessionId)
    setRenameValue(session?.title || '')
    setRenameModalId(sessionId)
    setContextMenu(null)
  }

  const handleRenameConfirm = async () => {
    if (!renameValue.trim() || !renameModalId) return
    try {
      const res = await updateAIChatSession(renameModalId, { title: renameValue.trim() })
      setSessions((prev) => prev.map((s) => (s.id === renameModalId ? { ...s, ...res.data } : s)))
      setRenameModalId(null)
    } catch {
      toast?.error(t('common.operationFailed'))
    }
  }

  const handleTogglePin = async (sessionId) => {
    setContextMenu(null)
    const session = sessions.find((s) => s.id === sessionId)
    if (!session) return
    try {
      const res = await updateAIChatSession(sessionId, { is_pinned: !session.is_pinned })
      setSessions((prev) => {
        const updated = prev.map((s) => (s.id === sessionId ? { ...s, ...res.data } : s))
        // Re-sort: pinned first, then by updated_at desc
        return updated.sort((a, b) => {
          if (a.is_pinned !== b.is_pinned) return b.is_pinned ? 1 : -1
          return new Date(b.updated_at) - new Date(a.updated_at)
        })
      })
    } catch {
      toast?.error(t('common.operationFailed'))
    }
  }

  const handleSend = async (e) => {
    e.preventDefault()
    const content = input.trim()
    if (!content || sending) return
    if (content.length > 2000) {
      toast?.error(t('aiChat.errorTooLong'))
      return
    }

    setSending(true)
    setInput('')

    // Optimistic: add user message
    const tempUserMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, tempUserMsg])

    try {
      const res = await sendAIChatMessage(activeSessionId, content)
      const { user_message, ai_message } = res.data

      // Replace temp with real + add AI response
      setMessages((prev) =>
        prev
          .filter((m) => m.id !== tempUserMsg.id)
          .concat([user_message, ai_message])
      )

      // Update session title in sidebar if first message
      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSessionId
            ? { ...s, title: user_message.content.slice(0, 50), message_count: (s.message_count || 0) + 2, last_message_preview: ai_message.content.slice(0, 80) }
            : s
        )
      )
    } catch {
      // Remove temp message on failure
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id))
      setInput(content)
      toast?.error(t('aiChat.sendFailed'))
    } finally {
      setSending(false)
    }
  }

  const handleBack = () => {
    setShowSidebar(true)
  }

  if (loading) return <LoadingSpinner />

  // Mobile: show sidebar or chat
  // Desktop: show both
  return (
    <div className="flex flex-1 min-h-0 gap-4">
      {/* Sidebar - Session list */}
      <div
        className={`${
          showSidebar ? 'flex' : 'hidden'
        } md:flex flex-col w-full md:w-[280px] shrink-0`}
      >
        <div className="glass p-4 flex-1 flex flex-col min-h-0">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-lg">{t('aiChat.title')}</h2>
            <button
              onClick={handleNewChat}
              className="btn-primary text-sm px-3 py-1.5"
            >
              + {t('aiChat.newChat')}
            </button>
          </div>

          {sessions.length === 0 ? (
            <EmptyState
              title={t('aiChat.noSessions')}
              description={t('aiChat.noSessionsDesc')}
              actionText={t('aiChat.startChat')}
              onAction={handleNewChat}
            />
          ) : (
            <div className="flex-1 overflow-y-auto space-y-2">
              {sessions.map((session) => (
                <div
                  key={session.id}
                  onClick={() => handleSelectSession(session.id)}
                  onContextMenu={(e) => handleContextMenu(e, session.id)}
                  className={`p-3 rounded-xl cursor-pointer transition-all group ${
                    activeSessionId === session.id
                      ? 'bg-purple-500/20 border border-purple-500/30'
                      : 'hover:bg-[var(--card-bg)] border border-transparent'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-sm truncate">
                        {session.is_pinned && <span className="mr-1 opacity-70" title={t('aiChat.pinned')}>📌</span>}
                        {session.title}
                      </p>
                      {session.last_message_preview && (
                        <p className="text-xs opacity-50 truncate mt-0.5">
                          {session.last_message_preview}
                        </p>
                      )}
                    </div>
                    <button
                      onClick={(e) => { e.stopPropagation(); setDeleteConfirmId(session.id) }}
                      className="opacity-0 group-hover:opacity-50 hover:!opacity-100 transition-opacity text-red-500 text-xs shrink-0 cursor-pointer"
                      title={t('aiChat.deleteSession')}
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <polyline points="3 6 5 6 21 6" />
                        <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                      </svg>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div
        className={`${
          !showSidebar ? 'flex' : 'hidden'
        } md:flex flex-col flex-1 min-h-0`}
      >
        {activeSessionId ? (
          <>
            {/* Chat header */}
            <div className="glass p-3 mb-3 flex items-center gap-3">
              <button
                onClick={handleBack}
                className="md:hidden opacity-60 hover:opacity-100 transition-opacity cursor-pointer"
              >
                &larr;
              </button>
              <span className="text-xl">🤖</span>
              <h3 className="font-semibold">{t('aiChat.title')}</h3>
              <span className="ml-auto text-xs opacity-40 hidden sm:inline">
                {t('aiChat.disclaimer')}
              </span>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto space-y-3 px-1 pb-3">
              {messages.length === 0 ? (
                <div className="text-center opacity-40 mt-12">
                  <span className="text-4xl block mb-3">🤖</span>
                  {t('aiChat.empty')}
                </div>
              ) : (
                messages.map((msg) => {
                  const isUser = msg.role === 'user'
                  return (
                    <div
                      key={msg.id}
                      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                    >
                      {!isUser && (
                        <span className="text-lg mr-2 mt-1 shrink-0">🤖</span>
                      )}
                      <div
                        className={`max-w-[75%] p-3 rounded-2xl ${
                          isUser
                            ? 'bg-purple-500/30 rounded-br-md'
                            : 'glass-card rounded-bl-md'
                        }`}
                      >
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">
                          {msg.content}
                        </p>
                        <p className="text-xs opacity-40 mt-1 text-right">
                          {new Date(msg.created_at).toLocaleTimeString(
                            LOCALE_MAP[lang] || lang,
                            {
                              timeZone: TZ_MAP[lang] || 'Asia/Taipei',
                              hour: '2-digit',
                              minute: '2-digit',
                            }
                          )}
                        </p>
                      </div>
                    </div>
                  )
                })
              )}
              {sending && (
                <div className="flex justify-start">
                  <span className="text-lg mr-2 mt-1">🤖</span>
                  <div className="glass-card p-3 rounded-2xl rounded-bl-md">
                    <div className="flex items-center gap-1.5 text-sm opacity-60">
                      <span className="inline-block w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <span className="inline-block w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <span className="inline-block w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                      <span className="ml-1">{t('aiChat.typing')}</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <form onSubmit={handleSend} className="glass p-3 flex gap-3">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={t('aiChat.placeholder')}
                className="glass-input flex-1"
                maxLength={2000}
                autoFocus
              />
              <button
                type="submit"
                disabled={sending || !input.trim()}
                className="btn-primary whitespace-nowrap"
              >
                {sending ? t('aiChat.sending') : t('aiChat.send')}
              </button>
            </form>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <EmptyState
              title={t('aiChat.noSessions')}
              description={t('aiChat.noSessionsDesc')}
              actionText={t('aiChat.startChat')}
              onAction={handleNewChat}
            />
          </div>
        )}
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <div
          role="menu"
          className="fixed z-50 glass-card py-1 rounded-xl shadow-xl min-w-[160px] border border-white/10"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => {
            if (e.key === 'Escape') setContextMenu(null)
            if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
              e.preventDefault()
              const items = e.currentTarget.querySelectorAll('[role="menuitem"]')
              const idx = Array.from(items).indexOf(document.activeElement)
              const next = e.key === 'ArrowDown' ? (idx + 1) % items.length : (idx - 1 + items.length) % items.length
              items[next]?.focus()
            }
          }}
          ref={(el) => el?.querySelector('[role="menuitem"]')?.focus()}
        >
          <button
            role="menuitem"
            tabIndex={0}
            className="w-full text-left px-4 py-2 text-sm hover:bg-white/10 transition-colors cursor-pointer focus:bg-white/10 outline-none"
            onClick={() => handleRenameStart(contextMenu.sessionId)}
          >
            {t('aiChat.rename')}
          </button>
          <button
            role="menuitem"
            tabIndex={0}
            className="w-full text-left px-4 py-2 text-sm hover:bg-white/10 transition-colors cursor-pointer focus:bg-white/10 outline-none"
            onClick={() => handleTogglePin(contextMenu.sessionId)}
          >
            {sessions.find((s) => s.id === contextMenu.sessionId)?.is_pinned
              ? t('aiChat.unpin')
              : t('aiChat.pin')}
          </button>
          <button
            role="menuitem"
            tabIndex={0}
            className="w-full text-left px-4 py-2 text-sm text-red-500 hover:bg-white/10 transition-colors cursor-pointer focus:bg-white/10 outline-none"
            onClick={() => { setContextMenu(null); setDeleteConfirmId(contextMenu.sessionId) }}
          >
            {t('aiChat.deleteSession')}
          </button>
        </div>
      )}

      {/* Delete Confirm Modal */}
      <ConfirmModal
        open={!!deleteConfirmId}
        title={t('aiChat.deleteSession')}
        message={t('aiChat.deleteConfirm')}
        confirmText={t('noteDetail.delete')}
        cancelText={t('common.cancel')}
        loading={deleteLoading}
        onConfirm={() => handleDeleteSession(deleteConfirmId)}
        onCancel={() => setDeleteConfirmId(null)}
      />

      {/* Rename Modal */}
      {renameModalId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" onKeyDown={(e) => { if (e.key === 'Escape') setRenameModalId(null) }}>
          <div className="popup-panel p-6 w-full max-w-sm space-y-4" role="dialog" aria-modal="true">
            <h2 className="text-lg font-semibold">{t('aiChat.renameTitle')}</h2>
            <input
              type="text"
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              placeholder={t('aiChat.renamePlaceholder')}
              className="glass-input"
              maxLength={100}
              autoFocus
              onKeyDown={(e) => { if (e.key === 'Enter') handleRenameConfirm() }}
            />
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setRenameModalId(null)}
                className="btn-secondary"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleRenameConfirm}
                disabled={!renameValue.trim()}
                className="btn-primary"
              >
                {t('settings.save')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
