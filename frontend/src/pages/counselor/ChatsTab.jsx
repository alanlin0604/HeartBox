import EmptyState from '../../components/EmptyState'
import { LOCALE_MAP } from '../../utils/locales'

export default function ChatsTab({
  t,
  lang,
  user,
  navigate,
  conversations,
  setTab,
  setContextMenu,
  setDeleteConfirmId,
}) {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{t('counselor.myChats')}</h2>
      {conversations.length === 0 ? (
        <EmptyState
          title={t('counselor.noChats')}
          description={t('counselor.noChatsDesc')}
          actionText={t('counselor.listTab')}
          onAction={() => setTab('list')}
        />
      ) : (
        <div className="space-y-3">
          {conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => navigate(`/chat/${conv.id}`)}
              onContextMenu={(e) => {
                e.preventDefault()
                e.stopPropagation()
                setContextMenu({ x: e.clientX, y: e.clientY, type: 'conversation', id: conv.id })
              }}
              className="glass-card p-4 cursor-pointer hover:border-orange-500/30 transition-all flex justify-between items-center"
            >
              <div>
                <h3 className="font-semibold">{conv.other_user.display_name || conv.other_user.username}</h3>
                {conv.last_message && (
                  <p className="text-sm text-slate-400 mt-1">
                    {conv.last_message.sender_name}: {conv.last_message.content}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  {conv.unread_count > 0 && (
                    <span className="inline-block bg-orange-500 text-white text-xs font-bold px-2 py-1 rounded-full">
                      {conv.unread_count}
                    </span>
                  )}
                  <p className="text-xs opacity-40 mt-1">
                    {new Date(conv.updated_at).toLocaleDateString(LOCALE_MAP[lang] || lang, {
                      timeZone: user?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); setDeleteConfirmId(conv.id) }}
                  className="text-xs px-2 py-1 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-colors cursor-pointer"
                  title={t('chat.deleteConversation')}
                >
                  {t('noteDetail.delete')}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
