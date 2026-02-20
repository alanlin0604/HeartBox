import { useState, useCallback, useRef, useEffect } from 'react'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'

export default function SearchFilterPanel({ filters, onFilterChange }) {
  const { t } = useLang()
  const toast = useToast()
  const [expanded, setExpanded] = useState(false)
  const [search, setSearch] = useState(filters.search || '')
  const [localTag, setLocalTag] = useState(filters.tag || '')
  const [localSentimentMin, setLocalSentimentMin] = useState(filters.sentiment_min ?? '')
  const [localSentimentMax, setLocalSentimentMax] = useState(filters.sentiment_max ?? '')
  const [localStressMin, setLocalStressMin] = useState(filters.stress_min ?? '')
  const [localStressMax, setLocalStressMax] = useState(filters.stress_max ?? '')
  const [localDateFrom, setLocalDateFrom] = useState(filters.date_from || '')
  const [localDateTo, setLocalDateTo] = useState(filters.date_to || '')
  const [showHistory, setShowHistory] = useState(false)
  const debounceRef = useRef(null)

  // Sync local state when filters change externally (e.g. clear)
  useEffect(() => {
    setSearch(filters.search || '')
    setLocalTag(filters.tag || '')
    setLocalSentimentMin(filters.sentiment_min ?? '')
    setLocalSentimentMax(filters.sentiment_max ?? '')
    setLocalStressMin(filters.stress_min ?? '')
    setLocalStressMax(filters.stress_max ?? '')
    setLocalDateFrom(filters.date_from || '')
    setLocalDateTo(filters.date_to || '')
  }, [filters])

  const getSearchHistory = () => {
    try { return JSON.parse(localStorage.getItem('heartbox_search_history') || '[]') } catch { return [] }
  }
  const saveSearchHistory = (term) => {
    if (!term.trim()) return
    try {
      const history = getSearchHistory().filter((h) => h !== term)
      history.unshift(term)
      localStorage.setItem('heartbox_search_history', JSON.stringify(history.slice(0, 10)))
    } catch { /* quota */ }
  }
  const clearSearchHistory = () => {
    try { localStorage.removeItem('heartbox_search_history') } catch {}
    setShowHistory(false)
  }
  const searchHistory = getSearchHistory()

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [])

  const handleSearchSubmit = useCallback((e) => {
    e.preventDefault()
    saveSearchHistory(search)
    setShowHistory(false)
    onFilterChange({ ...filters, search })
  }, [filters, search, onFilterChange])

  const updateFilter = useCallback((key, value) => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      const next = { ...filters, [key]: value }
      // Validate min <= max
      if (key === 'sentiment_min' && next.sentiment_max && Number(value) > Number(next.sentiment_max)) {
        toast?.error(t('search.minExceedsMax'))
        return
      }
      if (key === 'sentiment_max' && next.sentiment_min && Number(value) < Number(next.sentiment_min)) {
        toast?.error(t('search.minExceedsMax'))
        return
      }
      if (key === 'stress_min' && next.stress_max && Number(value) > Number(next.stress_max)) {
        toast?.error(t('search.minExceedsMax'))
        return
      }
      if (key === 'stress_max' && next.stress_min && Number(value) < Number(next.stress_min)) {
        toast?.error(t('search.minExceedsMax'))
        return
      }
      if (key === 'date_from' && next.date_to && value > next.date_to) {
        toast?.error(t('search.minExceedsMax'))
        return
      }
      if (key === 'date_to' && next.date_from && value < next.date_from) {
        toast?.error(t('search.minExceedsMax'))
        return
      }
      onFilterChange(next)
    }, 300)
  }, [filters, onFilterChange])

  const clearFilters = useCallback(() => {
    setSearch('')
    onFilterChange({})
  }, [onFilterChange])

  const hasActiveFilters = Object.values(filters).some((v) => v !== undefined && v !== null && v !== '')

  return (
    <div className="glass-card p-4 space-y-3">
      {/* Search bar */}
      <form onSubmit={handleSearchSubmit} className="flex gap-2 relative">
        <div className="relative flex-1">
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onFocus={() => searchHistory.length > 0 && setShowHistory(true)}
            onBlur={() => setTimeout(() => setShowHistory(false), 200)}
            placeholder={t('search.placeholder')}
            className="glass-input text-sm w-full"
          />
          {showHistory && searchHistory.length > 0 && (
            <div className="absolute left-0 right-0 top-full mt-1 glass-card p-2 z-30 space-y-1">
              <div className="flex items-center justify-between px-2 pb-1 border-b border-white/10">
                <span className="text-xs opacity-50">{t('search.recentSearches')}</span>
                <button
                  type="button"
                  onMouseDown={(e) => { e.preventDefault(); clearSearchHistory() }}
                  className="text-xs text-red-400 hover:text-red-300 cursor-pointer"
                >
                  {t('search.clearHistory')}
                </button>
              </div>
              {searchHistory.map((term) => (
                <button
                  key={term}
                  type="button"
                  onMouseDown={(e) => {
                    e.preventDefault()
                    setSearch(term)
                    setShowHistory(false)
                    onFilterChange({ ...filters, search: term })
                  }}
                  className="block w-full text-left text-sm px-2 py-1 rounded hover:bg-white/10 cursor-pointer truncate"
                >
                  {term}
                </button>
              ))}
            </div>
          )}
        </div>
        <button type="submit" className="btn-primary text-sm px-4">
          {t('search.search')}
        </button>
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="btn-primary text-sm px-3 opacity-70"
          title={t('search.filters')}
          aria-label={expanded ? t('aria.collapseFilters') : t('aria.expandFilters')}
          aria-expanded={expanded}
        >
          {expanded ? '▲' : '▼'}
        </button>
      </form>

      {/* Collapsible filters */}
      {expanded && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-2 border-t border-white/10">
          {/* Tag */}
          <div>
            <label className="text-xs opacity-60 mb-1 block">{t('search.tag')}</label>
            <input
              type="text"
              value={localTag}
              onChange={(e) => { setLocalTag(e.target.value); updateFilter('tag', e.target.value) }}
              placeholder={t('search.tagPlaceholder')}
              className="glass-input text-sm w-full"
            />
          </div>

          {/* Sentiment range */}
          <div>
            <label className="text-xs opacity-60 mb-1 block">{t('search.sentimentRange')}</label>
            <div className="flex gap-2">
              <input
                type="number"
                step="0.1"
                min="-1"
                max="1"
                value={localSentimentMin}
                onChange={(e) => { setLocalSentimentMin(e.target.value); updateFilter('sentiment_min', e.target.value) }}
                placeholder="-1.0"
                className="glass-input text-sm w-full"
              />
              <span className="self-center opacity-40">~</span>
              <input
                type="number"
                step="0.1"
                min="-1"
                max="1"
                value={localSentimentMax}
                onChange={(e) => { setLocalSentimentMax(e.target.value); updateFilter('sentiment_max', e.target.value) }}
                placeholder="1.0"
                className="glass-input text-sm w-full"
              />
            </div>
          </div>

          {/* Stress range */}
          <div>
            <label className="text-xs opacity-60 mb-1 block">{t('search.stressRange')}</label>
            <div className="flex gap-2">
              <input
                type="number"
                min="0"
                max="10"
                value={localStressMin}
                onChange={(e) => { setLocalStressMin(e.target.value); updateFilter('stress_min', e.target.value) }}
                placeholder="0"
                className="glass-input text-sm w-full"
              />
              <span className="self-center opacity-40">~</span>
              <input
                type="number"
                min="0"
                max="10"
                value={localStressMax}
                onChange={(e) => { setLocalStressMax(e.target.value); updateFilter('stress_max', e.target.value) }}
                placeholder="10"
                className="glass-input text-sm w-full"
              />
            </div>
          </div>

          {/* Date range */}
          <div className="sm:col-span-2 lg:col-span-2">
            <label className="text-xs opacity-60 mb-1 block">{t('search.dateRange')}</label>
            <div className="flex gap-2">
              <input
                type="date"
                value={localDateFrom}
                onChange={(e) => { setLocalDateFrom(e.target.value); updateFilter('date_from', e.target.value) }}
                className="glass-input text-sm w-full"
              />
              <span className="self-center opacity-40">~</span>
              <input
                type="date"
                value={localDateTo}
                onChange={(e) => { setLocalDateTo(e.target.value); updateFilter('date_to', e.target.value) }}
                className="glass-input text-sm w-full"
              />
            </div>
          </div>

          {/* Clear button */}
          {hasActiveFilters && (
            <div className="flex items-end">
              <button
                onClick={clearFilters}
                className="text-sm text-red-400 hover:text-red-300 transition-colors"
              >
                {t('search.clear')}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
