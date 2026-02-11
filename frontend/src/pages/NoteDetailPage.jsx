import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getNote, deleteNote, updateNote, togglePin } from '../api/notes'
import { useLang } from '../context/LanguageContext'
import MoodBadge from '../components/MoodBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import ShareNoteButton from '../components/ShareNoteButton'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../context/ToastContext'

import { LOCALE_MAP, TZ_MAP } from '../utils/locales'

export default function NoteDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { lang, t } = useLang()
  const toast = useToast()
  const [note, setNote] = useState(null)
  const [loading, setLoading] = useState(true)
  const [deleting, setDeleting] = useState(false)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [editWeather, setEditWeather] = useState('')
  const [editTemp, setEditTemp] = useState('')
  const [editTags, setEditTags] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getNote(id)
      .then((res) => setNote(res.data))
      .catch(() => navigate('/'))
      .finally(() => setLoading(false))
  }, [id, navigate])

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
      toast?.error('操作失敗')
    }
  }

  const handleDelete = async () => {
    setConfirmOpen(false)
    setDeleting(true)
    try {
      await deleteNote(id)
      toast?.success(t('noteDetail.deleted'))
      navigate('/')
    } catch (err) {
      console.error('Failed to delete:', err)
      setDeleting(false)
      toast?.error(t('noteDetail.deleteFailed'))
    }
  }

  const handleStartEdit = () => {
    setEditContent(note.decrypted_content || '')
    setEditWeather(note.metadata?.weather || '')
    setEditTemp(note.metadata?.temperature ?? '')
    setEditTags((note.metadata?.tags || []).join(', '))
    setEditing(true)
  }

  const handleSaveEdit = async () => {
    if (!editContent.trim()) return
    setSaving(true)
    const metadata = {}
    if (editWeather) metadata.weather = editWeather
    if (editTemp !== '' && editTemp != null) metadata.temperature = parseFloat(editTemp)
    if (editTags.trim()) metadata.tags = editTags.split(',').map((tag) => tag.trim()).filter(Boolean)
    try {
      const { data } = await updateNote(id, editContent, metadata)
      setNote(data)
      setEditing(false)
      toast?.success(t('noteDetail.editSaved'))
    } catch {
      toast?.error(t('noteDetail.editSaveFailed'))
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <LoadingSpinner />
  if (!note) return null

  const date = new Date(note.created_at).toLocaleDateString(LOCALE_MAP[lang] || lang, {
    timeZone: TZ_MAP[lang] || 'Asia/Taipei',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
    hour: '2-digit',
    minute: '2-digit',
  })

  const tags = note.metadata?.tags || []
  const attachments = note.attachments || []

  return (
    <div className="max-w-3xl mx-auto mt-4 space-y-4">
      <button
        onClick={() => navigate('/')}
        className="text-sm opacity-60 hover:opacity-100 transition-opacity cursor-pointer"
      >
        &larr; {t('noteDetail.back')}
      </button>

      <div className="glass p-6 space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <span className="text-sm opacity-60">{date}</span>
          <div className="flex items-center gap-3">
            <MoodBadge score={note.sentiment_score} />
            <button
              onClick={handleTogglePin}
              className={`text-xs px-2 py-1 rounded-lg border cursor-pointer transition-colors ${note.is_pinned ? 'bg-yellow-500/20 border-yellow-500/40 text-yellow-500' : 'border-white/10 opacity-60 hover:opacity-100'}`}
              title={note.is_pinned ? '取消置頂' : '置頂'}
            >
              📌
            </button>
            <ShareNoteButton noteId={note.id} />
            <button onClick={handleStartEdit} className="btn-secondary text-xs">
              {t('noteDetail.edit')}
            </button>
            <button onClick={() => setConfirmOpen(true)} disabled={deleting} className="btn-danger text-xs">
              {deleting ? t('noteDetail.deleting') : t('noteDetail.delete')}
            </button>
          </div>
        </div>

        {/* Content */}
        {editing ? (
          <div className="glass-card p-4 space-y-3">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="glass-input min-h-[140px] resize-y"
            />
            <div className="grid grid-cols-3 gap-3">
              <input value={editWeather} onChange={(e) => setEditWeather(e.target.value)} placeholder={t('noteForm.weather')} className="glass-input" />
              <input type="number" value={editTemp} onChange={(e) => setEditTemp(e.target.value)} placeholder={t('noteForm.temperature')} className="glass-input" />
              <input value={editTags} onChange={(e) => setEditTags(e.target.value)} placeholder={t('noteForm.tags')} className="glass-input" />
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={handleSaveEdit} className="btn-primary text-sm" disabled={saving}>
                {saving ? t('common.loading') : t('settings.save')}
              </button>
              <button type="button" onClick={() => setEditing(false)} className="btn-secondary text-sm">
                {t('common.cancel')}
              </button>
            </div>
          </div>
        ) : (
          <div className="glass-card p-4">
            <p className="leading-relaxed whitespace-pre-wrap">
              {note.decrypted_content}
            </p>
          </div>
        )}

        {/* Attachments */}
        {attachments.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold opacity-60">{t('noteDetail.attachments')}</h3>
            <div className="flex flex-wrap gap-3">
              {attachments.map((att) =>
                att.file_type === 'image' ? (
                  <img
                    key={att.id}
                    src={att.file}
                    alt={att.original_name}
                    className="max-w-xs rounded-xl border border-white/10"
                  />
                ) : (
                  <div key={att.id} className="glass-card p-3 flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M9 18V5l12-2v13"/>
                      <circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>
                    </svg>
                    <span className="text-xs">{att.original_name}</span>
                    <audio controls src={att.file} className="h-8" />
                  </div>
                )
              )}
            </div>
          </div>
        )}

        {/* Metadata */}
        {(note.metadata?.weather || note.metadata?.temperature != null || tags.length > 0) && (
          <div className="flex flex-wrap items-center gap-3">
            {note.metadata?.weather && (
              <span className="text-xs px-2.5 py-1 rounded-full bg-blue-500/15 text-blue-500 border border-blue-500/20">
                {note.metadata.weather}
              </span>
            )}
            {note.metadata?.temperature != null && (
              <span className="text-xs px-2.5 py-1 rounded-full bg-orange-500/15 text-orange-500 border border-orange-500/20">
                {note.metadata.temperature}°C
              </span>
            )}
            {tags.map((tag) => (
              <span
                key={tag}
                className="text-xs px-2.5 py-1 rounded-full bg-purple-500/15 text-purple-500 border border-purple-500/20"
              >
                #{tag}
              </span>
            ))}
          </div>
        )}

        {/* Stress Index */}
        {note.stress_index != null && (
          <div className="flex items-center gap-3">
            <span className="text-sm opacity-60">{t('noteDetail.stressIndex')}</span>
            <div className="flex-1 h-2 rounded-full max-w-xs" style={{ background: 'var(--stress-bar-bg)' }}>
              <div
                className="h-full rounded-full bg-gradient-to-r from-green-400 via-yellow-400 to-red-500"
                style={{ width: `${note.stress_index * 10}%` }}
              />
            </div>
            <span className="text-sm font-medium opacity-70">{note.stress_index}/10</span>
          </div>
        )}

        {/* AI Feedback */}
        {note.ai_feedback && (
          <div className="glass-card p-4 border-l-4 border-purple-500/50">
            <h3 className="text-sm font-semibold text-purple-500 mb-2">{t('noteDetail.aiFeedback')}</h3>
            <p className="text-sm leading-relaxed whitespace-pre-wrap opacity-80">
              {note.ai_feedback}
            </p>
            <p className="text-xs opacity-40 mt-3 italic">
              此為 AI 分析結果，僅供參考，不構成專業醫療或心理諮詢建議。
            </p>
          </div>
        )}
      </div>
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
    </div>
  )
}
