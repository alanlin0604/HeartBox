import { useState, useRef, useCallback, useEffect, useMemo } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { useLang } from '../context/LanguageContext'
import { getAnalytics } from '../api/analytics'

const WEATHER_LABEL_KEYS = [
  { labelKey: 'noteForm.weather', isEmpty: true },
  { labelKey: 'noteForm.weatherSunny' },
  { labelKey: 'noteForm.weatherCloudy' },
  { labelKey: 'noteForm.weatherOvercast' },
  { labelKey: 'noteForm.weatherLightRain' },
  { labelKey: 'noteForm.weatherHeavyRain' },
  { labelKey: 'noteForm.weatherShower' },
  { labelKey: 'noteForm.weatherSnow' },
  { labelKey: 'noteForm.weatherFog' },
  { labelKey: 'noteForm.weatherWindy' },
  { labelKey: 'noteForm.weatherPartlyCloudy' },
]

const ACTIVITIES = [
  { id: 'exercise', emoji: '\u{1F3C3}', labelKey: 'activities.exercise' },
  { id: 'social', emoji: '\u{1F465}', labelKey: 'activities.social' },
  { id: 'work', emoji: '\u{1F4BC}', labelKey: 'activities.work' },
  { id: 'reading', emoji: '\u{1F4DA}', labelKey: 'activities.reading' },
  { id: 'travel', emoji: '\u2708\uFE0F', labelKey: 'activities.travel' },
  { id: 'music', emoji: '\u{1F3B5}', labelKey: 'activities.music' },
  { id: 'cooking', emoji: '\u{1F373}', labelKey: 'activities.cooking' },
  { id: 'meditation', emoji: '\u{1F9D8}', labelKey: 'activities.meditation' },
  { id: 'gaming', emoji: '\u{1F3AE}', labelKey: 'activities.gaming' },
  { id: 'shopping', emoji: '\u{1F6CD}\uFE0F', labelKey: 'activities.shopping' },
  { id: 'movie', emoji: '\u{1F3AC}', labelKey: 'activities.movie' },
  { id: 'nature', emoji: '\u{1F33F}', labelKey: 'activities.nature' },
]

const LANG_SPEECH_MAP = { 'zh-TW': 'zh-TW', en: 'en-US', ja: 'ja-JP' }

