import { memo } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useLang } from '../context/LanguageContext'
import { LOCALE_MAP } from '../utils/locales'
import MoodBadge from './MoodBadge'
import HighlightText from './HighlightText'
import { ACTIVITY_ICONS } from './icons/ActivityIcons'

// Strip any residual HTML tags from content_preview (safety net)
const stripHtml = (str) => str ? str.replace(/<[^>]*>/g, '').replace(/&lt;|&gt;|&amp;|&quot;|&#39;/g, m => ({ '&lt;': '<', '&gt;': '>', '&amp;': '&', '&quot;': '"', '&#39;': "'" })[m] || m) : ''

export default memo(function NoteCard({ note, highlight }) {
  const { user } = useAuth()
  const { lang, t } = useLang()

  const date = new Date(note.created_at).toLocaleDateString(LOCALE_MAP[lang] || lang, {
    timeZone: user?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })

  // Merge tag sources: M2M ``note.tags`` array (new system, objects with
  // .name) and legacy ``metadata.tags`` (string list). Display names dedup
  // by lowercased value so a note with both new + old tags doesn't show
  // "#happy #Happy" twice.
  const tagsM2M = Array.isArray(note.tags) ? note.tags : []
  const tagsLegacy = Array.isArray(note.metadata?.tags) ? note.metadata.tags : []
  const tagNamesSeen = new Set()
  const tags = []
  for (const t of tagsM2M) {
    const name = (t?.name || '').trim()
    if (!name) continue
    const key = name.toLowerCase()
    if (tagNamesSeen.has(key)) continue
    tagNamesSeen.add(key)
    tags.push(name)
  }
  for (const name of tagsLegacy) {
    if (typeof name !== 'string') continue
    const trimmed = name.trim()
    const key = trimmed.toLowerCase()
    if (!trimmed || tagNamesSeen.has(key)) continue
    tagNamesSeen.add(key)
    tags.push(trimmed)
  }
  const activities = Array.isArray(note.metadata?.activities) ? note.metadata.activities : []

  return (
    <Link
      to={`/notes/${note.id}`}
      className="block focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-orange-400 rounded-xl"
      aria-label={`${t('noteCard.viewEntry') || '查看日記'}: ${date}`}
    >
      <div className="glass-card p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-[var(--text-secondary)]">{date}</span>
            {note.attachments?.length > 0 && (
              <span className="text-xs opacity-40" title={t('noteCard.hasAttachments')}>
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
                </svg>
                <span className="sr-only">{t('noteCard.hasAttachments')}</span>
              </span>
            )}
          </div>
          <MoodBadge score={note.sentiment_score} />
        </div>
        <p className="text-sm leading-relaxed mb-3 opacity-80">
          <HighlightText text={stripHtml(note.content_preview) || '...'} keyword={highlight} />
        </p>
        {(tags.length > 0 || activities.length > 0) && (
          <div className="flex flex-wrap items-center gap-1.5">
            {activities.map((act) => {
              const ActivityIcon = ACTIVITY_ICONS[act]
              return (
                <span
                  key={`act-${act}`}
                  className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-blue-500/15 text-blue-500 border border-blue-500/20"
                  title={t(`activities.${act}`) !== `activities.${act}` ? t(`activities.${act}`) : act}
                >
                  {ActivityIcon ? <ActivityIcon className="w-3 h-3" /> : null}
                  <span>{t(`activities.${act}`) !== `activities.${act}` ? t(`activities.${act}`) : act}</span>
                </span>
              )
            })}
            {tags.map((tag) => (
              <span
                key={`tag-${tag}`}
                className="text-xs px-2 py-0.5 rounded-full bg-orange-500/15 text-orange-500 border border-orange-500/20"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}
        {note.stress_index != null && (
          <div className="mt-2 flex items-center gap-2">
            <span className="text-xs text-slate-400">{t('noteCard.stress')}</span>
            <div className="flex-1 h-1.5 rounded-full" style={{ background: 'var(--stress-bar-bg)' }}>
              <div
                className="h-full rounded-full bg-gradient-to-r from-green-400 via-yellow-400 to-red-500"
                style={{ width: `${note.stress_index * 10}%` }}
              />
            </div>
            <span className="text-xs text-slate-400">{note.stress_index}/10</span>
          </div>
        )}
      </div>
    </Link>
  )
})
