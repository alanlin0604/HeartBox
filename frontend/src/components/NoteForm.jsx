import { useState, useRef, useCallback, useEffect, useMemo, lazy, Suspense } from 'react'
import { useLang } from '../context/LanguageContext'
import { ACTIVITY_ICONS } from './icons/ActivityIcons'
import TagInput from './TagInput'

const RichTextEditor = lazy(() => import('./RichTextEditor'))

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

// Activities with SVG Icons (Professional, Accessible)
const ACTIVITIES = [
  { id: 'exercise', icon: ACTIVITY_ICONS.exercise, labelKey: 'activities.exercise' },
  { id: 'social', icon: ACTIVITY_ICONS.social, labelKey: 'activities.social' },
  { id: 'work', icon: ACTIVITY_ICONS.work, labelKey: 'activities.work' },
  { id: 'reading', icon: ACTIVITY_ICONS.reading, labelKey: 'activities.reading' },
  { id: 'travel', icon: ACTIVITY_ICONS.travel, labelKey: 'activities.travel' },
  { id: 'music', icon: ACTIVITY_ICONS.music, labelKey: 'activities.music' },
  { id: 'cooking', icon: ACTIVITY_ICONS.cooking, labelKey: 'activities.cooking' },
  { id: 'meditation', icon: ACTIVITY_ICONS.meditation, labelKey: 'activities.meditation' },
  { id: 'gaming', icon: ACTIVITY_ICONS.gaming, labelKey: 'activities.gaming' },
  { id: 'shopping', icon: ACTIVITY_ICONS.shopping, labelKey: 'activities.shopping' },
  { id: 'movie', icon: ACTIVITY_ICONS.movie, labelKey: 'activities.movie' },
  { id: 'nature', icon: ACTIVITY_ICONS.nature, labelKey: 'activities.nature' },
]

const LANG_SPEECH_MAP = { 'zh-TW': 'zh-TW', en: 'en-US', ja: 'ja-JP' }