export default function NoteForm({ onSubmit, loading, initialPrompt }) {
  const { t, lang } = useLang()

  const TEMPLATES = [
    { key: 'morning', emoji: '\u{1F305}', labelKey: 'noteForm.tplMorning', textKey: 'noteForm.tplMorningText' },
    { key: 'gratitude', emoji: '\u{1F64F}', labelKey: 'noteForm.tplGratitude', textKey: 'noteForm.tplGratitudeText' },
    { key: 'stress', emoji: '\u{1F486}', labelKey: 'noteForm.tplStress', textKey: 'noteForm.tplStressText' },
  ]

  const [weather, setWeather] = useState('')
  const [temperature, setTemperature] = useState('')
  const [tagsInput, setTagsInput] = useState('')
  const [files, setFiles] = useState([])
  const [tagSuggestions, setTagSuggestions] = useState([])
  const [selectedActivities, setSelectedActivities] = useState([])
  const [sleepHours, setSleepHours] = useState('')
  const [sleepQuality, setSleepQuality] = useState(0)
  const [isRecording, setIsRecording] = useState(false)
  const fileInputRef = useRef(null)
  const recognitionRef = useRef(null)

  // Tiptap editor
  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: t('noteForm.placeholder') }),
    ],
    content: (() => {
      try { return localStorage.getItem('heartbox_draft') || '' } catch { return '' }
    })(),
    onUpdate: ({ editor }) => {
      try { localStorage.setItem('heartbox_draft', editor.getHTML()) } catch { /* quota */ }
    },
  })

  // Set initial prompt content if provided
  useEffect(() => {
    if (initialPrompt && editor) {
      editor.commands.setContent(initialPrompt)
    }
  }, [initialPrompt, editor])

  // Speech recognition support
  const speechSupported = useMemo(() => {
    return typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition)
  }, [])

  const toggleSpeechRecognition = useCallback(() => {
    if (isRecording) {
      recognitionRef.current?.stop()
      setIsRecording(false)
      return
    }
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) return
    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.lang = LANG_SPEECH_MAP[lang] || 'en-US'
    recognition.onresult = (event) => {
      let transcript = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          transcript += event.results[i][0].transcript
        }
      }
      if (transcript && editor) {
        editor.commands.insertContent(transcript)
      }
    }
    recognition.onerror = () => setIsRecording(false)
    recognition.onend = () => setIsRecording(false)
    recognitionRef.current = recognition
    recognition.start()
    setIsRecording(true)
  }, [isRecording, lang, editor])

  // Fetch frequent tags for autocomplete suggestions
  useEffect(() => {
    getAnalytics('week', 90)
      .then((res) => {
        const tags = res.data.frequent_tags || []
        setTagSuggestions(tags.map((t) => t.name))
      })
      .catch(() => {})
  }, [])

  // Manage object URLs for file previews
  const [previewUrls, setPreviewUrls] = useState([])
  useEffect(() => {
    const urls = files
      .filter((f) => f.type.startsWith('image/'))
      .map((f) => URL.createObjectURL(f))
    setPreviewUrls(urls)
    return () => { urls.forEach((url) => URL.revokeObjectURL(url)) }
  }, [files])

  const handleSubmit = useCallback((e) => {
    e.preventDefault()
    const content = editor?.getHTML() || ''
    if (!content.trim() || content === '<p></p>') return

    const metadata = {}
    if (weather) metadata.weather = weather
    if (temperature) metadata.temperature = parseFloat(temperature)
    if (tagsInput.trim()) {
      metadata.tags = tagsInput.split(',').map((t) => t.trim()).filter(Boolean)
    }
    if (selectedActivities.length > 0) {
      metadata.activities = selectedActivities
    }
    if (sleepHours) metadata.sleep_hours = parseFloat(sleepHours)
    if (sleepQuality > 0) metadata.sleep_quality = sleepQuality

    onSubmit(content, metadata, files)
    try { localStorage.removeItem('heartbox_draft') } catch { /* ignore */ }
    editor?.commands.clearContent()
    setWeather('')
    setTemperature('')
    setTagsInput('')
    setFiles([])
    setSelectedActivities([])
    setSleepHours('')
    setSleepQuality(0)
  }, [editor, weather, temperature, tagsInput, files, selectedActivities, sleepHours, sleepQuality, onSubmit])

  const handleFileChange = useCallback((e) => {
    const selected = Array.from(e.target.files)
    const valid = selected.filter((f) => {
      const type = f.type.split('/')[0]
      return type === 'image' && f.size <= 10 * 1024 * 1024
    })
    setFiles((prev) => [...prev, ...valid])
  }, [])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    const dropped = Array.from(e.dataTransfer.files)
    const valid = dropped.filter((f) => {
      const type = f.type.split('/')[0]
      return type === 'image' && f.size <= 10 * 1024 * 1024
    })
    setFiles((prev) => [...prev, ...valid])
  }, [])

  const removeFile = useCallback((idx) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx))
  }, [])

  const toggleActivity = (actId) => {
    setSelectedActivities((prev) =>
      prev.includes(actId) ? prev.filter((a) => a !== actId) : [...prev, actId]
    )
  }

  return (
    <form onSubmit={handleSubmit} className="glass p-6 space-y-4">
      <h2 className="text-lg font-semibold">{t('noteForm.title')}</h2>
      <div className="flex flex-wrap gap-2">
        {TEMPLATES.map((tpl) => (
          <button
            key={tpl.key}
            type="button"
            onClick={() => editor?.commands.setContent(t(tpl.textKey))}
            className="text-xs px-3 py-1.5 rounded-full bg-purple-500/15 text-purple-400 border border-purple-500/20 hover:bg-purple-500/25 transition-colors cursor-pointer"
          >
            {tpl.emoji} {t(tpl.labelKey)}
          </button>
        ))}
      </div>

      {/* Rich text editor toolbar + editor */}
      <div className="glass-card rounded-xl overflow-hidden">
        {editor && (
          <div className="flex flex-wrap items-center gap-1 px-3 py-2 border-b border-[var(--card-border)]">
            <button type="button" onClick={() => editor.chain().focus().toggleBold().run()}
              className={`p-1.5 rounded text-sm font-bold transition-colors ${editor.isActive('bold') ? 'bg-purple-500/30 text-purple-400' : 'opacity-50 hover:opacity-100'}`}>B</button>
            <button type="button" onClick={() => editor.chain().focus().toggleItalic().run()}
              className={`p-1.5 rounded text-sm italic transition-colors ${editor.isActive('italic') ? 'bg-purple-500/30 text-purple-400' : 'opacity-50 hover:opacity-100'}`}>I</button>
            <button type="button" onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
              className={`p-1.5 rounded text-sm font-bold transition-colors ${editor.isActive('heading', { level: 2 }) ? 'bg-purple-500/30 text-purple-400' : 'opacity-50 hover:opacity-100'}`}>H2</button>
            <button type="button" onClick={() => editor.chain().focus().toggleBulletList().run()}
              className={`p-1.5 rounded text-sm transition-colors ${editor.isActive('bulletList') ? 'bg-purple-500/30 text-purple-400' : 'opacity-50 hover:opacity-100'}`}>&#8226;</button>
            <button type="button" onClick={() => editor.chain().focus().toggleOrderedList().run()}
              className={`p-1.5 rounded text-sm transition-colors ${editor.isActive('orderedList') ? 'bg-purple-500/30 text-purple-400' : 'opacity-50 hover:opacity-100'}`}>1.</button>
            <button type="button" onClick={() => editor.chain().focus().toggleBlockquote().run()}
              className={`p-1.5 rounded text-sm transition-colors ${editor.isActive('blockquote') ? 'bg-purple-500/30 text-purple-400' : 'opacity-50 hover:opacity-100'}`}>&ldquo;</button>
            <div className="w-px h-5 bg-[var(--card-border)] mx-1" />
            <button type="button" onClick={() => editor.chain().focus().undo().run()} disabled={!editor.can().undo()}
              className="p-1.5 rounded text-sm opacity-50 hover:opacity-100 disabled:opacity-20">&larr;</button>
            <button type="button" onClick={() => editor.chain().focus().redo().run()} disabled={!editor.can().redo()}
              className="p-1.5 rounded text-sm opacity-50 hover:opacity-100 disabled:opacity-20">&rarr;</button>
            {speechSupported && (
              <>
                <div className="w-px h-5 bg-[var(--card-border)] mx-1" />
                <button type="button" onClick={toggleSpeechRecognition}
                  className={`p-1.5 rounded text-sm transition-colors ${isRecording ? 'bg-red-500/30 text-red-400 animate-pulse' : 'opacity-50 hover:opacity-100'}`}
                  title={t('noteForm.voiceInput')}>
                  {isRecording ? '\u{1F534}' : '\u{1F3A4}'}
                </button>
              </>
            )}
          </div>
        )}
        <EditorContent editor={editor} className="prose prose-invert max-w-none px-4 py-3 min-h-[140px] focus:outline-none [&_.tiptap]:outline-none [&_.tiptap]:min-h-[120px]" />
      </div>

      {/* Activities */}
      <div>
        <label className="block text-sm font-medium opacity-60 mb-2">{t('noteForm.activities')}</label>
        <div className="flex flex-wrap gap-2">
          {ACTIVITIES.map((act) => (
            <button
              key={act.id}
              type="button"
              onClick={() => toggleActivity(act.id)}
              className={`text-xs px-3 py-1.5 rounded-full border transition-colors cursor-pointer ${
                selectedActivities.includes(act.id)
                  ? 'bg-purple-500/25 border-purple-500/40 text-purple-400'
                  : 'border-[var(--card-border)] opacity-60 hover:opacity-100'
              }`}
            >
              {act.emoji} {t(act.labelKey)}
            </button>
          ))}
        </div>
      </div>

      {/* Sleep tracking */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium opacity-60 mb-1">{t('noteForm.sleepHours')}</label>
          <input
            type="number"
            min="0"
            max="24"
            step="0.5"
            value={sleepHours}
            onChange={(e) => setSleepHours(e.target.value)}
            placeholder="0-24"
            className="glass-input"
          />
        </div>
        <div>
          <label className="block text-sm font-medium opacity-60 mb-1">{t('noteForm.sleepQuality')}</label>
          <div className="flex gap-1 mt-1">
            {[1, 2, 3, 4, 5].map((star) => (
              <button
                key={star}
                type="button"
                onClick={() => setSleepQuality(sleepQuality === star ? 0 : star)}
                className={`text-xl transition-colors ${star <= sleepQuality ? 'text-yellow-400' : 'text-gray-500/30'}`}
              >
                &#9733;
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <select
          value={weather}
          onChange={(e) => setWeather(e.target.value)}
          className="glass-input"
        >
          {WEATHER_LABEL_KEYS.map((opt) => {
            const label = t(opt.labelKey)
            return (
              <option key={opt.labelKey} value={opt.isEmpty ? '' : label}>
                {label}
              </option>
            )
          })}
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
          list="heartbox-tag-suggestions"
        />
        <datalist id="heartbox-tag-suggestions">
          {tagSuggestions.map((tag) => (
            <option key={tag} value={tag} />
          ))}
        </datalist>
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
          accept="image/*"
          multiple
          onChange={handleFileChange}
          className="hidden"
        />
      </div>

      {/* File previews */}
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {files.map((f, idx) => {
            const imageIndex = files.slice(0, idx).filter((prev) => prev.type.startsWith('image/')).length
            return (
            <div key={idx} className="glass-card p-2 flex items-center gap-2 text-xs">
              <img
                src={previewUrls[imageIndex]}
                alt={f.name}
                className="w-10 h-10 rounded object-cover"
              />
              <span className="truncate max-w-[100px]">{f.name}</span>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); removeFile(idx) }}
                className="text-red-500 hover:text-red-400 cursor-pointer"
              >
                &times;
              </button>
            </div>
            )
          })}
        </div>
      )}

      <button type="submit" disabled={loading} className="btn-primary">
        {loading ? t('noteForm.saving') : t('noteForm.save')}
      </button>
    </form>
  )
}
