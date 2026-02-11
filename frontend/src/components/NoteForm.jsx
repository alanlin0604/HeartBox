import { useState, useRef, useCallback } from 'react'
import { useLang } from '../context/LanguageContext'

const WEATHER_KEYS = [
  { value: '', labelKey: 'noteForm.weather' },
  { value: '☀️ 晴天', labelKey: 'noteForm.weatherSunny' },
  { value: '⛅ 多雲', labelKey: 'noteForm.weatherCloudy' },
  { value: '☁️ 陰天', labelKey: 'noteForm.weatherOvercast' },
  { value: '🌧️ 小雨', labelKey: 'noteForm.weatherLightRain' },
  { value: '⛈️ 大雨/雷雨', labelKey: 'noteForm.weatherHeavyRain' },
  { value: '🌦️ 陣雨', labelKey: 'noteForm.weatherShower' },
  { value: '❄️ 下雪', labelKey: 'noteForm.weatherSnow' },
  { value: '🌫️ 霧', labelKey: 'noteForm.weatherFog' },
  { value: '💨 強風', labelKey: 'noteForm.weatherWindy' },
  { value: '🌤️ 晴時多雲', labelKey: 'noteForm.weatherPartlyCloudy' },
]

export default function NoteForm({ onSubmit, loading }) {
  const { t } = useLang()
  const [content, setContent] = useState('')
  const [weather, setWeather] = useState('')
  const [temperature, setTemperature] = useState('')
  const [tagsInput, setTagsInput] = useState('')
  const [files, setFiles] = useState([])
  const fileInputRef = useRef(null)

  const handleSubmit = useCallback((e) => {
    e.preventDefault()
    if (!content.trim()) return

    const metadata = {}
    if (weather) metadata.weather = weather
    if (temperature) metadata.temperature = parseFloat(temperature)
    if (tagsInput.trim()) {
      metadata.tags = tagsInput.split(',').map((t) => t.trim()).filter(Boolean)
    }

    onSubmit(content, metadata, files)
    setContent('')
    setWeather('')
    setTemperature('')
    setTagsInput('')
    setFiles([])
  }, [content, weather, temperature, tagsInput, files, onSubmit])

  const handleFileChange = useCallback((e) => {
    const selected = Array.from(e.target.files)
    const valid = selected.filter((f) => {
      const type = f.type.split('/')[0]
      return (type === 'image' || type === 'audio') && f.size <= 10 * 1024 * 1024
    })
    setFiles((prev) => [...prev, ...valid])
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    const dropped = Array.from(e.dataTransfer.files)
    const valid = dropped.filter((f) => {
      const type = f.type.split('/')[0]
      return (type === 'image' || type === 'audio') && f.size <= 10 * 1024 * 1024
    })
    setFiles((prev) => [...prev, ...valid])
  }, [])

  const removeFile = useCallback((idx) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx))
  }, [])

  return (
    <form onSubmit={handleSubmit} className="glass p-6 space-y-4">
      <h2 className="text-lg font-semibold">{t('noteForm.title')}</h2>
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder={t('noteForm.placeholder')}
        className="glass-input min-h-[140px] resize-y text-base"
        rows={5}
      />
      <div className="grid grid-cols-3 gap-3">
        <select
          value={weather}
          onChange={(e) => setWeather(e.target.value)}
          className="glass-input"
        >
          {WEATHER_KEYS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {t(opt.labelKey)}
            </option>
          ))}
        </select>
        <input
          type="number"
          value={temperature}
          onChange={(e) => setTemperature(e.target.value)}
          placeholder={t('noteForm.temperature')}
          className="glass-input"
        />
        <input
          type="text"
          value={tagsInput}
          onChange={(e) => setTagsInput(e.target.value)}
          placeholder={t('noteForm.tags')}
          className="glass-input"
        />
      </div>

      {/* File upload area */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className="glass-card p-4 border-2 border-dashed border-white/10 rounded-xl text-center cursor-pointer hover:border-purple-500/30 transition-colors"
      >
        <p className="text-sm opacity-60">{t('noteForm.attachHint')}</p>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,audio/*"
          multiple
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      {/* File previews */}
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {files.map((f, idx) => (
            <div key={idx} className="glass-card p-2 flex items-center gap-2 text-xs">
              {f.type.startsWith('image/') ? (
                <img
                  src={URL.createObjectURL(f)}
                  alt={f.name}
                  className="w-10 h-10 rounded object-cover"
                />
              ) : (
                <span className="w-10 h-10 rounded bg-purple-500/20 flex items-center justify-center text-lg">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M9 18V5l12-2v13"/>
                    <circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>
                  </svg>
                </span>
              )}
              <span className="truncate max-w-[100px]">{f.name}</span>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); removeFile(idx) }}
                className="text-red-500 hover:text-red-400 cursor-pointer"
              >
                &times;
              </button>
            </div>
          ))}
        </div>
      )}

      <button type="submit" disabled={loading || !content.trim()} className="btn-primary">
        {loading ? t('noteForm.saving') : t('noteForm.save')}
      </button>
    </form>
  )
}
