import { useState, useEffect } from 'react'
import { getArticles } from '../api/wellness'
import { useLang } from '../context/LanguageContext'
import LoadingSpinner from '../components/LoadingSpinner'

const CATEGORIES = [
  { value: '', labelKey: 'learn.allCategories' },
  { value: 'cbt', labelKey: 'learn.cbt' },
  { value: 'mindfulness', labelKey: 'learn.mindfulness' },
  { value: 'emotion', labelKey: 'learn.emotion' },
  { value: 'stress', labelKey: 'learn.stress' },
  { value: 'sleep', labelKey: 'learn.sleep' },
]

const LANG_FIELD_MAP = { 'zh-TW': 'zh', en: 'en', ja: 'ja' }

export default function PsychoContentPage() {
  const { t, lang } = useLang()
  const [articles, setArticles] = useState([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState('')
  const [expandedId, setExpandedId] = useState(null)

  useEffect(() => { document.title = `${t('nav.learn')} — ${t('app.name')}` }, [t])

  useEffect(() => {
    setLoading(true)
    getArticles(category)
      .then((res) => setArticles(res.data?.results || res.data || []))
      .catch(() => setArticles([]))
      .finally(() => setLoading(false))
  }, [category])

  const langKey = LANG_FIELD_MAP[lang] || 'en'

  return (
    <div className="space-y-6 mt-4 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold">{t('nav.learn')}</h1>

      {/* Category filter */}
      <div className="flex flex-wrap gap-2">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.value}
            onClick={() => setCategory(cat.value)}
            className={`text-sm px-4 py-2 rounded-lg transition-colors ${
              category === cat.value
                ? 'bg-purple-500/30 text-purple-400'
                : 'opacity-60 hover:opacity-100'
            }`}
          >
            {t(cat.labelKey)}
          </button>
        ))}
      </div>

      {loading ? <LoadingSpinner /> : articles.length === 0 ? (
        <p className="text-sm opacity-60 text-center py-12">{t('learn.noArticles')}</p>
      ) : (
        <div className="space-y-3">
          {articles.map((article) => {
            const title = article[`title_${langKey}`] || article.title_en
            const content = article[`content_${langKey}`] || article.content_en
            const isExpanded = expandedId === article.id

            return (
              <div key={article.id} className="glass overflow-hidden">
                <button
                  onClick={() => setExpandedId(isExpanded ? null : article.id)}
                  className="w-full p-4 flex items-center justify-between text-left hover:bg-purple-500/5 transition-colors cursor-pointer"
                >
                  <div>
                    <h3 className="font-semibold">{title}</h3>
                    <div className="flex items-center gap-3 mt-1 text-xs opacity-50">
                      <span className="px-2 py-0.5 rounded bg-purple-500/15 text-purple-400">
                        {t(`learn.${article.category}`)}
                      </span>
                      <span>{article.reading_time} {t('learn.minRead')}</span>
                    </div>
                  </div>
                  <span className={`transition-transform text-lg opacity-50 ${isExpanded ? 'rotate-180' : ''}`}>
                    &#9660;
                  </span>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-4 pt-0">
                    <div className="border-t border-[var(--card-border)] pt-4 prose prose-invert max-w-none text-sm leading-relaxed whitespace-pre-wrap opacity-80">
                      {content}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
