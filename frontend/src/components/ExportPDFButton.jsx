import { useState, useRef, useEffect } from 'react'
import { exportNotesPDF, exportNotesCSV } from '../api/notes'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'

export default function ExportPDFButton() {
  const { t, lang } = useLang()
  const toast = useToast()
  const [expanded, setExpanded] = useState(false)
  const panelRef = useRef(null)

  useEffect(() => {
    if (!expanded) return
    const handleClickOutside = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        setExpanded(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [expanded])
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

  const panelContent = (
    <div className="popup-panel p-4 space-y-3 w-full">
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
  )

  return (
    <div className="relative inline-block" ref={panelRef}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="btn-primary text-sm px-4"
        aria-label="Export notes"
      >
        {t('export.button')}
      </button>

      {/* Desktop: dropdown */}
      {expanded && (
        <div className="hidden sm:block absolute right-0 top-full mt-2 z-20 w-[280px]">
          {panelContent}
        </div>
      )}

      {/* Mobile: fixed centered modal */}
      {expanded && (
        <div
          className="sm:hidden fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-6"
          onClick={() => setExpanded(false)}
        >
          <div className="w-full max-w-xs" onClick={(e) => e.stopPropagation()}>
            {panelContent}
          </div>
        </div>
      )}
    </div>
  )
}
