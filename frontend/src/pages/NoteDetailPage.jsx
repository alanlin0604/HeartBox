import { useState, useEffect, useMemo, useRef, lazy, Suspense } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import DOMPurify from 'dompurify'
import { getNote, deleteNote, updateNote, togglePin } from '../api/notes'
import { useLang } from '../context/LanguageContext'
import MoodBadge from '../components/MoodBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import ConfirmModal from '../components/ConfirmModal'
import AIFeedbackText from '../components/AIFeedbackText'
import { ACTIVITY_ICONS } from '../components/icons/ActivityIcons'
// Counselor share UI hidden pre-launch — re-enable along with /counselors.
// import ShareNoteButton from '../components/ShareNoteButton'
// import { getNoteShares, unshareNote } from '../api/notes'
import { useToast } from '../context/ToastContext'
import { Card, Button, Input } from '../components/ui'

const RichTextEditor = lazy(() => import('../components/RichTextEditor'))
const ShareNoteToFriends = lazy(() => import('../components/friends/ShareNoteToFriends'))

import { LOCALE_MAP } from '../utils/locales'
import { useAuth } from '../context/AuthContext'

// Map raw weather values (stored by NoteForm or by the demo seed) to their
// localised display strings via the existing dailySuggestion.weather.*
// i18n bucket. Notes seeded by seed_demo_test_accounts persist plain
// English values like 'cloudy' / 'sunny' / 'rainy' / 'stormy', which
// previously rendered raw on the detail page.
const WEATHER_KEY_BY_VALUE = {
  sunny: 'clear', clear: 'clear', sun: 'clear',
  cloudy: 'cloudy', overcast: 'cloudy', partly_cloudy: 'cloudy', 'partly-cloudy': 'cloudy',
  rain: 'rain', rainy: 'rain', light_rain: 'rain', heavy_rain: 'rain', shower: 'rain',
  storm: 'storm', stormy: 'storm', thunderstorm: 'storm',
  snow: 'snow', snowy: 'snow',
  fog: 'fog', foggy: 'fog', mist: 'fog',
  windy: 'cloudy',
}

function localizeWeather(t, raw) {
  if (!raw) return ''
  // Already a localised label (NoteForm dropdown stores values like "⛅ 多雲")
  if (/[一-鿿]/.test(raw)) return raw
  const norm = String(raw).trim().toLowerCase().replace(/\s+/g, '_')
  const key = WEATHER_KEY_BY_VALUE[norm]
  if (key) return t(`dailySuggestion.weather.${key}`)
  return raw
}

