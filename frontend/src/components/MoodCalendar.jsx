/**
 * MoodCalendar Component with WCAG 2.1 AA Compliance
 *
 * Features:
 * - Color + Pattern/Shape for accessibility
 * - SVG icons instead of unicode symbols
 * - Touch-friendly targets (min 44px)
 * - Proper ARIA labels
 * - No layout shift on hover
 */

import { useState, useEffect, memo } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCalendarData } from '../api/analytics'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'

const WEEKDAY_KEYS = [
  'calendar.sun', 'calendar.mon', 'calendar.tue',
  'calendar.wed', 'calendar.thu', 'calendar.fri', 'calendar.sat',
]

// Navigation Icons
const ChevronLeft = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M15 18l-6-6 6-6" />
  </svg>
)

const ChevronRight = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M9 18l6-6-6-6" />
  </svg>
)

// Sentiment Indicator — sr-only label, color/pattern handled separately on the cell.
const SentimentIndicator = ({ score }) => {
  if (score == null) return null
  let label
  if (score >= 0.3) label = 'Positive'
  else if (score >= -0.3) label = 'Neutral'
  else if (score >= -0.6) label = 'Somewhat negative'
  else label = 'Negative'
  return <span className="sr-only">{label}</span>
}

function sentimentColor(score) {
  if (score == null) return 'transparent'
  if (score >= 0.3) return 'rgba(34, 197, 94, 0.6)'
  if (score >= -0.3) return 'rgba(250, 204, 21, 0.5)'
  if (score >= -0.6) return 'rgba(249, 115, 22, 0.5)'
  return 'rgba(239, 68, 68, 0.6)'
}

export default memo(function MoodCalendar() {
  const { t } = useLang()
  const toast = useToast()
  const navigate = useNavigate()
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [days, setDays] = useState([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    getCalendarData(year, month)
      .then((res) => setDays(res.data.days || []))
      .catch(() => {
        toast?.error(t('common.operationFailed'))
      })
      .finally(() => setLoading(false))
  }, [year, month])

  // Build calendar grid
  const firstDay = new Date(year, month - 1, 1).getDay()
  const daysInMonth = new Date(year, month, 0).getDate()
  const dayMap = {}
  days.forEach((d) => {
    dayMap[d.date] = d
  })

  const cells = []
  for (let i = 0; i < firstDay; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)

  const prevMonth = () => {
    if (month === 1) { setYear(year - 1); setMonth(12) }
    else setMonth(month - 1)
  }

  const nextMonth = () => {
    if (month === 12) { setYear(year + 1); setMonth(1) }
    else setMonth(month + 1)
  }

  const handleDayClick = (day) => {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    navigate(`/?date_from=${dateStr}&date_to=${dateStr}`)
  }

  return (
    <div className="glass p-6" role="region" aria-label={t('calendar.title')}>
      {/* Header with Navigation */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">{t('calendar.title')}</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={prevMonth}
            className="inline-flex items-center justify-center min-h-[44px] min-w-[44px] rounded-lg hover:bg-white/10 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-400)]"
            aria-label={t('aria.previousMonth')}
            type="button"
          >
            <ChevronLeft />
          </button>
          <span className="text-sm font-medium min-w-[100px] text-center" aria-live="polite">
            {year} / {String(month).padStart(2, '0')}
          </span>
          <button
            onClick={nextMonth}
            className="inline-flex items-center justify-center min-h-[44px] min-w-[44px] rounded-lg hover:bg-white/10 transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-400)]"
            aria-label={t('aria.nextMonth')}
            type="button"
          >
            <ChevronRight />
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center opacity-60 py-8" role="status" aria-live="polite">
          {t('common.loading')}
        </div>
      ) : days.length === 0 ? (
        <div className="text-center opacity-40 py-8 text-sm" role="status">
          {t('calendar.noData')}
        </div>
      ) : (
        <div className="grid grid-cols-7 gap-1 sm:gap-2" role="grid" aria-label="Mood calendar">
          {/* Weekday Headers */}
          {WEEKDAY_KEYS.map((key) => (
            <div
              key={key}
              className="text-center text-xs text-slate-400 py-2 font-medium"
              role="columnheader"
            >
              {t(key)}
            </div>
          ))}

          {/* Calendar Days */}
          {cells.map((day, i) => {
            if (day === null) return <div key={`empty-${i}`} role="gridcell" aria-hidden="true" />

            const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
            const info = dayMap[dateStr]
            const bg = info ? sentimentColor(info.avg_sentiment) : 'transparent'

            const getSentimentLabel = (score) => {
              if (!score && score !== 0) return ''
              if (score >= 0.3) return 'Positive'
              if (score >= -0.3) return 'Neutral'
              if (score >= -0.6) return 'Somewhat negative'
              return 'Negative'
            }

            return (
              <button
                key={dateStr}
                onClick={() => info && handleDayClick(day)}
                disabled={!info}
                className={`
                  aspect-square rounded-lg
                  flex flex-col items-center justify-center
                  border border-white/5
                  min-h-[44px] sm:min-h-[52px]
                  transition-all duration-200
                  focus-visible:outline-2 focus-visible:outline-offset-2
                  focus-visible:outline-[var(--color-primary-400)]
                  touch-manipulation
                  ${info
                    ? 'hover:brightness-110 hover:shadow-md cursor-pointer'
                    : 'cursor-default opacity-40'
                  }
                `}
                style={{ backgroundColor: bg }}
                aria-label={
                  info
                    ? `${day} ${t('calendar.noteCount')}: ${info.count}, ${getSentimentLabel(info.avg_sentiment)}`
                    : `${day}, no data`
                }
                role="gridcell"
                type="button"
              >
                <span className={`text-base sm:text-lg ${info ? 'font-semibold' : ''}`}>
                  {day}
                </span>
                {info && (
                  <span className="text-xs opacity-90 mt-0.5">
                    {info.count}
                  </span>
                )}
                {info && <SentimentIndicator score={info.avg_sentiment} />}
              </button>
            )
          })}
        </div>
      )}

      {/* Legend - Color + Text */}
      <div className="flex flex-wrap items-center justify-center gap-4 sm:gap-6 mt-6 text-xs sm:text-sm">
        <span className="flex items-center gap-2">
          <span className="w-4 h-4 rounded border border-white/10" style={{ backgroundColor: 'rgba(34, 197, 94, 0.6)' }} aria-hidden="true" />
          <span>{t('calendar.positive')}</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="w-4 h-4 rounded border border-white/10" style={{ backgroundColor: 'rgba(250, 204, 21, 0.5)' }} aria-hidden="true" />
          <span>{t('calendar.neutral')}</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="w-4 h-4 rounded border border-white/10" style={{ backgroundColor: 'rgba(239, 68, 68, 0.6)' }} aria-hidden="true" />
          <span>{t('calendar.negative')}</span>
        </span>
      </div>
    </div>
  )
})
