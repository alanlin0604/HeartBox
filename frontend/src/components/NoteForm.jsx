import { useState, useRef, useCallback, useEffect, useMemo } from 'react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { useLang } from '../context/LanguageContext'
import { getAnalytics } from '../api/analytics'
import EditorToolbar from './EditorToolbar'

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

// Add punctuation to speech transcript based on language
function addPunctuation(text, lang) {
  if (!text) return text
  let result = text.trim()
  if (!result) return result

  if (lang === 'zh-TW' || lang === 'ja-JP') {
    // CJK: add comma between clauses (split on natural pauses like 然後/但是/所以/因為/而且/不過/可是/就是)
    result = result.replace(/(?<=[^\s，。！？、])(然後|但是|所以|因為|而且|不過|可是|就是|接著|另外)/g, '，$1')
    // Add period at end if missing punctuation
    if (!/[，。！？、\s]$/.test(result)) {
      result += '。'
    }
  } else {
    // English: capitalize first letter, add period at end
    result = result.charAt(0).toUpperCase() + result.slice(1)
    if (!/[.!?,\s]$/.test(result)) {
      result += '.'
    }
  }
  return result
}

const GRATITUDE_TEMPLATES = [
  { id: 'gratitude_3things', nameKey: 'noteForm.gratitude3Things', contentKey: 'noteForm.gratitude3ThingsContent' },
  { id: 'gratitude_person', nameKey: 'noteForm.gratitudePerson', contentKey: 'noteForm.gratitudePersonContent' },
  { id: 'gratitude_moment', nameKey: 'noteForm.gratitudeMoment', contentKey: 'noteForm.gratitudeMomentContent' },
  { id: 'gratitude_overlooked', nameKey: 'noteForm.gratitudeOverlooked', contentKey: 'noteForm.gratitudeOverlookedContent' },
]

