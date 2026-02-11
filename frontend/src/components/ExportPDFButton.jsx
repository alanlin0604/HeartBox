import { useState } from 'react'
import { exportNotesPDF, exportNotesCSV } from '../api/notes'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'

export default function ExportPDFButton() {
  const { t, lang } = useLang()
  const toast = useToast()
  const [expanded, setExpanded] = useState(false)
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [loading, setLoading] = useState(false)
  const [format, setFormat] = useState('pdf')

  const handleExport = async () => {
    setLoading(true)
    try {
      if (format === 'csv') {
        const res = await exportNotesCSV()
        const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }))
        const a = document.createElement('a')
        a.href = url
        a.download = `heartbox_export.csv`
        document.body.appendChild(a)
        a.click()
        a.remove()
        window.URL.revokeObjectURL(url)
      } else {
        const res = await exportNotesPDF(dateFrom, dateTo, lang)
        const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
        const a = document.createElement('a')
        a.href = url
        a.download = `heartbox_${dateFrom || 'all'}_${dateTo || 'now'}.pdf`
        document.body.appendChild(a)
        a.click()
        a.remove()
        window.URL.revokeObjectURL(url)
      }
      setExpanded(false)
    } catch (err) {
      console.error('Export failed:', err)
      toast?.error(t('common.operationFailed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="relative inline-block">
      <button
        onClick={() => setExpanded(!expanded)}
        className="btn-primary text-sm px-4"
        aria-label="Export notes"
      >
        {t('export.button')}
      </button>

      {expanded && (
        <div className="absolute right-0 top-full mt-2 glass-card p-4 z-20 min-w-[280px] max-w-[90vw] space-y-3">
          <h3 className="text-sm font-semibold">{t('export.title')}</h3>
          <div>
            <label className="text-xs opacity-60 block mb-1">{t('export.format')}</label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              className="glass-input text-sm w-full"
            >
              <option value="pdf">PDF</option>
              <option value="csv">CSV</option>
            </select>
          </div>
          {format === 'pdf' && (
            <>
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
            </>
          )}
          <button
            onClick={handleExport}
            disabled={loading}
            className="btn-primary text-sm w-full disabled:opacity-50"
          >
            {loading ? t('export.exporting') : (format === 'csv' ? t('export.downloadCSV') : t('export.download'))}
          </button>
        </div>
      )}
    </div>
  )
}
