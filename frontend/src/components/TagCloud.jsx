import { useEffect, useState } from 'react'
import { tagAPI } from '../api/tags'
import { useLang } from '../context/LanguageContext'

export default function TagCloud({ onTagClick }) {
  const { t } = useLang()
  const [tags, setTags] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadTagCloud()
  }, [])

  async function loadTagCloud() {
    try {
      setLoading(true)
      const data = await tagAPI.cloud()
      setTags(data)
    } catch (err) {
      console.error('Failed to load tag cloud:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('tags.cloud')}</h2>
        <p className="text-sm text-slate-400">{t('dashboard.loading')}</p>
      </div>
    )
  }

  if (tags.length === 0) {
    return (
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('tags.cloud')}</h2>
        <p className="text-sm text-slate-400">{t('dashboard.noTags')}</p>
      </div>
    )
  }

  // Calculate font sizes based on count (logarithmic scale for better visual balance)
  const counts = tags.map(t => t.count)
  const maxCount = Math.max(...counts)
  const minCount = Math.min(...counts)
  const range = maxCount - minCount || 1

  function getFontSize(count) {
    // Logarithmic scale: 0.75rem to 2rem
    const normalized = (Math.log(count + 1) - Math.log(minCount + 1)) / (Math.log(maxCount + 1) - Math.log(minCount + 1))
    return `${0.75 + normalized * 1.25}rem`
  }

  function getOpacity(count) {
    // More used tags are more opaque
    const normalized = (count - minCount) / range
    return 0.6 + normalized * 0.4
  }

  return (
    <div className="glass p-6">
      <h2 className="text-lg font-semibold mb-4">{t('tags.cloud')}</h2>
      <div className="flex flex-wrap gap-3 items-center justify-center min-h-[200px]">
        {tags.map(tag => (
          <button
            key={tag.name}
            onClick={() => onTagClick?.(tag.name)}
            className="transition-all hover:scale-110 hover:brightness-125"
            style={{
              color: tag.color,
              fontSize: getFontSize(tag.count),
              opacity: getOpacity(tag.count),
              fontWeight: 500,
            }}
            title={`${tag.count} ${t('tags.notes')}`}
          >
            {tag.name}
          </button>
        ))}
      </div>
    </div>
  )
}