export default function NoteForm({ onSubmit, loading, initialPrompt }) {
  const { t, lang } = useLang()

  const TEMPLATES_KEY = 'heartbox_custom_templates'

  const loadTemplates = () => {
    try {
      return JSON.parse(localStorage.getItem(TEMPLATES_KEY) || '[]')
    } catch { return [] }
  }

  const [customTemplates, setCustomTemplates] = useState(loadTemplates)
  const [showSaveTemplate, setShowSaveTemplate] = useState(false)
  const [templateName, setTemplateName] = useState('')

  const saveTemplate = () => {
    const content = editor?.getHTML() || ''
    const textOnly = content.replace(/<[^>]*>/g, '').trim()
    if (!textOnly) return
    if (!templateName.trim()) return
    const newTpl = { id: Date.now().toString(), name: templateName.trim(), content }
    const updated = [...customTemplates, newTpl]
    setCustomTemplates(updated)
    try { localStorage.setItem(TEMPLATES_KEY, JSON.stringify(updated)) } catch {}
    setTemplateName('')
    setShowSaveTemplate(false)
  }

  const deleteTemplate = (id) => {
    const updated = customTemplates.filter((tpl) => tpl.id !== id)
    setCustomTemplates(updated)
    try { localStorage.setItem(TEMPLATES_KEY, JSON.stringify(updated)) } catch {}
  }

  const [weather, setWeather] = useState('')
  const [temperature, setTemperature] = useState('')
  const [tagsInput, setTagsInput] = useState('')
  const [files, setFiles] = useState([])
  const [tagSuggestions, setTagSuggestions] = useState([])
  const [selectedActivities, setSelectedActivities] = useState([])
  const [isRecording, setIsRecording] = useState(false)
  const [metadataType, setMetadataType] = useState(null)
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
      editor.commands.setContent(`<p>${initialPrompt}</p>`)
      editor.commands.focus('end')
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
    const speechLang = LANG_SPEECH_MAP[lang] || 'en-US'
    recognition.onresult = (event) => {
      let transcript = ''
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          transcript += event.results[i][0].transcript
        }
      }
      if (transcript && editor) {
        editor.commands.insertContent(addPunctuation(transcript, speechLang))
      }
    }
    recognition.onerror = () => setIsRecording(false)
    recognition.onend = () => setIsRecording(false)
    recognitionRef.current = recognition
    recognition.start()
    setIsRecording(true)
  }, [isRecording, lang, editor])

  // Stop speech recognition on unmount
  useEffect(() => {
    return () => {
      recognitionRef.current?.stop()
    }
  }, [])

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
    if (metadataType) {
      metadata.type = metadataType
    }

    onSubmit(content, metadata, files)
    try { localStorage.removeItem('heartbox_draft') } catch { /* ignore */ }
    editor?.commands.clearContent()
    setWeather('')
    setTemperature('')
    setTagsInput('')
    setFiles([])
    setSelectedActivities([])
    setMetadataType(null)
  }, [editor, weather, temperature, tagsInput, files, selectedActivities, metadataType, onSubmit])

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
      <div className="space-y-2">
        <div className="flex flex-wrap gap-2">
          {GRATITUDE_TEMPLATES.map((tpl) => (
            <button
              key={tpl.id}
              type="button"
              onClick={() => {
                if (editor) {
                  editor.chain().clearContent().setContent(t(tpl.contentKey)).focus('end').run()
                  setMetadataType('gratitude')
                }
              }}
              className={`text-sm px-3 py-1.5 rounded-full border font-medium transition-colors cursor-pointer ${
                metadataType === 'gratitude'
                  ? 'bg-amber-500/30 border-amber-400/50'
                  : 'bg-amber-500/20 border-amber-400/40 hover:bg-amber-500/30'
              }`}
              style={{ color: 'var(--text-primary)' }}
            >
              {t(tpl.nameKey)}
            </button>
          ))}
          {customTemplates.map((tpl) => (
            <div key={tpl.id} className="group relative">
              <button
                type="button"
                onClick={() => {
                  if (editor && tpl.content) {
                    editor.chain().clearContent().setContent(tpl.content).focus('end').run()
                  }
                }}
                className="text-sm px-3 py-1.5 rounded-full bg-purple-500/25 border border-purple-400/40 hover:bg-purple-500/35 font-medium transition-colors cursor-pointer pr-7"
                style={{ color: 'var(--text-primary)' }}
              >
                {tpl.name}
              </button>
              <button
                type="button"
                onClick={() => deleteTemplate(tpl.id)}
                className="absolute right-1 top-1/2 -translate-y-1/2 text-red-400 hover:text-red-300 text-xs opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer w-4 h-4 flex items-center justify-center"
                title={t('noteForm.deleteTemplate')}
              >
                &times;
              </button>
            </div>
          ))}
          {!showSaveTemplate ? (
            <button
              type="button"
              onClick={() => setShowSaveTemplate(true)}
              className="text-xs px-3 py-1.5 rounded-full border border-dashed border-[var(--card-border)] opacity-50 hover:opacity-100 transition-opacity cursor-pointer"
            >
              + {t('noteForm.saveTemplate')}
            </button>
          ) : (
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                placeholder={t('noteForm.templateNamePlaceholder')}
                className="glass-input text-xs py-1 px-2 w-36"
                autoFocus
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); saveTemplate() } }}
              />
              <button type="button" onClick={saveTemplate} className="text-xs text-purple-400 hover:text-purple-300 cursor-pointer">{t('common.save')}</button>
              <button type="button" onClick={() => { setShowSaveTemplate(false); setTemplateName('') }} className="text-xs opacity-50 hover:opacity-100 cursor-pointer">{t('common.cancel')}</button>
            </div>
          )}
        </div>
      </div>

      {/* Rich text editor toolbar + editor */}
      <div className="glass-card rounded-xl overflow-hidden">
        <EditorToolbar
          editor={editor}
          showVoice={speechSupported}
          isListening={isRecording}
          onToggleVoice={toggleSpeechRecognition}
        />
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
