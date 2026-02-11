import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getNotes, createNote, uploadAttachment } from '../api/notes'
import { useLang } from '../context/LanguageContext'
import NoteForm from '../components/NoteForm'
import NoteCard from '../components/NoteCard'
import LoadingSpinner from '../components/LoadingSpinner'
import SearchFilterPanel from '../components/SearchFilterPanel'
import ExportPDFButton from '../components/ExportPDFButton'
import AlertBanner from '../components/AlertBanner'
import EmptyState from '../components/EmptyState'
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
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchNotes(1, filters)
  }, [filters])

  const handleCreate = async (content, metadata, files = []) => {
    setCreating(true)
    try {
      const res = await createNote(content, metadata)
      const noteId = res.data.id
      // Upload attachments after note creation
      for (const file of files) {
        await uploadAttachment(noteId, file)
      }
      await fetchNotes(1, filters)
      toast?.success(t('noteForm.saved'))
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

  return (
    <div className="space-y-6 mt-4">
      <AlertBanner />

      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">{t('journal.recentNotes')}</h2>
        <ExportPDFButton />
      </div>

      <SearchFilterPanel filters={filters} onFilterChange={handleFilterChange} />

      <NoteForm onSubmit={handleCreate} loading={creating} />

      <div>
        {loading ? (
          <LoadingSpinner />
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
              <NoteCard key={note.id} note={note} highlight={filters.search} />
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
    </div>
  )
}
