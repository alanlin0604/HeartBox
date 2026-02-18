import { memo } from 'react'
import { Link } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'
import { LOCALE_MAP, TZ_MAP } from '../utils/locales'
import MoodBadge from './MoodBadge'
import HighlightText from './HighlightText'

// Strip any residual HTML tags from content_preview (safety net)
const stripHtml = (str) => str ? str.replace(/<[^>]*>/g, '').replace(/&lt;|&gt;|&amp;|&quot;|&#39;/g, m => ({ '&lt;': '<', '&gt;': '>', '&amp;': '&', '&quot;': '"', '&#39;': "'" })[m] || m) : ''

export default memo(function NoteCard({ note, highlight }) {
  const { lang, t } = useLang()

  const date = new Date(note.created_at).toLocaleDateString(LOCALE_MAP[lang] || lang, {
    timeZone: TZ_MAP[lang] || 'Asia/Taipei',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

  const tags = note.metadata?.tags || []

  return (
    <Link to={`/notes/${note.id}`} className="block">
      <div className="glass-card p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs opacity-60">{date}</span>
            {note.attachments?.length > 0 && (
              <span className="text-xs opacity-40" title={t('noteCard.hasAttachments')}>
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
                </svg>
              </span>
            )}
          </div>
          <MoodBadge score={note.sentiment_score} />
        </div>
        <p className="text-sm leading-relaxed mb-3 opacity-80">
          <HighlightText text={stripHtml(note.content_preview) || '...'} keyword={highlight} />
        </p>
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {tags.map((tag) => (
              <span
                key={tag}
                className="text-xs px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-500 border border-purple-500/20"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}
        {note.stress_index != null && (
          <div className="mt-2 flex items-center gap-2">
            <span className="text-xs opacity-50">{t('noteCard.stress')}</span>
            <div className="flex-1 h-1.5 rounded-full" style={{ background: 'var(--stress-bar-bg)' }}>
              <div
                className="h-full rounded-full bg-gradient-to-r from-green-400 via-yellow-400 to-red-500"
                style={{ width: `${note.stress_index * 10}%` }}
              />
            </div>
            <span className="text-xs opacity-60">{note.stress_index}/10</span>
          </div>
        )}
      </div>
    </Link>
  )
})
