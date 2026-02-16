import { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { getYearPixels } from '../api/wellness'
import { useLang } from '../context/LanguageContext'

const MONTH_KEYS = [
  'months.jan', 'months.feb', 'months.mar', 'months.apr',
  'months.may', 'months.jun', 'months.jul', 'months.aug',
  'months.sep', 'months.oct', 'months.nov', 'months.dec',
]

function getSentimentColor(score) {
  if (score == null) return 'bg-gray-500/20'
  if (score > 0.5) return 'bg-green-500'
  if (score > 0.2) return 'bg-green-400/70'
  if (score > -0.2) return 'bg-yellow-400/70'
  if (score > -0.5) return 'bg-orange-400/70'
  return 'bg-red-500/80'
}

export default function YearInPixels() {
  const { t } = useLang()
  const navigate = useNavigate()
  const [year, setYear] = useState(new Date().getFullYear())
  const [pixels, setPixels] = useState({})
  const [loading, setLoading] = useState(true)
  const [hovered, setHovered] = useState(null)

  useEffect(() => {
    setLoading(true)
    getYearPixels(year)
      .then((res) => setPixels(res.data.pixels || {}))
      .catch(() => setPixels({}))
      .finally(() => setLoading(false))
  }, [year])

  const grid = useMemo(() => {
    const rows = []
    for (let m = 0; m < 12; m++) {
      const days = []
      const daysInMonth = new Date(year, m + 1, 0).getDate()
      for (let d = 1; d <= 31; d++) {
        if (d > daysInMonth) {
          days.push({ date: null, score: null })
        } else {
          const dateStr = `${year}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
          days.push({ date: dateStr, score: pixels[dateStr] ?? null })
        }
      }
      rows.push({ monthKey: MONTH_KEYS[m], days })
    }
    return rows
  }, [year, pixels])

  const handleClick = (dateStr) => {
    if (dateStr && pixels[dateStr] != null) {
      navigate(`/?date_from=${dateStr}&date_to=${dateStr}`)
    }
  }

  return (
    <div className="glass p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">{t('dashboard.yearInPixels')}</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setYear(year - 1)}
            className="text-sm opacity-60 hover:opacity-100 px-2 py-1 rounded border border-[var(--card-border)]"
          >
            &larr;
          </button>
          <span className="text-sm font-medium">{year}</span>
          <button
            onClick={() => setYear(year + 1)}
            disabled={year >= new Date().getFullYear()}
            className="text-sm opacity-60 hover:opacity-100 px-2 py-1 rounded border border-[var(--card-border)] disabled:opacity-20"
          >
            &rarr;
          </button>
        </div>
      </div>

      {loading ? (
        <div className="h-48 flex items-center justify-center opacity-40">{t('common.loading')}</div>
      ) : (
        <>
          <div className="overflow-x-auto">
            <div className="min-w-[680px]">
              {/* Day numbers header */}
              <div className="flex items-center gap-px mb-1">
                <div className="w-8 text-xs opacity-40" />
                {Array.from({ length: 31 }, (_, i) => (
                  <div key={i} className="w-3.5 h-3.5 flex items-center justify-center text-[8px] opacity-30">
                    {(i + 1) % 5 === 0 ? i + 1 : ''}
                  </div>
                ))}
              </div>
              {grid.map((row) => (
                <div key={row.monthKey} className="flex items-center gap-px mb-px">
                  <div className="w-8 text-xs opacity-50 text-right pr-1">{t(row.monthKey)}</div>
                  {row.days.map((cell, idx) => (
                    <div
                      key={idx}
                      className={`w-3.5 h-3.5 rounded-[2px] transition-all ${
                        cell.date ? `${getSentimentColor(cell.score)} cursor-pointer hover:ring-1 hover:ring-purple-400` : ''
                      }`}
                      onMouseEnter={() => cell.date && setHovered(cell)}
                      onMouseLeave={() => setHovered(null)}
                      onClick={() => handleClick(cell.date)}
                    />
                  ))}
                </div>
              ))}
            </div>
          </div>

          {/* Tooltip */}
          {hovered && (
            <div className="mt-2 text-xs opacity-60">
              {hovered.date}: {hovered.score != null ? `${t('dashboard.avgSentiment')} ${hovered.score}` : t('dashboard.noData')}
            </div>
          )}

          {/* Legend */}
          <div className="flex items-center gap-2 mt-3 text-xs opacity-50">
            <span>{t('dashboard.negative')}</span>
            <div className="w-3.5 h-3.5 rounded-[2px] bg-red-500/80" />
            <div className="w-3.5 h-3.5 rounded-[2px] bg-orange-400/70" />
            <div className="w-3.5 h-3.5 rounded-[2px] bg-yellow-400/70" />
            <div className="w-3.5 h-3.5 rounded-[2px] bg-green-400/70" />
            <div className="w-3.5 h-3.5 rounded-[2px] bg-green-500" />
            <span>{t('dashboard.positive')}</span>
            <div className="w-3.5 h-3.5 rounded-[2px] bg-gray-500/20 ml-2" />
            <span>{t('dashboard.noData')}</span>
          </div>
        </>
      )}
    </div>
  )
}
