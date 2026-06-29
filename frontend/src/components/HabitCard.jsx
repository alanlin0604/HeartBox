import { useEffect, useState } from 'react'
import { useLang } from '../context/LanguageContext'
import { getHabitCalendar } from '../api/habits'

/**
 * Habit list card — completion stats, today's check-in toggle, optional note,
 * and an expandable 90-day heatmap fed by /habits/<id>/calendar/.
 *
 * Reads `habit.checked_today` from the serializer (added in this commit) so
 * the post-check-in state is correct on first render. Previously the card
 * looked at a non-existent `habit.last_check_in` field, leaving the button
 * stuck on "check in" even right after a successful check-in (the API would
 * then 400 on the duplicate).
 */
export default function HabitCard({ habit, onCheckIn, onUncheckIn, onEdit, onDelete }) {
  const { t } = useLang()
  const [busy, setBusy] = useState(false)
  const [showNote, setShowNote] = useState(false)
  const [note, setNote] = useState('')
  const [showCalendar, setShowCalendar] = useState(false)
  const [calendarLoading, setCalendarLoading] = useState(false)
  const [completedDates, setCompletedDates] = useState(null)

  const checked = !!habit.checked_today

  useEffect(() => {
    // Reset transient UI bits when the underlying habit changes (parent
    // refetched the list after a check-in / edit).
    setShowNote(false)
    setNote('')
  }, [habit.id, habit.checked_today])

  const loadCalendar = async () => {
    if (calendarLoading || completedDates) return
    setCalendarLoading(true)
    try {
      const res = await getHabitCalendar(habit.id)
      setCompletedDates(new Set(res.data?.completed_dates || []))
    } finally {
      setCalendarLoading(false)
    }
  }

  const handleCheckIn = async () => {
    if (busy || checked) return
    setBusy(true)
    try {
      await onCheckIn(habit.id, note.trim() || undefined)
      setShowNote(false)
      setNote('')
    } finally {
      setBusy(false)
    }
  }

  const handleUncheckIn = async () => {
    if (busy || !checked || !onUncheckIn) return
    setBusy(true)
    try {
      await onUncheckIn(habit.id)
    } finally {
      setBusy(false)
    }
  }

  const toggleCalendar = () => {
    const next = !showCalendar
    setShowCalendar(next)
    if (next) loadCalendar()
  }

  return (
    <div className="glass-card p-6 hover:shadow-lg transition-shadow duration-300">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl overflow-hidden"
            style={{ backgroundColor: `${habit.color}20`, color: habit.color }}
          >
            {habit.icon?.startsWith('/')
              ? <img src={habit.icon} alt="" aria-hidden="true" className="w-8 h-8 object-contain" />
              : (habit.icon || '✓')}
          </div>
          <div>
            <h3 className="font-semibold text-lg text-[var(--text-primary)]">
              {habit.name}
            </h3>
            {habit.category && (
              <span className="text-xs text-[var(--text-secondary)]">
                {habit.category}
              </span>
            )}
          </div>
        </div>

        <div className="flex space-x-1">
          <button
            onClick={() => onEdit(habit)}
            className="p-2 hover:bg-orange-500/10 rounded-lg transition-colors"
            aria-label={t('common.edit')}
          >
            <svg className="w-4 h-4 text-[var(--text-secondary)]" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
            </svg>
          </button>
          <button
            onClick={() => onDelete(habit.id)}
            className="p-2 hover:bg-red-500/10 rounded-lg transition-colors"
            aria-label={t('common.delete')}
          >
            <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        </div>
      </div>

      {/* Description */}
      {habit.description && (
        <p className="text-sm text-[var(--text-secondary)] mb-4 line-clamp-2">
          {habit.description}
        </p>
      )}

      {/* Stats */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <span className="text-2xl">🔥</span>
          <div>
            <div className="text-2xl font-bold text-[var(--text-primary)]">{habit.streak || 0}</div>
            <div className="text-xs text-[var(--text-secondary)]">{t('habit.streak')}</div>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-orange-400">{Math.round(habit.completion_rate || 0)}%</div>
          <div className="text-xs text-[var(--text-secondary)]">{t('habit.completionRate')}</div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="h-2 bg-[var(--card-bg)] rounded-full mb-4 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-orange-500 to-rose-500 rounded-full transition-all duration-1000"
          style={{ width: `${habit.completion_rate || 0}%` }}
        />
      </div>

      {/* Optional note input — only when checking in fresh today */}
      {!checked && showNote && (
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value.slice(0, 280))}
          placeholder={t('habit.notePlaceholder') || 'Add a quick note (optional)...'}
          aria-label={t('habit.addNote') || 'Add a note'}
          rows={2}
          maxLength={280}
          className="w-full mb-3 px-3 py-2 text-sm rounded-lg bg-white/5 border border-white/10 focus:border-orange-500/60 focus:outline-none resize-none"
        />
      )}

      {/* Check-in button: 3 states — fresh today / already checked / loading */}
      {checked ? (
        <div className="flex gap-2">
          <button
            disabled
            className="flex-1 py-3 rounded-xl font-medium bg-green-500/20 text-green-400 cursor-default flex items-center justify-center space-x-2"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
            </svg>
            <span>{t('habit.checked')}</span>
          </button>
          {onUncheckIn && (
            <button
              onClick={handleUncheckIn}
              disabled={busy}
              className="px-3 py-3 rounded-xl text-sm bg-white/5 hover:bg-white/10 text-[var(--text-secondary)] disabled:opacity-50"
              aria-label={t('habit.undoCheckIn') || 'Undo check-in'}
              title={t('habit.undoCheckIn') || 'Undo check-in'}
            >
              ↶
            </button>
          )}
        </div>
      ) : (
        <div className="flex gap-2">
          <button
            onClick={handleCheckIn}
            disabled={busy}
            className="flex-1 py-3 rounded-xl font-medium bg-orange-500 hover:bg-orange-600 text-white transition-all duration-300 flex items-center justify-center space-x-2 disabled:opacity-50"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{busy ? t('common.loading') : t('habit.checkIn')}</span>
          </button>
          <button
            onClick={() => setShowNote((v) => !v)}
            className="px-3 py-3 rounded-xl bg-white/5 hover:bg-white/10 text-[var(--text-secondary)]"
            aria-label={t('habit.addNote') || 'Add note'}
            title={t('habit.addNote') || 'Add note'}
          >
            ✎
          </button>
        </div>
      )}

      {/* Calendar heatmap toggle */}
      <button
        onClick={toggleCalendar}
        className="mt-4 w-full text-xs text-[var(--text-secondary)] hover:text-orange-400 transition-colors flex items-center justify-center gap-1"
      >
        <span>{showCalendar ? '▾' : '▸'}</span>
        <span>{showCalendar ? (t('habit.hideCalendar') || 'Hide history') : (t('habit.showCalendar') || 'Show 90-day history')}</span>
      </button>
      {showCalendar && (
        <div className="mt-3 p-3 rounded-lg bg-white/5">
          {calendarLoading && !completedDates ? (
            <div className="text-xs text-center text-[var(--text-secondary)]">{t('common.loading')}</div>
          ) : (
            <>
              {/* One-line title so the dot grid isn't just floating dots */}
              <div className="text-xs text-[var(--text-secondary)] mb-2">
                {t('habit.heatmapTitle')}
              </div>
              <CalendarHeatmap completedDates={completedDates} color={habit.color} />
              {/* Legend: 已完成 vs 未完成 swatches + count summary */}
              <div className="mt-3 flex items-center justify-between text-xs text-[var(--text-secondary)]">
                <div className="flex items-center gap-3">
                  <span className="inline-flex items-center gap-1.5">
                    <span
                      className="inline-block w-3 h-3 rounded-sm"
                      style={{ backgroundColor: habit.color }}
                    />
                    {t('habit.heatmapLegendDone')}
                  </span>
                  <span className="inline-flex items-center gap-1.5">
                    <span className="inline-block w-3 h-3 rounded-sm bg-white/10" />
                    {t('habit.heatmapLegendMissed')}
                  </span>
                </div>
                <span>
                  {t('habit.heatmapCount', { count: completedDates?.size ?? 0 })}
                </span>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * Compact 90-day heatmap. 13 weeks × 7 days, oldest top-left, today bottom-right.
 * Filled cells use the habit's accent color; empty cells are a faint slate.
 */
function CalendarHeatmap({ completedDates, color = '#F97316' }) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const startOfRange = new Date(today)
  startOfRange.setDate(today.getDate() - 89)

  // Build grid: column = week, row = day-of-week (Mon = 0). 13 columns covers 91 days.
  const cells = []
  for (let i = 0; i < 90; i++) {
    const d = new Date(startOfRange)
    d.setDate(startOfRange.getDate() + i)
    const iso = d.toISOString().split('T')[0]
    const isFilled = completedDates ? completedDates.has(iso) : false
    cells.push({ iso, filled: isFilled, day: d })
  }

  return (
    <div className="flex gap-[2px]">
      {Array.from({ length: 13 }, (_, w) => (
        <div key={w} className="flex flex-col gap-[2px]">
          {Array.from({ length: 7 }, (_, d) => {
            const idx = w * 7 + d
            const cell = cells[idx]
            if (!cell) return <div key={d} className="w-3 h-3" />
            return (
              <div
                key={d}
                className="w-3 h-3 rounded-sm transition-colors"
                style={{
                  backgroundColor: cell.filled ? color : 'rgba(255,255,255,0.07)',
                }}
                title={`${cell.iso}${cell.filled ? ' ✓' : ''}`}
              />
            )
          })}
        </div>
      ))}
    </div>
  )
}
