import { useEffect, useState } from 'react'
import { reviewAPI } from '../api/reviews'
import { useLang } from '../context/LanguageContext'
import { Link } from 'react-router-dom'

export default function OnThisDay() {
  const { t } = useLang()
  const [memories, setMemories] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadMemories()
  }, [])

  async function loadMemories() {
    try:
      setLoading(true)
      const data = await reviewAPI.getOnThisDay()
      setMemories(data)
    } catch (err) {
      console.error('Failed to load memories:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('review.onThisDay')}</h2>
        <p className="text-sm text-slate-400">{t('loading')}</p>
      </div>
    )
  }

  if (memories.length === 0) {
    return (
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('review.onThisDay')}</h2>
        <p className="text-sm text-slate-400">{t('review.noMemories')}</p>
      </div>
    )
  }

  const getSentimentColor = (score) => {
    if (score >= 0.3) return 'text-green-400'
    if (score <= -0.3) return 'text-red-400'
    return 'text-slate-400'
  }

  const getSentimentEmoji = (score) => {
    if (score >= 0.5) return '😊'
    if (score >= 0.3) return '🙂'
    if (score <= -0.5) return '😢'
    if (score <= -0.3) return '😔'
    return '😐'
  }

  return (
    <div className="glass p-6">
      <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
        <span>📅</span>
        {t('review.onThisDay')}
      </h2>

      <div className="space-y-4">
        {memories.map((memory) => (
          <div key={memory.year} className="p-4 rounded-lg bg-white/5 border border-white/10">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-purple-400">
                {t('review.yearsAgo', { count: memory.years_ago })}
              </h3>
              <span className="text-xs text-slate-400">{memory.date}</span>
            </div>

            <div className="space-y-2">
              {memory.notes.map((note) => (
                <Link
                  key={note.id}
                  to={`/journal/${note.id}`}
                  className="block p-3 rounded bg-white/5 hover:bg-white/10 transition-colors"
                >
                  <div className="flex items-start gap-2">
                    <span className="text-2xl">
                      {getSentimentEmoji(note.sentiment_score)}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm line-clamp-2">{note.preview}</p>
                      {note.sentiment_score !== null && (
                        <span className={`text-xs ${getSentimentColor(note.sentiment_score)}`}>
                          {t('mood.score')}: {note.sentiment_score.toFixed(2)}
                        </span>
                      )}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
