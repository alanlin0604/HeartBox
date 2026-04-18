import { useState, useRef } from 'react'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'
import { importCSV } from '../api/notes'
import { invalidate } from '../api/cache'

export default function ImportModal({ onClose, onSuccess }) {
  const { t } = useLang()
  const toast = useToast()
  const fileRef = useRef(null)
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState([])
  const [importing, setImporting] = useState(false)

  const handleFileChange = (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)

    const reader = new FileReader()
    reader.onload = (ev) => {
      const text = ev.target.result
      const lines = text.split('\n').slice(0, 6) // Header + 5 rows
      setPreview(lines.map(l => l.split(',')))
    }
    reader.readAsText(f)
  }

  const handleImport = async () => {
    if (!file) return
    setImporting(true)
    try {
      const result = await importCSV(file)
      invalidate('analytics')
      invalidate('calendar')
      toast?.success(t('import.success').replace('{count}', result.data.imported))
      onSuccess?.()
      onClose()
    } catch {
      toast?.error(t('import.failed'))
    } finally {
      setImporting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="popup-panel p-6 w-full max-w-lg space-y-4" role="dialog" aria-modal="true">
        <h2 className="text-lg font-semibold">{t('import.title')}</h2>
        <p className="text-sm text-slate-400">{t('import.desc')}</p>
        <p className="text-xs text-slate-400">{t('import.format')}</p>

        <input
          ref={fileRef}
          type="file"
          accept=".csv"
          onChange={handleFileChange}
          className="glass-input"
        />

        {preview.length > 0 && (
          <div className="overflow-x-auto">
            <table className="text-xs w-full">
              <tbody>
                {preview.map((row, i) => (
                  <tr key={i} className={i === 0 ? 'font-bold text-slate-400' : 'text-slate-400'}>
                    {row.map((cell, j) => (
                      <td key={j} className="px-2 py-1 border border-[var(--card-border)] truncate max-w-[120px]">{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="btn-secondary">{t('common.cancel')}</button>
          <button onClick={handleImport} disabled={!file || importing} className="btn-primary">
            {importing ? t('import.importing') : t('import.button')}
          </button>
        </div>
      </div>
    </div>
  )
}
