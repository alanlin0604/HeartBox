import { useState, useEffect, memo } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCalendarData } from '../api/analytics'
import { useLang } from '../context/LanguageContext'

const WEEKDAY_KEYS = [
  'calendar.sun', 'calendar.mon', 'calendar.tue',
  'calendar.wed', 'calendar.thu', 'calendar.fri', 'calendar.sat',
]

function sentimentColor(score) {
  if (score == null) return 'transparent'
  if (score >= 0.3) return 'rgba(34, 197, 94, 0.6)'   // green — positive
  if (score >= -0.3) return 'rgba(250, 204, 21, 0.5)'  // yellow — neutral
  if (score >= -0.6) return 'rgba(249, 115, 22, 0.5)'  // orange — somewhat negative
  return 'rgba(239, 68, 68, 0.6)'                       // red — negative
}

export default memo(function MoodCalendar() {
  const { t } = useLang()
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
      .catch(console.error)
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
    <div className="glass p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">{t('calendar.title')}</h2>
        <div className="flex items-center gap-2">
          <button onClick={prevMonth} className="btn-primary text-sm px-2 py-1">◀</button>
          <span className="text-sm font-medium min-w-[100px] text-center">
            {year} / {String(month).padStart(2, '0')}
          </span>
          <button onClick={nextMonth} className="btn-primary text-sm px-2 py-1">▶</button>
        </div>
      </div>

      {loading ? (
        <div className="text-center opacity-60 py-8">{t('common.loading')}</div>
      ) : (
        <div className="grid grid-cols-7 gap-1">
          {WEEKDAY_KEYS.map((key) => (
            <div key={key} className="text-center text-xs opacity-50 py-1">
              {t(key)}
            </div>
          ))}
          {cells.map((day, i) => {
            if (day === null) return <div key={`empty-${i}`} />
            const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
            const info = dayMap[dateStr]
            const bg = info ? sentimentColor(info.avg_sentiment) : 'transparent'
            return (
              <button
                key={dateStr}
                onClick={() => info && handleDayClick(day)}
                className="aspect-square rounded-lg flex flex-col items-center justify-center transition-all hover:scale-105 border border-white/5"
                style={{ backgroundColor: bg }}
                title={info ? `${t('calendar.avgSentiment')}: ${info.avg_sentiment}, ${t('calendar.noteCount')}: ${info.count}` : ''}
              >
                <span className={`text-lg ${info ? 'font-bold' : 'opacity-40'}`}>{day}</span>
                {info && <span className="text-xs opacity-80">{info.count} {t('calendar.noteCount')}</span>}
              </button>
            )
          })}
        </div>
      )}

      {/* Legend */}
      <div className="flex items-center justify-center gap-5 mt-4 text-sm opacity-80">
        <span className="flex items-center gap-1.5">
          <span className="w-4 h-4 rounded" style={{ backgroundColor: 'rgba(34, 197, 94, 0.6)' }} />
          {t('calendar.positive')}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-4 h-4 rounded" style={{ backgroundColor: 'rgba(250, 204, 21, 0.5)' }} />
          {t('calendar.neutral')}
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-4 h-4 rounded" style={{ backgroundColor: 'rgba(239, 68, 68, 0.6)' }} />
          {t('calendar.negative')}
        </span>
      </div>
    </div>
  )
})
