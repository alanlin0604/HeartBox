import { useState, useEffect } from 'react'
import { getWeeklySummary, getWeeklySummaryList, exportWeeklySummaryPDF } from '../api/wellness'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'
import LoadingSpinner from '../components/LoadingSpinner'

function getMonday(date) {
  const d = new Date(date)
  const day = d.getDay()
  const diff = d.getDate() - day + (day === 0 ? -6 : 1)
  d.setDate(diff)
  return d.toISOString().slice(0, 10)
}

function dateToWeekInput(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  // ISO week number: find Thursday of the week, then calculate week number
  const thu = new Date(d)
  thu.setDate(d.getDate() + (4 - ((d.getDay() + 6) % 7 + 1)))
  const yearStart = new Date(thu.getFullYear(), 0, 1)
  const weekNum = Math.ceil(((thu - yearStart) / 86400000 + 1) / 7)
  return `${thu.getFullYear()}-W${String(weekNum).padStart(2, '0')}`
}

function weekInputToDate(weekStr) {
  // "YYYY-Wnn" → Monday date string
  const [yearStr, weekPart] = weekStr.split('-W')
  const year = Number(yearStr)
  const week = Number(weekPart)
  // Jan 4 is always in ISO week 1
  const jan4 = new Date(year, 0, 4)
  const dayOfWeek = jan4.getDay() || 7 // Monday=1 ... Sunday=7
  // Monday of week 1
  const week1Monday = new Date(jan4)
  week1Monday.setDate(jan4.getDate() - dayOfWeek + 1)
  // Monday of the target week
  const target = new Date(week1Monday)
  target.setDate(week1Monday.getDate() + (week - 1) * 7)
  return target.toISOString().slice(0, 10)
}

export default function WeeklySummaryPage() {
  const { t } = useLang()
  const toast = useToast()
  const [summaries, setSummaries] = useState([])
  const [selectedWeek, setSelectedWeek] = useState(getMonday(new Date()))
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(false)
  const [listLoading, setListLoading] = useState(true)

  useEffect(() => { document.title = `${t('nav.weeklySummary')} — ${t('app.name')}` }, [t])

  useEffect(() => {
    setListLoading(true)
    getWeeklySummaryList()
      .then((res) => setSummaries(res.data?.results || res.data || []))
      .catch(() => setSummaries([]))
      .finally(() => setListLoading(false))
  }, [])

  const handleGenerate = async () => {
    setLoading(true)
    setDetail(null)
    try {
      const { data } = await getWeeklySummary(selectedWeek)
      setDetail(data)
      // Add to list if not present
      setSummaries((prev) => {
        if (prev.find((s) => s.week_start === data.week_start)) return prev
        return [data, ...prev]
      })
    } catch (err) {
      if (err.response?.status === 404) {
        toast?.error(t('weeklySummary.noNotes'))
      } else {
        toast?.error(t('common.operationFailed'))
      }
    } finally {
      setLoading(false)
    }
  }

  const handleViewSummary = async (weekStart) => {
    setSelectedWeek(weekStart)
    setLoading(true)
    try {
      const { data } = await getWeeklySummary(weekStart)
      setDetail(data)
    } catch {
      toast?.error(t('common.operationFailed'))
    } finally {
      setLoading(false)
    }
  }

  const weekInputValue = dateToWeekInput(selectedWeek)
  const currentWeekValue = dateToWeekInput(getMonday(new Date()))

  return (
    <div className="space-y-6 mt-4 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold">{t('nav.weeklySummary')}</h1>

      {/* Generate new */}
      <div className="glass p-4 flex flex-wrap items-center gap-3">
        <input
          type="week"
          value={weekInputValue}
          onChange={(e) => {
            if (e.target.value) {
              setSelectedWeek(weekInputToDate(e.target.value))
            }
          }}
          max={currentWeekValue}
          className="glass-input w-auto"
        />
        <button onClick={handleGenerate} disabled={loading} className="btn-primary text-sm">
          {loading ? t('common.loading') : t('weeklySummary.generate')}
        </button>
      </div>

      {/* Detail view */}
      {detail && (
        <div className="glass p-6 space-y-4">
          <h2 className="text-lg font-semibold">
            {t('weeklySummary.weekOf', { date: detail.week_start })}
          </h2>
          <div className="grid grid-cols-3 gap-4">
            <div className="glass-card p-3 text-center">
              <p className="text-xs opacity-60">{t('weeklySummary.noteCount')}</p>
              <p className="text-2xl font-bold">{detail.note_count}</p>
            </div>
            <div className="glass-card p-3 text-center">
              <p className="text-xs opacity-60">{t('weeklySummary.avgMood')}</p>
              <p className="text-2xl font-bold">{detail.mood_avg ?? '-'}</p>
            </div>
            <div className="glass-card p-3 text-center">
              <p className="text-xs opacity-60">{t('weeklySummary.avgStress')}</p>
              <p className="text-2xl font-bold">{detail.stress_avg ?? '-'}</p>
            </div>
          </div>

          {detail.top_activities?.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold opacity-60 mb-2">{t('weeklySummary.topActivities')}</h3>
              <div className="flex flex-wrap gap-2">
                {detail.top_activities.map((act) => {
                  const label = t(`activities.${act.name}`) !== `activities.${act.name}` ? t(`activities.${act.name}`) : act.name
                  return (
                    <span key={act.name} className="text-xs px-3 py-1 rounded-full bg-purple-500/15 text-purple-400 border border-purple-500/20">
                      {label} ({act.count})
                    </span>
                  )
                })}
              </div>
            </div>
          )}

          {detail.ai_summary && (
            <div className="glass-card p-4 border-l-4 border-purple-500/50">
              <h3 className="text-sm font-semibold text-purple-400 mb-2">{t('weeklySummary.aiSummary')}</h3>
              <p className="text-sm leading-relaxed whitespace-pre-wrap opacity-80">{detail.ai_summary}</p>
            </div>
          )}

          <button
            onClick={async () => {
              try {
                const res = await exportWeeklySummaryPDF(detail.week_start)
                const url = URL.createObjectURL(res.data)
                const a = document.createElement('a')
                a.href = url
                a.download = `weekly_summary_${detail.week_start}.pdf`
                a.click()
                URL.revokeObjectURL(url)
              } catch {
                toast?.error(t('common.operationFailed'))
              }
            }}
            className="btn-secondary text-sm"
          >
            {t('weeklySummary.exportPDF') || 'Export PDF'}
          </button>
        </div>
      )}

      {/* History list */}
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('weeklySummary.history')}</h2>
        {listLoading ? <LoadingSpinner /> : summaries.length === 0 ? (
          <p className="text-sm opacity-60">{t('weeklySummary.noHistory')}</p>
        ) : (
          <div className="space-y-2">
            {summaries.map((s) => (
              <button
                key={s.id}
                onClick={() => handleViewSummary(s.week_start)}
                className="w-full glass-card p-3 flex items-center justify-between text-sm hover:bg-purple-500/10 transition-colors cursor-pointer"
              >
                <span>{t('weeklySummary.weekOf', { date: s.week_start })}</span>
                <span className="opacity-60">{s.note_count} {t('weeklySummary.notes')}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
