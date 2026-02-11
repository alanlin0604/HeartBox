import { useState } from 'react'
import { exportNotesPDF } from '../api/notes'
import { useLang } from '../context/LanguageContext'

export default function ExportPDFButton() {
  const { t, lang } = useLang()
  const [expanded, setExpanded] = useState(false)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [loading, setLoading] = useState(false)

  const handleExport = async () => {
    setLoading(true)
    try {
      const res = await exportNotesPDF(dateFrom, dateTo, lang)
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const a = document.createElement('a')
      a.href = url
      a.download = `heartbox_${dateFrom || 'all'}_${dateTo || 'now'}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      setExpanded(false)
    } catch (err) {
      console.error('PDF export failed:', err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setExpanded(!expanded)}
        className="btn-primary text-sm px-4"
      >
        {t('export.button')}
      </button>

      {expanded && (
        <div className="absolute right-0 top-full mt-2 glass-card p-4 z-20 min-w-[280px] space-y-3">
          <h3 className="text-sm font-semibold">{t('export.title')}</h3>
          <div>
            <label className="text-xs opacity-60 block mb-1">{t('export.from')}</label>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="glass-input text-sm w-full"
            />
          </div>
          <div>
            <label className="text-xs opacity-60 block mb-1">{t('export.to')}</label>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="glass-input text-sm w-full"
            />
          </div>
          <button
            onClick={handleExport}
            disabled={loading}
            className="btn-primary text-sm w-full disabled:opacity-50"
          >
            {loading ? t('export.exporting') : t('export.download')}
          </button>
        </div>
      )}
    </div>
  )
}
