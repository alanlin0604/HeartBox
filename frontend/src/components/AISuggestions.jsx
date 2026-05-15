import { useEffect, useState } from 'react'
import { aiAPI } from '../api/ai'
import { useLang } from '../context/LanguageContext'

export default function AISuggestions({ onUsePrompt }) {
  const { t } = useLang()
  const [suggestions, setSuggestions] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expandedSections, setExpandedSections] = useState({
    prompt: true,
    insights: false,
    questions: false,
  })

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await aiAPI.getSuggestions()
        if (!cancelled) setSuggestions(data)
      } catch (err) {
        if (cancelled) return
        console.error('Failed to load AI suggestions:', err)
        setError(err.response?.data?.error || t('ai.loadError'))
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [t])

  function toggleSection(section) {
    setExpandedSections((prev) => ({
      ...prev,
      [section]: !prev[section],
    }))
  }

  function handleUsePrompt() {
    if (onUsePrompt && suggestions?.writing_prompt) {
      onUsePrompt(suggestions.writing_prompt.prompt)
    }
  }

  if (loading) {
    return (
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('ai.suggestions')}</h2>
        <p className="text-sm text-slate-400">{t('loading')}</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('ai.suggestions')}</h2>
        <p className="text-sm text-slate-400">{error}</p>
      </div>
    )
  }

  if (!suggestions) return null

  return (
    <div className="space-y-4">
      {/* Writing Prompt */}
      {suggestions.writing_prompt && (
        <div className="glass p-6">
          <button
            onClick={() => toggleSection('prompt')}
            className="w-full flex items-center justify-between text-left"
          >
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <span>💡</span>
              {t('ai.writingPrompt')}
            </h2>
            <span className="text-slate-400">{expandedSections.prompt ? '▼' : '▶'}</span>
          </button>

          {expandedSections.prompt && (
            <div className="mt-4">
              <p className="text-base mb-3 text-slate-200">
                {suggestions.writing_prompt.prompt}
              </p>
              {onUsePrompt && (
                <button
                  onClick={handleUsePrompt}
                  className="px-4 py-2 bg-orange-500/20 hover:bg-orange-500/30 border border-orange-500/30 rounded-lg text-sm transition-colors"
                >
                  {t('ai.usePrompt')}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Emotional Insights */}
      {suggestions.insights && suggestions.insights.length > 0 && (
        <div className="glass p-6">
          <button
            onClick={() => toggleSection('insights')}
            className="w-full flex items-center justify-between text-left"
          >
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <span>🧠</span>
              {t('ai.insights')}
            </h2>
            <span className="text-slate-400">{expandedSections.insights ? '▼' : '▶'}</span>
          </button>

          {expandedSections.insights && (
            <div className="mt-4 space-y-3">
              {suggestions.insights.map((insight, index) => (
                <div
                  key={index}
                  className="p-4 rounded-lg bg-white/5 border border-white/10"
                >
                  <div className="flex items-start gap-3">
                    <span className="text-2xl flex-shrink-0">{insight.icon}</span>
                    <p className="text-sm text-slate-200">{insight.message}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Reflection Questions */}
      {suggestions.reflection_questions && suggestions.reflection_questions.length > 0 && (
        <div className="glass p-6">
          <button
            onClick={() => toggleSection('questions')}
            className="w-full flex items-center justify-between text-left"
          >
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <span>❓</span>
              {t('ai.reflectionQuestions')}
            </h2>
            <span className="text-slate-400">{expandedSections.questions ? '▼' : '▶'}</span>
          </button>

          {expandedSections.questions && (
            <div className="mt-4 space-y-2">
              {suggestions.reflection_questions.map((question, index) => (
                <div
                  key={index}
                  className="p-3 rounded-lg bg-white/5 border border-white/10 hover:border-orange-500/30 transition-colors cursor-pointer"
                  onClick={() => onUsePrompt && onUsePrompt(question)}
                >
                  <p className="text-sm text-slate-200">• {question}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <p className="text-xs text-slate-500 text-center">
        {t('ai.suggestionsDisclaimer')}
      </p>
    </div>
  )
}
