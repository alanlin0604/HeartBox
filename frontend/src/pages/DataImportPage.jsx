import { useEffect, useRef, useState } from 'react'
import { useLang } from '../context/LanguageContext'
import { importAPI } from '../api/import'

const ACCEPT = '.csv,.json'

export default function DataImportPage() {
  const { t } = useLang()
  const [step, setStep] = useState(1) // 1: upload, 2: mapping, 3: result
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [mapping, setMapping] = useState({})
  const [result, setResult] = useState(null)
  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const pollRef = useRef(null)

  // Poll an in-flight async import every second until done/failed.
  useEffect(() => {
    if (!job || job.status === 'done' || job.status === 'failed') {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
      return
    }
    pollRef.current = setInterval(async () => {
      try {
        const next = await importAPI.getJobStatus(job.job_id)
        setJob(next)
        if (next.status === 'done') {
          setResult({
            imported: next.imported_count,
            errors: next.errors || [],
            total: next.total_rows,
          })
          setStep(3)
        } else if (next.status === 'failed') {
          setError(next.error_message || t('import.errorImport'))
        }
      } catch {
        /* transient failure — keep polling */
      }
    }, 1000)
    return () => clearInterval(pollRef.current)
  }, [job, t])

  async function handleFileSelect(e) {
    const selectedFile = e.target.files?.[0]
    if (!selectedFile) return
    const ext = selectedFile.name.toLowerCase()
    if (!(ext.endsWith('.csv') || ext.endsWith('.json'))) {
      setError(t('import.errorInvalidFormat'))
      return
    }
    setFile(selectedFile)
    setError(null)
    try {
      setLoading(true)
      const previewData = await importAPI.previewFile(selectedFile)
      setPreview(previewData)
      setMapping(previewData.suggested_mapping || {})
      setStep(2)
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.message || t('import.errorPreview'))
    } finally {
      setLoading(false)
    }
  }

  async function handleConfirmImport() {
    try {
      setLoading(true)
      setError(null)
      const res = await importAPI.importFile(file, mapping)
      if (res.mode === 'sync') {
        setResult({ imported: res.imported, errors: res.errors || [], total: res.total_rows })
        setStep(3)
      } else {
        setJob(res)
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.response?.data?.message || t('import.errorImport'))
    } finally {
      setLoading(false)
    }
  }

  function handleReset() {
    setStep(1)
    setFile(null)
    setPreview(null)
    setMapping({})
    setResult(null)
    setJob(null)
    setError(null)
  }

  const fmtLabel = preview?.format === 'json' ? 'JSON' : 'CSV'
  const willGoAsync = preview && preview.total_rows > (preview.sync_limit || 500)
  const totalSteps = 3

  return (
    <div className="min-h-screen p-6 max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-rose-400 mb-8">
        {t('import.title')}
      </h1>

      {/* Step indicator */}
      <div className="flex items-center justify-center mb-8">
        {Array.from({ length: totalSteps }, (_, i) => i + 1).map((s) => (
          <div key={s} className="flex items-center">
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold ${
                step >= s ? 'bg-orange-500 text-white' : 'bg-white/10 text-slate-400'
              }`}
            >
              {s}
            </div>
            {s < totalSteps && (
              <div className={`w-16 h-1 mx-2 ${step > s ? 'bg-orange-500' : 'bg-white/10'}`} />
            )}
          </div>
        ))}
      </div>

      {error && (
        <div className="glass p-4 mb-6 border border-red-400/50 bg-red-500/10">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      )}

      {/* Step 1: file upload */}
      {step === 1 && (
        <div className="glass p-8">
          <h2 className="text-xl font-semibold mb-4">{t('import.step1Title')}</h2>
          <p className="text-slate-400 mb-6">{t('import.step1Description')}</p>

          <div className="border-2 border-dashed border-white/20 rounded-lg p-12 text-center hover:border-orange-500/50 transition-colors">
            <input
              type="file"
              accept={ACCEPT}
              onChange={handleFileSelect}
              className="hidden"
              id="import-upload"
              disabled={loading}
            />
            <label htmlFor="import-upload" className="cursor-pointer flex flex-col items-center">
              <svg className="w-16 h-16 text-slate-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <span className="text-lg font-semibold mb-2">
                {loading ? t('common.loading') : t('import.uploadFile')}
              </span>
              <span className="text-sm text-slate-400">{t('import.uploadHint')}</span>
            </label>
          </div>

          <div className="mt-6 p-4 bg-white/5 rounded-lg space-y-3">
            <div>
              <h3 className="font-semibold mb-2">CSV</h3>
              <p className="text-sm text-slate-400 mb-2">{t('import.templateDescription')}</p>
              <code className="text-xs bg-black/30 p-2 rounded block overflow-x-auto">
                date,content,mood,stress,tags<br />
                2024-01-01,今天心情很好,5,2,工作,運動<br />
                2024-01-02,有點壓力,3,7,工作,健康
              </code>
            </div>
            <div>
              <h3 className="font-semibold mb-2">JSON (Day One / Journey / generic)</h3>
              <p className="text-sm text-slate-400">
                {t('import.jsonHint') || 'Day One exports (entries array), Journey JSON (epoch timestamps), or a generic array of {date, content, mood, ...}.'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Step 2: mapping + preview */}
      {step === 2 && preview && (
        <div className="space-y-6">
          <div className="glass p-6">
            <h2 className="text-xl font-semibold mb-4">{t('import.step2Title')}</h2>
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="p-4 bg-white/5 rounded-lg">
                <div className="text-2xl font-bold text-orange-400">{preview.total_rows}</div>
                <div className="text-sm text-slate-400">{t('import.totalRows')}</div>
              </div>
              <div className="p-4 bg-white/5 rounded-lg">
                <div className="text-2xl font-bold text-orange-400">{preview.columns.length}</div>
                <div className="text-sm text-slate-400">{t('import.totalColumns')}</div>
              </div>
              <div className="p-4 bg-white/5 rounded-lg">
                <div className="text-2xl font-bold text-rose-400">{fmtLabel}</div>
                <div className="text-sm text-slate-400">Format</div>
              </div>
            </div>

            {willGoAsync && (
              <div className="p-3 mb-4 rounded-lg bg-orange-500/10 border border-orange-500/30 text-sm text-orange-300">
                {t('import.asyncNotice') || `Large file detected (${preview.total_rows} rows). The import will run in the background and report progress.`}
              </div>
            )}

            <h3 className="font-semibold mb-3">{t('import.columnMapping')}</h3>
            <div className="space-y-2 mb-4">
              {preview.columns.map((col) => (
                <div key={col} className="flex items-center gap-3">
                  <div className="w-1/3 text-sm text-slate-300 truncate" title={col}>{col}</div>
                  <svg className="w-5 h-5 text-slate-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                  <select
                    value={mapping[col] || '_ignore'}
                    onChange={(e) => setMapping({ ...mapping, [col]: e.target.value })}
                    className="flex-1 bg-white/10 border border-white/20 rounded px-3 py-2 text-sm"
                  >
                    <option value="date">{t('import.fieldDate')}</option>
                    <option value="content">{t('import.fieldContent')}</option>
                    <option value="mood">{t('import.fieldMood')}</option>
                    <option value="stress">{t('import.fieldStress')}</option>
                    <option value="tags">{t('import.fieldTags')}</option>
                    <option value="weather">{t('import.fieldWeather')}</option>
                    <option value="temperature">{t('import.fieldTemperature')}</option>
                    <option value="_ignore">{t('import.fieldIgnore')}</option>
                  </select>
                </div>
              ))}
            </div>

            <h3 className="font-semibold mb-3">{t('import.previewData')}</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10">
                    {preview.columns.map((col) => (
                      <th key={col} className="px-3 py-2 text-left text-slate-400 font-medium">{col}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.preview_rows.map((row, idx) => (
                    <tr key={idx} className="border-b border-white/5">
                      {preview.columns.map((col) => (
                        <td key={col} className="px-3 py-2 text-slate-300">{row[col] || '-'}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="flex gap-3 justify-end">
            <button
              onClick={handleReset}
              className="px-6 py-2 bg-white/10 hover:bg-white/20 border border-white/20 rounded-lg transition-colors"
              disabled={loading || !!job}
            >
              {t('common.cancel')}
            </button>
            <button
              onClick={handleConfirmImport}
              disabled={loading || !!job}
              className="px-6 py-2 bg-orange-500 hover:bg-orange-600 rounded-lg font-semibold transition-colors disabled:opacity-50"
            >
              {loading ? t('common.importing') : t('import.confirmImport')}
            </button>
          </div>

          {/* Async progress overlay */}
          {job && job.status !== 'done' && job.status !== 'failed' && (
            <div className="glass p-6 mt-6">
              <h3 className="font-semibold mb-3">
                {t('import.processing') || 'Processing…'}
              </h3>
              <div className="w-full h-3 bg-white/10 rounded-full overflow-hidden mb-2">
                <div
                  className="h-full bg-gradient-to-r from-orange-500 to-rose-500 transition-all"
                  style={{ width: `${job.progress_percent || 0}%` }}
                />
              </div>
              <div className="flex justify-between text-sm text-slate-400">
                <span>{job.processed_rows} / {job.total_rows}</span>
                <span>{job.progress_percent || 0}%</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Step 3: result */}
      {step === 3 && result && (
        <div className="glass p-8">
          <div className="text-center mb-6">
            <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold mb-2">{t('import.importSuccess')}</h2>
            <p className="text-slate-400">{t('import.importedCount', { count: result.imported })}</p>
          </div>

          {result.errors && result.errors.length > 0 && (
            <div className="mb-6">
              <h3 className="font-semibold mb-2 text-yellow-400">{t('import.someErrors')}</h3>
              <ul className="space-y-1 text-sm text-slate-400">
                {result.errors.map((err, idx) => (
                  <li key={idx}>• {err}</li>
                ))}
              </ul>
            </div>
          )}

          <button
            onClick={handleReset}
            className="w-full px-6 py-3 bg-orange-500 hover:bg-orange-600 rounded-lg font-semibold transition-colors"
          >
            {t('import.importAnother')}
          </button>
        </div>
      )}
    </div>
  )
}
