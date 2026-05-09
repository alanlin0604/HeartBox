import EmptyState from '../../components/EmptyState'
import { LOCALE_MAP } from '../../utils/locales'

export default function SharedNotesTab({
  t,
  lang,
  user,
  sharedNotes,
  expandedNoteId,
  setExpandedNoteId,
  setTab,
}) {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{t('share.receivedTitle')}</h2>
      {sharedNotes.length === 0 ? (
        <EmptyState
          title={t('share.noShared')}
          description={t('share.noSharedDesc')}
          actionText={t('schedule.tab')}
          onAction={() => setTab('schedule')}
        />
      ) : (
        <div className="space-y-3">
          {sharedNotes.map((sn) => (
            <div
              key={sn.id}
              className="glass-card p-4 space-y-2 cursor-pointer hover:border-orange-500/30 transition-all"
              onClick={() => setExpandedNoteId(expandedNoteId === sn.id ? null : sn.id)}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">
                  {sn.author || t('share.anonymousUser')}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-xs opacity-40">
                    {new Date(sn.shared_at).toLocaleDateString(LOCALE_MAP[lang] || lang, {
                      timeZone: user?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </span>
                  <span className="text-xs opacity-40">{expandedNoteId === sn.id ? '▲' : '▼'}</span>
                </div>
              </div>
              {expandedNoteId === sn.id ? (
                <>
                  <p className="text-sm opacity-80 whitespace-pre-wrap">{sn.note_content || sn.note_preview}</p>
                  {sn.note_tags?.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {sn.note_tags.map((tag) => (
                        <span key={tag} className="text-xs px-2 py-0.5 rounded-full bg-orange-500/15 text-orange-400 border border-orange-500/20">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                  {sn.note_ai_feedback && (
                    <div className="glass-card p-3 border-l-4 border-orange-500/50 mt-2">
                      <p className="text-xs font-semibold text-orange-400 mb-1">{t('noteDetail.aiFeedback')}</p>
                      <p className="text-xs opacity-70 whitespace-pre-wrap">{sn.note_ai_feedback}</p>
                    </div>
                  )}
                </>
              ) : (
                <p className="text-sm opacity-80">{sn.note_preview}</p>
              )}
              <div className="flex items-center gap-3 text-xs opacity-60">
                {sn.sentiment_score != null && (
                  <span>{t('dashboard.avgSentiment')}: {sn.sentiment_score?.toFixed(2)}</span>
                )}
                {sn.stress_index != null && (
                  <span>{t('noteCard.stress')}: {sn.stress_index}/10</span>
                )}
                {sn.is_anonymous && (
                  <span className="text-orange-500">{t('share.anonymousLabel')}</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
