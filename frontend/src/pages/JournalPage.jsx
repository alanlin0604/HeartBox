import { useState, useEffect, useMemo, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getNotes, createNote, uploadAttachment, reanalyzeNote, batchDeleteNotes, getTrashNotes, restoreNote, permanentDeleteNote, togglePin, deleteNote } from '../api/notes'
import { getAnalytics } from '../api/analytics'
import { useLang } from '../context/LanguageContext'
import NoteForm from '../components/NoteForm'
import NoteCard from '../components/NoteCard'
import SkeletonCard from '../components/SkeletonCard'
import SearchFilterPanel from '../components/SearchFilterPanel'
import ExportPDFButton from '../components/ExportPDFButton'
import AlertBanner from '../components/AlertBanner'
import EmptyState from '../components/EmptyState'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../context/ToastContext'
import FeedbackWidget from '../components/FeedbackWidget'

export default function JournalPage() {
  const { t } = useLang()
  const toast = useToast()
  const [searchParams] = useSearchParams()
  const [notes, setNotes] = useState([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [totalCount, setTotalCount] = useState(0)
  const [streak, setStreak] = useState(0)
  const [weekAvgMood, setWeekAvgMood] = useState(null)
  const [selectMode, setSelectMode] = useState(false)
  const [selected, setSelected] = useState(new Set())
  const [batchConfirmOpen, setBatchConfirmOpen] = useState(false)
  const [batchDeleting, setBatchDeleting] = useState(false)
  const [showTrash, setShowTrash] = useState(false)
  const [trashNotes, setTrashNotes] = useState([])
  const [trashLoading, setTrashLoading] = useState(false)
  const [contextMenu, setContextMenu] = useState(null) // { x, y, noteId }
  const [deleteConfirmId, setDeleteConfirmId] = useState(null)

  // Close context menu on click anywhere
  useEffect(() => {
    if (!contextMenu) return
    const handler = () => setContextMenu(null)
    window.addEventListener('click', handler)
    return () => window.removeEventListener('click', handler)
  }, [contextMenu])

  const handleContextMenu = useCallback((e, noteId) => {
    e.preventDefault()
    e.stopPropagation()
    const x = Math.min(e.clientX, window.innerWidth - 180)
    const y = Math.min(e.clientY, window.innerHeight - 140)
    setContextMenu({ x, y, noteId })
  }, [])

  const handleTogglePin = async (noteId) => {
    setContextMenu(null)
    try {
      const { data } = await togglePin(noteId)
      setNotes((prev) => prev.map((n) => n.id === noteId ? { ...n, is_pinned: data.is_pinned } : n))
      toast?.success(data.is_pinned ? t('journal.pinned') : t('journal.unpinned'))
    } catch {
      toast?.error(t('common.operationFailed'))
    }
  }

  const handleDeleteNote = async (noteId) => {
    setDeleteConfirmId(null)
    try {
      await deleteNote(noteId)
      setNotes((prev) => prev.filter((n) => n.id !== noteId))
      toast?.success(t('journal.noteDeleted'))
    } catch {
      toast?.error(t('common.operationFailed'))
    }
  }

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
      setTotalCount(data.count || 0)
      setPage(p)
    } catch (err) {
      console.error('Failed to fetch notes:', err)
      toast?.error(t('common.operationFailed'))
    } finally {
      setLoading(false)
    }
  }

  const loadTrash = async () => {
    setTrashLoading(true)
    try {
      const { data } = await getTrashNotes()
      setTrashNotes(data)
    } catch { setTrashNotes([]) }
    finally { setTrashLoading(false) }
  }

  const handleRestore = async (id) => {
    try {
      await restoreNote(id)
      setTrashNotes((prev) => prev.filter((n) => n.id !== id))
      toast?.success(t('journal.restore'))
      fetchNotes(page, filters)
    } catch { toast?.error(t('common.operationFailed')) }
  }

  const handlePermanentDelete = async (id) => {
    try {
      await permanentDeleteNote(id)
      setTrashNotes((prev) => prev.filter((n) => n.id !== id))
    } catch { toast?.error(t('common.operationFailed')) }
  }

  useEffect(() => { document.title = `${t('nav.journal')} — ${t('app.name')}` }, [t])

  useEffect(() => {
    fetchNotes(1, filters)
  }, [filters])

  useEffect(() => {
    const timer = setTimeout(() => {
      getAnalytics('week', 30)
        .then((res) => {
          setStreak(res.data.current_streak || 0)
          // Compute weekly average mood from mood_trends
          const trends = res.data.mood_trends || []
          if (trends.length > 0) {
            const sum = trends.reduce((acc, t) => acc + (t.avg_sentiment ?? 0), 0)
            setWeekAvgMood((sum / trends.length).toFixed(2))
          }
        })
        .catch(() => {})
    }, 100)
    return () => clearTimeout(timer)
  }, [])

  // Count today's notes from fetched notes list
  const todayNoteCount = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10)
    return notes.filter((n) => n.created_at?.slice(0, 10) === today).length
  }, [notes])

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

  // Sidebar content (shared between desktop aside and mobile inline)
  const sidebarContent = (
    <>
      {streak > 0 && (
        <div className="glass-card p-3 flex items-center gap-2 text-sm">
          <span className="text-xl">🔥</span>
          <span className="font-medium">{t('journal.streak', { days: streak })}</span>
        </div>
      )}
      <div className="glass-card p-4 space-y-3">
        <h3 className="text-sm font-semibold opacity-70">{t('journal.todayNotes')}</h3>
        <p className="text-2xl font-bold">{todayNoteCount}</p>
      </div>
      {weekAvgMood !== null && (
        <div className="glass-card p-4 space-y-3">
          <h3 className="text-sm font-semibold opacity-70">{t('journal.weekAvgMood')}</h3>
          <p className="text-2xl font-bold">{weekAvgMood}</p>
        </div>
      )}
    </>
  )

  return (
    <div className="mt-4">
      <div className="lg:grid lg:grid-cols-[1fr_280px] lg:gap-6">
        {/* Left column: main content */}
        <div className="space-y-6">
          <AlertBanner />

          {/* Write section */}
          <NoteForm onSubmit={handleCreate} loading={creating} />

          {/* Mobile: streak + stats inline */}
          <div className="lg:hidden space-y-3">
            {sidebarContent}
            <FeedbackWidget />
          </div>

          {/* Divider */}
          <hr className="border-white/10" />

          {/* Browse section */}
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-semibold">{showTrash ? t('journal.trash') : t('journal.recentNotes')}</h2>
              <button
                onClick={() => { setShowTrash(!showTrash); if (!showTrash) loadTrash() }}
                className={`text-xs px-2 py-1 rounded border transition-colors ${showTrash ? 'border-purple-500 text-purple-500' : 'border-[var(--card-border)] opacity-50 hover:opacity-100'}`}
              >
                {showTrash ? t('journal.recentNotes') : t('journal.trash')}
              </button>
            </div>
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

          {!showTrash && <SearchFilterPanel filters={filters} onFilterChange={handleFilterChange} />}

          {showTrash ? (
            <div>
              {trashLoading ? (
                <div className="space-y-3">{[1, 2].map((i) => <SkeletonCard key={i} />)}</div>
              ) : trashNotes.length === 0 ? (
                <EmptyState title={t('journal.trashEmpty')} description={t('journal.trashEmptyDesc')} />
              ) : (
                <div className="space-y-3">
                  {trashNotes.map((note) => (
                    <div key={note.id} className="glass-card p-4 opacity-70">
                      <p className="text-sm mb-2">{note.content_preview}</p>
                      <div className="flex items-center justify-between text-xs opacity-60">
                        <span>{t('journal.deletedAt')}: {new Date(note.created_at).toLocaleDateString()}</span>
                        <div className="flex gap-2">
                          <button onClick={() => handleRestore(note.id)} className="text-purple-500 hover:text-purple-400">{t('journal.restore')}</button>
                          <button onClick={() => handlePermanentDelete(note.id)} className="text-red-500 hover:text-red-400">{t('journal.permanentDelete')}</button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
          <div>
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => <SkeletonCard key={i} />)}
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
                    <div className="flex-1 min-w-0 relative" onContextMenu={(e) => handleContextMenu(e, note.id)}>
                      {note.is_pinned && (
                        <span className="absolute top-2 right-2 z-10 text-xs opacity-60" title={t('noteDetail.pin')}>📌</span>
                      )}
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
                  {t('journal.page', { page, total: Math.ceil(totalCount / 20) || 1 })}
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
          )}
        </div>

        {/* Right column: sidebar (desktop only) */}
        <aside className="hidden lg:block lg:sticky lg:top-24 lg:self-start space-y-4">
          {sidebarContent}
          <FeedbackWidget />
        </aside>
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

      <ConfirmModal
        open={!!deleteConfirmId}
        title={t('noteDetail.delete')}
        message={t('journal.deleteConfirm')}
        confirmText={t('noteDetail.delete')}
        cancelText={t('common.cancel')}
        onConfirm={() => handleDeleteNote(deleteConfirmId)}
        onCancel={() => setDeleteConfirmId(null)}
      />

      {/* Right-click context menu */}
      {contextMenu && (
        <div
          role="menu"
          className="fixed z-50 glass-card py-1 rounded-xl shadow-xl min-w-[160px] border border-white/10"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          onClick={(e) => e.stopPropagation()}
        >
          <button
            role="menuitem"
            tabIndex={0}
            className="w-full text-left px-4 py-2 text-sm hover:bg-white/10 transition-colors cursor-pointer focus:bg-white/10 outline-none"
            onClick={() => handleTogglePin(contextMenu.noteId)}
          >
            {notes.find((n) => n.id === contextMenu.noteId)?.is_pinned
              ? t('noteDetail.unpin')
              : t('noteDetail.pin')}
          </button>
          <button
            role="menuitem"
            tabIndex={0}
            className="w-full text-left px-4 py-2 text-sm text-red-500 hover:bg-white/10 transition-colors cursor-pointer focus:bg-white/10 outline-none"
            onClick={() => { setContextMenu(null); setDeleteConfirmId(contextMenu.noteId) }}
          >
            {t('noteDetail.delete')}
          </button>
        </div>
      )}
    </div>
  )
}
