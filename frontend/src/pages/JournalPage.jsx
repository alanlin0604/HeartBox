import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getNotes, createNote, uploadAttachment, reanalyzeNote, batchDeleteNotes } from '../api/notes'
import { getAnalytics } from '../api/analytics'
import { useLang } from '../context/LanguageContext'
import NoteForm from '../components/NoteForm'
import NoteCard from '../components/NoteCard'
import LoadingSpinner from '../components/LoadingSpinner'
import SearchFilterPanel from '../components/SearchFilterPanel'
import ExportPDFButton from '../components/ExportPDFButton'
import AlertBanner from '../components/AlertBanner'
import EmptyState from '../components/EmptyState'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../context/ToastContext'

export default function JournalPage() {
  const { t } = useLang()
  const toast = useToast()
  const [searchParams] = useSearchParams()
  const [notes, setNotes] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [streak, setStreak] = useState(0)
  const [selectMode, setSelectMode] = useState(false)
  const [selected, setSelected] = useState(new Set())
  const [batchConfirmOpen, setBatchConfirmOpen] = useState(false)
  const [batchDeleting, setBatchDeleting] = useState(false)

  // Initialize filters from URL query params (for calendar click-through)
  const [filters, setFilters] = useState(() => {
    const initial = {}
    const dateFrom = searchParams.get('date_from')
    const dateTo = searchParams.get('date_to')
    if (dateFrom) initial.date_from = dateFrom
    if (dateTo) initial.date_to = dateTo
    return initial
  })

  const fetchNotes = async (p = 1, f = filters) => {
    setLoading(true)
    try {
      const { data } = await getNotes(p, f)
      setNotes(data.results || [])
      setHasNext(!!data.next)
      setPage(p)
    } catch (err) {
      console.error('Failed to fetch notes:', err)
      toast?.error(t('common.operationFailed'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { document.title = `${t('nav.journal')} — HeartBox` }, [t])

  useEffect(() => {
    fetchNotes(1, filters)
  }, [filters])

  useEffect(() => {
    const timer = setTimeout(() => {
      getAnalytics('week', 30)
        .then((res) => setStreak(res.data.current_streak || 0))
        .catch(() => {})
    }, 100)
    return () => clearTimeout(timer)
  }, [])

  const handleCreate = async (content, metadata, files = []) => {
    setCreating(true)
    try {
      const res = await createNote(content, metadata)
      const noteId = res.data.id
      // Upload attachments after note creation (don't block refresh on failure)
      let attachFailed = false
      const hasImages = files.some((f) => f.type.startsWith('image/'))
      for (const file of files) {
        try {
          await uploadAttachment(noteId, file)
        } catch {
          attachFailed = true
        }
      }
      // Re-analyze with images if any were uploaded successfully
      if (hasImages && !attachFailed) {
        try {
          await reanalyzeNote(noteId)
        } catch {
          // Non-critical — text-only analysis already saved
        }
      }
      await fetchNotes(1, filters)
      if (attachFailed) {
        toast?.error(t('noteForm.attachFailed'))
      } else {
        toast?.success(t('noteForm.saved'))
      }
    } catch (err) {
      console.error('Failed to create note:', err)
      toast?.error(t('noteForm.saveFailed'))
    } finally {
      setCreating(false)
    }
  }

  const handleFilterChange = (newFilters) => {
    setFilters(newFilters)
    setPage(1)
  }

  const toggleSelect = (id) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleBatchDelete = async () => {
    setBatchConfirmOpen(false)
    setBatchDeleting(true)
    try {
      const ids = [...selected]
      const { data } = await batchDeleteNotes(ids)
      toast?.success(t('journal.batchDeleteSuccess', { count: data.deleted }))
      setSelected(new Set())
      setSelectMode(false)
      await fetchNotes(1, filters)
    } catch {
      toast?.error(t('journal.batchDeleteFailed'))
    } finally {
      setBatchDeleting(false)
    }
  }

  return (
    <div className="space-y-6 mt-4">
      <AlertBanner />

      {/* Write section */}
      <NoteForm onSubmit={handleCreate} loading={creating} />

      {streak > 0 && (
        <div className="glass-card p-3 flex items-center gap-2 text-sm">
          <span className="text-xl">🔥</span>
          <span className="font-medium">{t('journal.streak', { days: streak })}</span>
        </div>
      )}

      {/* Divider */}
      <hr className="border-white/10" />

      {/* Browse section */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-lg font-semibold">{t('journal.recentNotes')}</h2>
        <div className="flex items-center gap-2">
          {selectMode ? (
            <>
              <button
                onClick={() => {
                  if (selected.size === notes.length) setSelected(new Set())
                  else setSelected(new Set(notes.map((n) => n.id)))
                }}
                className="btn-secondary text-xs"
              >
                {t('journal.selectAll')}
              </button>
              <button
                onClick={() => setBatchConfirmOpen(true)}
                disabled={selected.size === 0 || batchDeleting}
                className="btn-danger text-xs disabled:opacity-30"
              >
                {batchDeleting ? t('common.loading') : t('journal.batchDelete', { count: selected.size })}
              </button>
              <button
                onClick={() => { setSelectMode(false); setSelected(new Set()) }}
                className="btn-secondary text-xs"
              >
                {t('journal.cancelSelect')}
              </button>
            </>
          ) : (
            <>
              {notes.length > 0 && (
                <button onClick={() => setSelectMode(true)} className="btn-secondary text-xs">
                  {t('journal.selectMode')}
                </button>
              )}
              <ExportPDFButton />
            </>
          )}
        </div>
      </div>

      <SearchFilterPanel filters={filters} onFilterChange={handleFilterChange} />

      <div>
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="glass-card p-4 animate-pulse space-y-3">
                <div className="h-4 bg-white/10 rounded w-3/4" />
                <div className="h-3 bg-white/10 rounded w-1/2" />
                <div className="h-3 bg-white/10 rounded w-1/3" />
              </div>
            ))}
          </div>
        ) : notes.length === 0 ? (
          <EmptyState
            title={t('journal.empty')}
            description={t('journal.emptyDescription')}
            actionText={t('journal.writeFirst')}
            onAction={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
          />
        ) : (
          <div className="space-y-3">
            {notes.map((note) => (
              <div key={note.id} className="flex items-start gap-2">
                {selectMode && (
                  <input
                    type="checkbox"
                    checked={selected.has(note.id)}
                    onChange={() => toggleSelect(note.id)}
                    className="mt-4 w-4 h-4 accent-purple-500 cursor-pointer flex-shrink-0"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <NoteCard note={note} highlight={filters.search} />
                </div>
              </div>
            ))}
          </div>
        )}

        {(page > 1 || hasNext) && (
          <div className="flex justify-center gap-4 mt-4">
            <button
              onClick={() => fetchNotes(page - 1, filters)}
              disabled={page <= 1}
              className="btn-primary text-sm disabled:opacity-30"
            >
              {t('journal.prevPage')}
            </button>
            <span className="opacity-60 text-sm self-center">
              {t('journal.page', { page })}
            </span>
            <button
              onClick={() => fetchNotes(page + 1, filters)}
              disabled={!hasNext}
              className="btn-primary text-sm disabled:opacity-30"
            >
              {t('journal.nextPage')}
            </button>
          </div>
        )}
      </div>
      <ConfirmModal
        open={batchConfirmOpen}
        title={t('journal.batchDelete', { count: selected.size })}
        message={t('journal.batchDeleteConfirm', { count: selected.size })}
        confirmText={t('noteDetail.delete')}
        cancelText={t('common.cancel')}
        loading={batchDeleting}
        onConfirm={handleBatchDelete}
        onCancel={() => setBatchConfirmOpen(false)}
      />
    </div>
  )
}