export default function NoteDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { lang, t } = useLang()
  const toast = useToast()
  const [note, setNote] = useState(null)
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editWeather, setEditWeather] = useState('')
  const [editTemp, setEditTemp] = useState('')
  const [editTags, setEditTags] = useState('')
  const [saving, setSaving] = useState(false)
  const [shareOpen, setShareOpen] = useState(false)
  const editorRef = useRef(null)
  const [editorContent, setEditorContent] = useState('')

  useEffect(() => { document.title = `${t('nav.journal')} — ${t('app.name')}` }, [t])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getNote(id)
      .then((res) => { if (!cancelled) setNote(res.data) })
      .catch(() => {
        if (cancelled) return
        toast?.error(t('common.operationFailed'))
        window.history.length > 1 ? navigate(-1) : navigate('/')
      })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [id, navigate, toast, t])

  // Counselor share UI hidden pre-launch — `getNoteShares` / `unshareNote`
  // calls removed along with the share button. Re-enable when /counselors ships.

  // Listen for the background AI analysis finishing — pushed via
  // NotificationBell's WebSocket after perform_create scheduled it. When
  // a `note_analyzed` event for THIS note fires, merge the new sentiment /
  // stress / feedback values into the displayed note so the user doesn't
  // need to refresh. Avoids the previous 5-15 s blocking save.
  useEffect(() => {
    const handler = (e) => {
      const payload = e.detail
      if (!payload || String(payload.note_id) !== String(id)) return
      setNote((prev) => prev ? {
        ...prev,
        sentiment_score: payload.sentiment_score,
        stress_index: payload.stress_index,
        ai_feedback: payload.ai_feedback,
      } : prev)
    }
    window.addEventListener('heartbox:note_analyzed', handler)
    return () => window.removeEventListener('heartbox:note_analyzed', handler)
  }, [id])

  // Warn before leaving if editing
  useEffect(() => {
    const handler = (e) => {
      if (editing) {
        e.preventDefault()
        e.returnValue = ''
      }
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [editing])

  const handleTogglePin = async () => {
    try {
      const { data } = await togglePin(id)
      setNote((prev) => ({ ...prev, is_pinned: data.is_pinned }))
    } catch {
      toast?.error(t('common.operationFailed'))
    }
  }

  const handleDelete = async () => {
    setConfirmOpen(false)
    setDeleting(true)
    try {
      await deleteNote(id)
      toast?.success(t('noteDetail.deleted'))
      navigate('/')
    } catch {
      setDeleting(false)
      toast?.error(t('noteDetail.deleteFailed'))
    }
  }

  const handleStartEdit = () => {
    setEditorContent(note.decrypted_content || '')
    setEditWeather(note.metadata?.weather || '')
    setEditTemp(note.metadata?.temperature ?? '')
    setEditTags((note.metadata?.tags || []).join(', '))
    setEditing(true)
  }

  const handleSaveEdit = async () => {
    const content = editorRef.current?.getHTML() || ''
    const textOnly = content.replace(/<[^>]*>/g, '').trim()
    if (!textOnly) return
    setSaving(true)
    const metadata = {}
    if (editWeather) metadata.weather = editWeather
    if (editTemp !== '' && editTemp != null) metadata.temperature = parseFloat(editTemp)
    if (editTags.trim()) metadata.tags = editTags.split(',').map((tag) => tag.trim()).filter(Boolean)
    try {
      const { data } = await updateNote(id, content, metadata)
      setNote(data)
      setEditing(false)
      toast?.success(t('noteDetail.editSaved'))
    } catch {
      toast?.error(t('noteDetail.editSaveFailed'))
    } finally {
      setSaving(false)
    }
  }

  const sanitizedContent = useMemo(
    () => note ? DOMPurify.sanitize(note.decrypted_content || '') : '',
    [note?.decrypted_content]
  )

  if (loading) return <LoadingSpinner />
  if (!note) return null

  const date = new Date(note.created_at).toLocaleDateString(LOCALE_MAP[lang] || lang, {
    timeZone: user?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
    hour: '2-digit',
    minute: '2-digit',
  })

  // Merge tag sources: M2M ``note.tags`` (new system, objects with .name)
  // and legacy ``metadata.tags`` (string list). Dedup by lowercased name.
  const tagsM2M = Array.isArray(note.tags) ? note.tags : []
  const tagsLegacy = Array.isArray(note.metadata?.tags) ? note.metadata.tags : []
  const _tagSeen = new Set()
  const tags = []
  for (const tt of tagsM2M) {
    const name = (tt?.name || '').trim()
    if (!name) continue
    const key = name.toLowerCase()
    if (_tagSeen.has(key)) continue
    _tagSeen.add(key); tags.push(name)
  }
  for (const name of tagsLegacy) {
    if (typeof name !== 'string') continue
    const trimmed = name.trim()
    const key = trimmed.toLowerCase()
    if (!trimmed || _tagSeen.has(key)) continue
    _tagSeen.add(key); tags.push(trimmed)
  }
  const activities = Array.isArray(note.metadata?.activities) ? note.metadata.activities : []
  const attachments = note.attachments || []

  return (
    <div className="max-w-3xl mx-auto mt-2 sm:mt-4 px-2 sm:px-0 space-y-3 sm:space-y-4 pb-6">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/'))}
      >
        &larr; {t('noteDetail.back')}
      </Button>

      <Card variant="default" padding="lg" className="space-y-4" animate staggerDelay={0.1}>
        {/* Header */}
        <div className="space-y-2">
          <div className="text-sm text-slate-400">{date}</div>
          <div className="flex flex-wrap items-center gap-2">
            <MoodBadge score={note.sentiment_score} />
            <button
              onClick={handleTogglePin}
              className={`text-sm px-3 py-2 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg border cursor-pointer transition-colors ${note.is_pinned ? 'bg-yellow-500/20 border-yellow-500/40 text-yellow-500' : 'border-white/10 opacity-60 hover:opacity-100'}`}
              title={note.is_pinned ? t('noteDetail.unpin') : t('noteDetail.pin')}
              aria-label={note.is_pinned ? t('noteDetail.unpin') : t('noteDetail.pin')}
            >
              📌
            </button>
            <div className="flex-1" />
            <Button onClick={handleStartEdit} variant="secondary" size="sm">
              {t('noteDetail.edit')}
            </Button>
            <Button
              onClick={() => setShareOpen(true)}
              variant="secondary"
              size="sm"
              aria-label={t('friends.share.title')}
              title={t('friends.share.title')}
            >
              {t('friends.share.shareButton')}
            </Button>
            {/* Counselor share button hidden pre-launch — re-enable with /counselors. */}
            <Button onClick={() => setConfirmOpen(true)} disabled={deleting} variant="danger" size="sm">
              {deleting ? t('noteDetail.deleting') : t('noteDetail.delete')}
            </Button>
          </div>
        </div>

        {/* Content */}
        {editing ? (
          <div className="glass-card p-3 sm:p-4 space-y-3">
            <div className="rounded-xl overflow-hidden border border-[var(--card-border)]">
              <Suspense fallback={
                <div className="prose prose-invert max-w-none px-3 sm:px-4 py-3 min-h-[140px] flex items-center justify-center opacity-50">
                  <div className="animate-pulse text-sm">Loading editor...</div>
                </div>
              }>
                <RichTextEditor
                  ref={editorRef}
                  initialContent={editorContent}
                  placeholder={t('noteForm.placeholder')}
                  className="prose prose-invert max-w-none px-3 sm:px-4 py-3 min-h-[140px] focus:outline-none [&_.tiptap]:outline-none [&_.tiptap]:min-h-[120px]"
                />
              </Suspense>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <Input value={editWeather} onChange={(e) => setEditWeather(e.target.value)} placeholder={t('noteForm.weather')} />
              <Input type="number" value={editTemp} onChange={(e) => setEditTemp(e.target.value)} placeholder={t('noteForm.temperature')} />
              <Input value={editTags} onChange={(e) => setEditTags(e.target.value)} placeholder={t('noteForm.tags')} />
            </div>
            <div className="flex gap-2">
              <Button type="button" onClick={handleSaveEdit} disabled={saving} loading={saving} size="sm">
                {saving ? t('common.loading') : t('settings.save')}
              </Button>
              <Button type="button" variant="secondary" onClick={() => setEditing(false)} size="sm">
                {t('common.cancel')}
              </Button>
            </div>
          </div>
        ) : (
          <div className="glass-card p-3 sm:p-4 prose prose-invert max-w-none break-words"
            dangerouslySetInnerHTML={{ __html: sanitizedContent }}
          />
        )}

        {/* Attachments */}
        {attachments.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-400">{t('noteDetail.attachments')}</h3>
            <div className="flex flex-wrap gap-3">
              {attachments.map((att) => (
                <img
                  key={att.id}
                  src={att.file}
                  alt={att.original_name}
                  loading="lazy"
                  decoding="async"
                  className="max-w-full sm:max-w-xs rounded-xl border border-white/10"
                />
              ))}
            </div>
          </div>
        )}

        {/* Metadata chips: weather, temperature, activities, tags. All
            three colour groups render in one row so the user gets the
            full context (what kind of day this was) at a glance. */}
        {(note.metadata?.weather || note.metadata?.temperature != null || activities.length > 0 || tags.length > 0) && (
          <div className="flex flex-wrap items-center gap-2">
            {note.metadata?.weather && (
              <span className="text-xs px-2.5 py-1 rounded-full bg-blue-500/15 text-blue-500 border border-blue-500/20">
                {localizeWeather(t, note.metadata.weather)}
              </span>
            )}
            {note.metadata?.temperature != null && (
              <span className="text-xs px-2.5 py-1 rounded-full bg-blue-400/15 text-blue-400 border border-blue-400/20">
                {note.metadata.temperature}°C
              </span>
            )}
            {activities.map((act) => {
              const ActivityIcon = ACTIVITY_ICONS[act]
              const label = t(`activities.${act}`) !== `activities.${act}` ? t(`activities.${act}`) : act
              return (
                <span
                  key={`act-${act}`}
                  className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-purple-500/15 text-purple-500 border border-purple-500/20"
                  title={label}
                >
                  {ActivityIcon ? <ActivityIcon className="w-3 h-3" /> : null}
                  <span>{label}</span>
                </span>
              )
            })}
            {tags.map((tag) => (
              <span
                key={`tag-${tag}`}
                className="text-xs px-2.5 py-1 rounded-full bg-orange-500/15 text-orange-500 border border-orange-500/20"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}

        {/* Stress Index */}
        {note.stress_index != null && (
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-400 shrink-0">{t('noteDetail.stressIndex')}</span>
            <div className="flex-1 h-2 rounded-full max-w-xs" style={{ background: 'var(--stress-bar-bg)' }}>
              <div
                className="h-full rounded-full bg-gradient-to-r from-green-400 via-yellow-400 to-red-500"
                style={{ width: `${note.stress_index * 10}%` }}
              />
            </div>
            <span className="text-sm font-medium opacity-70 shrink-0">{note.stress_index}/10</span>
          </div>
        )}

        {/* Sentiment Score */}
        {note.sentiment_score != null && (
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-400 shrink-0">{t('noteDetail.sentimentScore')}</span>
            <div className="flex-1 h-2 rounded-full max-w-xs" style={{ background: 'var(--stress-bar-bg)' }}>
              <div
                className="h-full rounded-full bg-gradient-to-r from-red-400 via-yellow-400 to-green-500"
                style={{ width: `${((note.sentiment_score + 1) / 2) * 100}%` }}
              />
            </div>
            <span className="text-sm font-medium opacity-70 shrink-0">{note.sentiment_score.toFixed(2)}</span>
          </div>
        )}

        {/* AI Feedback */}
        {note.ai_feedback ? (
          <div className="glass-card p-4 border-l-4 border-orange-500/50">
            <h3 className="text-sm font-semibold text-orange-500 mb-2">{t('noteDetail.aiFeedback')}</h3>
            <AIFeedbackText text={note.ai_feedback} />
            <p className="text-xs opacity-40 mt-3 italic">
              {t('noteDetail.aiDisclaimer')}
            </p>
          </div>
        ) : (
          // sentiment_score === null is the signal that the background AI
          // analysis worker hasn't finished yet (perform_create returned
          // immediately and threading.Thread is still running on the
          // backend). Show a placeholder so the user knows analysis is
          // coming, instead of leaving the section blank or stale.
          note.sentiment_score == null && (
            <div className="glass-card p-4 border-l-4 border-orange-500/30">
              <h3 className="text-sm font-semibold text-orange-500/70 mb-2 flex items-center gap-2">
                <span className="inline-block w-2 h-2 rounded-full bg-orange-500 animate-pulse" />
                {t('noteDetail.aiAnalyzing')}
              </h3>
              <p className="text-sm leading-relaxed opacity-50">
                {t('noteDetail.aiAnalyzingDesc')}
              </p>
            </div>
          )
        )}

        {/* Shared With (counselor list) hidden pre-launch — re-enable with /counselors. */}
      </Card>
      <ConfirmModal
        open={confirmOpen}
        title={t('noteDetail.confirmTitle')}
        message={t('noteDetail.confirmDelete')}
        confirmText={t('noteDetail.delete')}
        cancelText={t('common.cancel')}
        loading={deleting}
        onConfirm={handleDelete}
        onCancel={() => setConfirmOpen(false)}
      />
      {shareOpen && (
        <Suspense fallback={null}>
          <ShareNoteToFriends
            noteId={Number(id)}
            onClose={() => setShareOpen(false)}
            onShared={() => setShareOpen(false)}
          />
        </Suspense>
      )}
    </div>
  )
}
