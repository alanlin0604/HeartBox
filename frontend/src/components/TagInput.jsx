import { useState, useEffect, useRef, forwardRef, useImperativeHandle } from 'react'
import { tagAPI } from '../api/tags'
import { useLang } from '../context/LanguageContext'

// User-pickable tag accent colors. Brand orange/rose first.
const TAG_COLORS = [
  '#f97316', // orange (brand)
  '#f43f5e', // rose (brand)
  '#ec4899', // pink
  '#f59e0b', // amber
  '#10b981', // emerald
  '#06b6d4', // cyan
  '#3b82f6', // blue
  '#6366f1', // indigo
]

function TagInputImpl({ value = [], onChange }, ref) {
  const { t } = useLang()
  const [input, setInput] = useState('')
  const [suggestions, setSuggestions] = useState([])
  const [showDropdown, setShowDropdown] = useState(false)
  const [allTags, setAllTags] = useState([])
  const inputRef = useRef(null)

  async function loadTags() {
    try {
      const tags = await tagAPI.list()
      setAllTags(tags)
    } catch (err) {
      console.error('Failed to load tags:', err)
    }
  }

  async function loadSuggestions(query) {
    try {
      const tags = await tagAPI.autocomplete(query)
      // Filter out already selected tags
      const filtered = tags.filter(tag => !value.find(v => v.id === tag.id))
      setSuggestions(filtered)
      setShowDropdown(true)
    } catch (err) {
      console.error('Failed to load tag suggestions:', err)
    }
  }

  // eslint-disable-next-line react-hooks/exhaustive-deps -- mount-only
  useEffect(() => { loadTags() }, [])

  // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional: re-run on input change only
  useEffect(() => {
    if (input.trim()) {
      loadSuggestions(input)
    } else {
      setSuggestions([])
    }
  }, [input])

  async function handleCreateTag() {
    return await createTagFromInput(input)
  }

  // Internal — name-aware create. Returns the tag object (existing or
  // newly-created) so the imperative `flush()` API can return it to
  // NoteForm, which needs the id synchronously to include in tag_ids on
  // submit. Falls back to null on API failure.
  async function createTagFromInput(rawName) {
    const name = (rawName || '').trim().toLowerCase()
    if (!name) return null
    const existing = allTags.find(t => t.name === name)
    if (existing) {
      handleSelectTag(existing)
      return existing
    }
    try {
      const color = TAG_COLORS[Math.floor(Math.random() * TAG_COLORS.length)]
      const newTag = await tagAPI.create({ name, color })
      setAllTags(prev => [...prev, newTag])
      handleSelectTag(newTag)
      return newTag
    } catch (err) {
      console.error('Failed to create tag:', err)
      return null
    }
  }

  // Imperative API for parent forms: pull whatever pending text is in the
  // input, materialize it as a Tag row, return the resulting tag(s) so
  // the parent can include them in the submission without waiting for
  // React state to flush. Fixes the "user typed a tag, clicked Submit
  // without pressing Enter, note saved without the tag" bug.
  useImperativeHandle(ref, () => ({
    async flush() {
      if (!input.trim()) return []
      const tag = await createTagFromInput(input)
      setInput('')
      return tag ? [tag] : []
    },
  }), [input, allTags])

  function handleSelectTag(tag) {
    if (!value.find(v => v.id === tag.id)) {
      onChange([...value, tag])
    }
    setInput('')
    setSuggestions([])
    setShowDropdown(false)
    inputRef.current?.focus()
  }

  function handleRemoveTag(tagId) {
    onChange(value.filter(t => t.id !== tagId))
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter') {
      e.preventDefault()
      if (suggestions.length > 0) {
        handleSelectTag(suggestions[0])
      } else {
        handleCreateTag()
      }
    } else if (e.key === 'Backspace' && !input && value.length > 0) {
      handleRemoveTag(value[value.length - 1].id)
    }
  }

  // Hide dropdown on blur. We intentionally do NOT auto-create the
  // pending tag here because of a timing race with form submit: blur on
  // click-Submit fires BEFORE the submit handler, so an async tag-create
  // would still leave selectedTags stale by the time the handler reads
  // it. NoteForm calls `tagInputRef.current.flush()` from inside its
  // submit handler instead, which materializes the pending tag AND
  // returns it synchronously so it can be included in tag_ids.
  function handleBlur() {
    setTimeout(() => setShowDropdown(false), 200)
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2 p-2 glass-input min-h-11">
        {value.map(tag => (
          <span
            key={tag.id}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium"
            style={{
              backgroundColor: tag.color + '20',
              color: tag.color,
              border: `1px solid ${tag.color}40`,
            }}
          >
            {tag.name}
            <button
              type="button"
              onClick={() => handleRemoveTag(tag.id)}
              className="ml-1 hover:opacity-70"
              aria-label={t('tags.remove')}
            >
              ×
            </button>
          </span>
        ))}
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => input && setShowDropdown(true)}
          onBlur={handleBlur}
          placeholder={value.length === 0 ? t('tags.placeholder') : ''}
          className="flex-1 min-w-[120px] bg-transparent border-none outline-none text-sm"
        />
      </div>

      {showDropdown && suggestions.length > 0 && (
        <div className="glass rounded-lg p-2 max-h-48 overflow-y-auto">
          {suggestions.map(tag => (
            <button
              key={tag.id}
              type="button"
              onClick={() => handleSelectTag(tag)}
              className="w-full text-left px-3 py-2 rounded hover:bg-white/10 flex items-center gap-2"
            >
              <span
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: tag.color }}
              />
              <span className="text-sm">{tag.name}</span>
              <span className="ml-auto text-xs text-slate-400">
                {tag.note_count} {t('tags.notes')}
              </span>
            </button>
          ))}
        </div>
      )}

      {input && !showDropdown && (
        <p className="text-xs text-slate-400">
          {t('tags.pressEnter')}
        </p>
      )}
    </div>
  )
}

const TagInput = forwardRef(TagInputImpl)
export default TagInput