// Add punctuation to speech transcript based on language
function addPunctuation(text, lang) {
  if (!text) return text
  let result = text.trim()
  if (!result) return result

  if (lang === 'zh-TW' || lang === 'ja-JP') {
    // CJK: add comma between clauses (split on natural pauses like 然後/但是/所以/因為/而且/不過/可是/就是)
    result = result.replace(/([^\s，。！？、])(然後|但是|所以|因為|而且|不過|可是|就是|接著|另外)/g, '$1，$2')
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
  const PINS_KEY = 'heartbox_template_pins'
  const HIDDEN_KEY = 'heartbox_template_hidden'

  const loadJSON = (key, fallback) => {
    try {
      const raw = localStorage.getItem(key)
      return raw ? JSON.parse(raw) : fallback
    } catch { return fallback }
  }
  const writeJSON = (key, value) => {
    try { localStorage.setItem(key, JSON.stringify(value)) } catch { /* quota / private mode */ }
  }

  const [customTemplates, setCustomTemplates] = useState(() => loadJSON(TEMPLATES_KEY, []))
  const [pinnedIds, setPinnedIds] = useState(() => loadJSON(PINS_KEY, []))
  const [hiddenIds, setHiddenIds] = useState(() => loadJSON(HIDDEN_KEY, []))
  const [showSaveTemplate, setShowSaveTemplate] = useState(false)
  const [templateName, setTemplateName] = useState('')
  // Right-click / long-press context menu: { x, y, template } or null
  const [tplMenu, setTplMenu] = useState(null)

  const saveTemplate = () => {
    const content = editorRef.current?.getHTML() || ''
    const textOnly = content.replace(/<[^>]*>/g, '').trim()
    if (!textOnly) return
    if (!templateName.trim()) return
    const newTpl = { id: Date.now().toString(), name: templateName.trim(), content }
    const updated = [...customTemplates, newTpl]
    setCustomTemplates(updated)
    writeJSON(TEMPLATES_KEY, updated)
    setTemplateName('')
    setShowSaveTemplate(false)
  }

  const togglePin = (id) => {
    const next = pinnedIds.includes(id)
      ? pinnedIds.filter((p) => p !== id)
      : [id, ...pinnedIds]
    setPinnedIds(next)
    writeJSON(PINS_KEY, next)
  }

  const removeTemplate = (tpl) => {
    if (tpl.kind === 'custom') {
      const updated = customTemplates.filter((c) => c.id !== tpl.id)
      setCustomTemplates(updated)
      writeJSON(TEMPLATES_KEY, updated)
      // Also drop from pins if present
      if (pinnedIds.includes(tpl.id)) {
        const next = pinnedIds.filter((p) => p !== tpl.id)
        setPinnedIds(next)
        writeJSON(PINS_KEY, next)
      }
    } else {
      // Built-in: hide via flag (so it can be restored)
      const next = [...hiddenIds, tpl.id]
      setHiddenIds(next)
      writeJSON(HIDDEN_KEY, next)
    }
  }

  const restoreHidden = () => {
    setHiddenIds([])
    writeJSON(HIDDEN_KEY, [])
  }

  const [weather, setWeather] = useState('')
  const [temperature, setTemperature] = useState('')
  const [selectedTags, setSelectedTags] = useState([])
  const [files, setFiles] = useState([])
  const [selectedActivities, setSelectedActivities] = useState([])
  const [isRecording, setIsRecording] = useState(false)
  const [metadataType, setMetadataType] = useState(null)
  const fileInputRef = useRef(null)
  const recognitionRef = useRef(null)
  const editorRef = useRef(null)

  // Initial content from localStorage draft
  const [initialContent] = useState(() => {
    try { return localStorage.getItem('heartbox_draft') || '' } catch { return '' }
  })

  // Handle editor updates
  const handleEditorUpdate = useCallback((html) => {
    try { localStorage.setItem('heartbox_draft', html) } catch { /* quota */ }
  }, [])

  // Set initial prompt content if provided
  useEffect(() => {
    if (initialPrompt && editorRef.current) {
      editorRef.current.setContent(`<p>${initialPrompt}</p>`)
      editorRef.current.focus('end')
    }
  }, [initialPrompt])

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
      if (transcript && editorRef.current) {
        editorRef.current.insertContent(addPunctuation(transcript, speechLang))
      }
    }
    recognition.onerror = () => setIsRecording(false)
    recognition.onend = () => setIsRecording(false)
    recognitionRef.current = recognition
    recognition.start()
    setIsRecording(true)
  }, [isRecording, lang])

  // Stop speech recognition on unmount
  useEffect(() => {
    return () => {
      recognitionRef.current?.stop()
    }
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
    const content = editorRef.current?.getHTML() || ''
    if (!content.trim() || content === '<p></p>') return

    const metadata = {}
    if (weather) metadata.weather = weather
    if (temperature) metadata.temperature = parseFloat(temperature)
    if (selectedActivities.length > 0) {
      metadata.activities = selectedActivities
    }
    if (metadataType) {
      metadata.type = metadataType
    }

    const tag_ids = selectedTags.map(tag => tag.id)
    onSubmit(content, metadata, files, tag_ids)
    try { localStorage.removeItem('heartbox_draft') } catch { /* ignore */ }
    editorRef.current?.clear()
    setWeather('')
    setTemperature('')
    setSelectedTags([])
    setFiles([])
    setSelectedActivities([])
    setMetadataType(null)
  }, [weather, temperature, selectedTags, files, selectedActivities, metadataType, onSubmit])

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

  // === Unified template list: built-in + custom, hidden filtered, pinned first ===
  const allTemplates = useMemo(() => {
    const builtin = GRATITUDE_TEMPLATES.map((tpl) => ({
      id: tpl.id,
      name: t(tpl.nameKey),
      content: t(tpl.contentKey),
      kind: 'builtin',
      isGratitude: true,
    }))
    const custom = customTemplates.map((tpl) => ({
      id: tpl.id,
      name: tpl.name,
      content: tpl.content,
      kind: 'custom',
      isGratitude: false,
    }))
    const visible = [...builtin, ...custom].filter((tpl) => !hiddenIds.includes(tpl.id))
    const pinSet = new Set(pinnedIds)
    const pinned = pinnedIds
      .map((id) => visible.find((v) => v.id === id))
      .filter(Boolean)
    const rest = visible.filter((v) => !pinSet.has(v.id))
    return [...pinned, ...rest]
  }, [customTemplates, pinnedIds, hiddenIds, t])

  const applyTemplate = (tpl) => {
    if (!editorRef.current?.editor || !tpl.content) return
    editorRef.current.editor.chain().clearContent().setContent(tpl.content).focus('end').run()
    if (tpl.isGratitude) setMetadataType('gratitude')
  }

  // === Long-press detection (mobile) ===
  const longPressTimer = useRef(null)
  const longPressFired = useRef(false)
  const touchStartPos = useRef({ x: 0, y: 0 })

  const handleTouchStart = (e, tpl) => {
    longPressFired.current = false
    const touch = e.touches[0]
    touchStartPos.current = { x: touch.clientX, y: touch.clientY }
    longPressTimer.current = setTimeout(() => {
      longPressFired.current = true
      setTplMenu({ x: touch.clientX, y: touch.clientY, template: tpl })
    }, 500)
  }
  const handleTouchMove = (e) => {
    if (!longPressTimer.current) return
    const touch = e.touches[0]
    const dx = Math.abs(touch.clientX - touchStartPos.current.x)
    const dy = Math.abs(touch.clientY - touchStartPos.current.y)
    if (dx > 10 || dy > 10) {
      clearTimeout(longPressTimer.current)
      longPressTimer.current = null
    }
  }
  const handleTouchEnd = () => {
    if (longPressTimer.current) {
      clearTimeout(longPressTimer.current)
      longPressTimer.current = null
    }
  }

  // Close menu on outside click / Escape
  useEffect(() => {
    if (!tplMenu) return
    const close = () => setTplMenu(null)
    const onKey = (e) => { if (e.key === 'Escape') close() }
    document.addEventListener('mousedown', close)
    document.addEventListener('touchstart', close)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('touchstart', close)
      document.removeEventListener('keydown', onKey)
    }
  }, [tplMenu])

  return (
    <form onSubmit={handleSubmit} className="glass p-6 space-y-4">
      <h2 className="text-lg font-semibold">{t('noteForm.title')}</h2>
      <div className="space-y-2">
        <div className="flex flex-wrap gap-2">
          {allTemplates.map((tpl) => {
            const pinned = pinnedIds.includes(tpl.id)
            const isActive = tpl.isGratitude && metadataType === 'gratitude'
            const baseColor = tpl.isGratitude
              ? (isActive ? 'bg-amber-500/30 border-amber-400/50' : 'bg-amber-500/20 border-amber-400/40 hover:bg-amber-500/30')
              : 'bg-orange-500/25 border-orange-400/40 hover:bg-orange-500/35'
            return (
              <button
                key={tpl.id}
                type="button"
                onClick={() => {
                  if (longPressFired.current) { longPressFired.current = false; return }
                  applyTemplate(tpl)
                }}
                onContextMenu={(e) => {
                  e.preventDefault()
                  setTplMenu({ x: e.clientX, y: e.clientY, template: tpl })
                }}
                onTouchStart={(e) => handleTouchStart(e, tpl)}
                onTouchMove={handleTouchMove}
                onTouchEnd={handleTouchEnd}
                className={`text-sm px-3 py-1.5 rounded-full border font-medium transition-colors cursor-pointer select-none ${baseColor}`}
                style={{ color: 'var(--text-primary)', WebkitTouchCallout: 'none' }}
              >
                {pinned && <span className="mr-1" aria-hidden="true">📌</span>}
                {tpl.name}
              </button>
            )
          })}
          {hiddenIds.length > 0 && (
            <button
              type="button"
              onClick={restoreHidden}
              className="text-xs px-3 py-1.5 rounded-full border border-dashed border-[var(--card-border)] opacity-50 hover:opacity-100 transition-opacity cursor-pointer"
            >
              ↺ {t('noteForm.restoreHidden')}
            </button>
          )}
          {!showSaveTemplate ? (
            <button
              type="button"
              onClick={() => setShowSaveTemplate(true)}
              className="text-xs px-3 py-1.5 rounded-full border border-dashed border-[var(--card-border)] opacity-50 hover:opacity-100 transition-opacity cursor-pointer"
            >
              + {t('noteForm.saveTemplate')}
            </button>
          ) : (
            <div className="flex items-center gap-2 flex-wrap">
              <input
                type="text"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                placeholder={t('noteForm.templateNamePlaceholder')}
                className="glass-input text-sm py-2 px-3 w-40 sm:w-48"
                autoFocus
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); saveTemplate() } }}
              />
              <button type="button" onClick={saveTemplate} className="text-sm text-orange-400 hover:text-orange-300 cursor-pointer px-2 py-1.5">{t('common.save')}</button>
              <button type="button" onClick={() => { setShowSaveTemplate(false); setTemplateName('') }} className="text-sm opacity-50 hover:opacity-100 cursor-pointer px-2 py-1.5">{t('common.cancel')}</button>
            </div>
          )}
        </div>
      </div>

      {/* Rich text editor toolbar + editor */}
      <div className="glass-card rounded-xl overflow-hidden">
        <Suspense fallback={
          <div className="prose prose-invert max-w-none px-4 py-3 min-h-[140px] flex items-center justify-center opacity-50">
            <div className="animate-pulse text-sm">Loading editor...</div>
          </div>
        }>
          <RichTextEditor
            ref={editorRef}
            initialContent={initialContent}
            placeholder={t('noteForm.placeholder')}
            onUpdate={handleEditorUpdate}
            showVoice={speechSupported}
            isListening={isRecording}
            onToggleVoice={toggleSpeechRecognition}
            className="prose prose-invert max-w-none px-4 py-3 min-h-[140px] focus:outline-none [&_.tiptap]:outline-none [&_.tiptap]:min-h-[120px]"
          />
        </Suspense>
      </div>

      {/* Activities - SVG Icons */}
      <div>
        <label className="block text-sm font-medium text-slate-400 mb-2">{t('noteForm.activities')}</label>
        <div className="flex flex-wrap gap-2">
          {ACTIVITIES.map((act) => {
            const Icon = act.icon
            return (
              <button
                key={act.id}
                type="button"
                onClick={() => toggleActivity(act.id)}
                className={`
                  inline-flex items-center gap-1.5
                  text-xs px-3 py-2 rounded-full border
                  transition-all cursor-pointer
                  min-h-[36px]
                  focus-visible:outline-2 focus-visible:outline-offset-2
                  focus-visible:outline-[var(--color-primary-400)]
                  ${selectedActivities.includes(act.id)
                    ? 'bg-orange-500/25 border-orange-500/40 text-orange-400 shadow-sm'
                    : 'border-[var(--card-border)] opacity-60 hover:opacity-100 hover:border-[var(--border-primary)]'
                  }
                `.trim().replace(/\s+/g, ' ')}
                aria-pressed={selectedActivities.includes(act.id)}
                aria-label={t(act.labelKey)}
              >
                <Icon className="w-4 h-4 shrink-0" />
                <span>{t(act.labelKey)}</span>
              </button>
            )
          })}
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
        <TagInput value={selectedTags} onChange={setSelectedTags} />
      </div>

      {/* File upload area */}
      <div
        onDragOver={(e) => e.preventDefault()}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className="glass-card p-4 border-2 border-dashed border-white/10 rounded-xl text-center cursor-pointer hover:border-orange-500/30 transition-colors"
      >
        <p className="text-sm text-slate-400">{t('noteForm.attachHint')}</p>
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
                className="text-red-500 hover:text-red-400 cursor-pointer p-1 -m-1 leading-none text-lg"
                aria-label={t('aria.removeFile') || 'Remove file'}
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

      {tplMenu && (
        <div
          role="menu"
          onMouseDown={(e) => e.stopPropagation()}
          onTouchStart={(e) => e.stopPropagation()}
          className="fixed z-[60] min-w-[140px] py-1 rounded-lg shadow-xl border"
          style={{
            left: Math.min(tplMenu.x, window.innerWidth - 160),
            top: Math.min(tplMenu.y, window.innerHeight - 100),
            background: 'var(--card-bg)',
            borderColor: 'var(--card-border)',
            color: 'var(--text-primary)',
          }}
        >
          <button
            type="button"
            role="menuitem"
            onClick={() => { togglePin(tplMenu.template.id); setTplMenu(null) }}
            className="w-full text-left px-3 py-2 text-sm hover:bg-white/10 cursor-pointer flex items-center gap-2"
          >
            <span aria-hidden="true">📌</span>
            {pinnedIds.includes(tplMenu.template.id) ? t('noteForm.templateUnpin') : t('noteForm.templatePin')}
          </button>
          <button
            type="button"
            role="menuitem"
            onClick={() => { removeTemplate(tplMenu.template); setTplMenu(null) }}
            className="w-full text-left px-3 py-2 text-sm hover:bg-white/10 text-red-400 cursor-pointer flex items-center gap-2"
          >
            <span aria-hidden="true">🗑</span>
            {tplMenu.template.kind === 'custom' ? t('noteForm.templateDelete') : t('noteForm.templateHide')}
          </button>
        </div>
      )}
    </form>
  )
}
