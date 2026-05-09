import { useEffect, useState } from 'react'
import { aiAPI } from '../api/ai'
import { useLang } from '../context/LanguageContext'

export default function MoodPrediction() {
  const { t } = useLang()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    loadPredictions()
  }, [])

  async function loadPredictions() {
    try {
      setLoading(true)
      setError(null)
      const result = await aiAPI.getPredictions()
      setData(result)
    } catch (err) {
      console.error('Failed to load predictions:', err)
      setError(err.response?.data?.error || t('prediction.loadError'))
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('prediction.title')}</h2>
        <p className="text-sm text-slate-400">{t('loading')}</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('prediction.title')}</h2>
        <p className="text-sm text-slate-400">{error}</p>
      </div>
    )
  }

  if (!data) return null

  const { prediction, health_tips } = data

  if (!prediction.has_prediction) {
    return (
      <div className="glass p-6">
        <h2 className="text-lg font-semibold mb-4">{t('prediction.title')}</h2>
        <p className="text-sm text-slate-400">{prediction.message}</p>
      </div>
    )
  }

  const getTrendIcon = (trend) => {
    if (trend === 'improving' || trend === 'decreasing') return '📈'
    if (trend === 'declining' || trend === 'increasing') return '📉'
    return '➡️'
  }

  const getTrendColor = (type, trend) => {
    if (type === 'sentiment') {
      if (trend === 'improving') return 'text-green-400'
      if (trend === 'declining') return 'text-red-400'
    } else {
      // stress
      if (trend === 'decreasing') return 'text-green-400'
      if (trend === 'increasing') return 'text-red-400'
    }
    return 'text-slate-400'
  }

  const getWarningColor = (level) => {
    if (level === 'high') return 'border-red-500/30 bg-red-500/10'
    if (level === 'medium') return 'border-yellow-500/30 bg-yellow-500/10'
    if (level === 'positive') return 'border-green-500/30 bg-green-500/10'
    return 'border-slate-500/30 bg-slate-500/10'
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass p-6">
        <h1 className="text-3xl font-bold mb-2 text-transparent bg-clip-text bg-gradient-to-r from-orange-400 to-rose-400">
          {t('prediction.title')}
        </h1>
        <p className="text-slate-400">{t('prediction.subtitle')}</p>
      </div>

      {/* Current Status */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Sentiment */}
        <div className="glass p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span>😊</span>
            {t('prediction.moodTrend')}
          </h2>
          <div className="space-y-3">
            <div>
              <p className="text-sm text-slate-400">{t('prediction.current')}</p>
              <p className="text-2xl font-bold">{prediction.sentiment.current}</p>
            </div>
            <div>
              <p className="text-sm text-slate-400">{t('prediction.trend')}</p>
              <p className={`text-lg font-semibold ${getTrendColor('sentiment', prediction.sentiment.trend)}`}>
                {getTrendIcon(prediction.sentiment.trend)} {t(`prediction.trend_${prediction.sentiment.trend}`)}
              </p>
            </div>
            {Math.abs(prediction.sentiment.slope) > 0.01 && (
              <div>
                <p className="text-sm text-slate-400">{t('prediction.forecast7d')}</p>
                <p className="text-lg">{prediction.sentiment.forecast_7d}</p>
              </div>
            )}
          </div>
        </div>

        {/* Stress */}
        <div className="glass p-6">
          <h2 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span>📊</span>
            {t('prediction.stressTrend')}
          </h2>
          <div className="space-y-3">
            <div>
              <p className="text-sm text-slate-400">{t('prediction.current')}</p>
              <p className="text-2xl font-bold">{prediction.stress.current} / 10</p>
            </div>
            <div>
              <p className="text-sm text-slate-400">{t('prediction.trend')}</p>
              <p className={`text-lg font-semibold ${getTrendColor('stress', prediction.stress.trend)}`}>
                {getTrendIcon(prediction.stress.trend)} {t(`prediction.trend_${prediction.stress.trend}`)}
              </p>
            </div>
            {Math.abs(prediction.stress.slope) > 0.05 && (
              <div>
                <p className="text-sm text-slate-400">{t('prediction.forecast7d')}</p>
                <p className="text-lg">{prediction.stress.forecast_7d} / 10</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Warnings and Alerts */}
      {prediction.warnings && prediction.warnings.length > 0 && (
        <div className="glass p-6">
          <h2 className="text-lg font-semibold mb-4">{t('prediction.alerts')}</h2>
          <div className="space-y-3">
            {prediction.warnings.map((warning, index) => (
              <div
                key={index}
                className={`p-4 rounded-lg border ${getWarningColor(warning.level)}`}
              >
                <div className="flex items-start gap-3">
                  <span className="text-2xl flex-shrink-0">{warning.icon}</span>
                  <p className="text-sm text-slate-200">{warning.message}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {prediction.recommendations && prediction.recommendations.length > 0 && (
        <div className="glass p-6">
          <h2 className="text-lg font-semibold mb-4">{t('prediction.recommendations')}</h2>
          <ul className="space-y-2">
            {prediction.recommendations.map((rec, index) => (
              <li key={index} className="flex items-start gap-2 text-sm text-slate-200">
                <span className="text-orange-400 mt-1">•</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Health Tips */}
      {health_tips && health_tips.length > 0 && (
        <div className="glass p-6">
          <h2 className="text-lg font-semibold mb-4">{t('prediction.healthTips')}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {health_tips.map((tip, index) => (
              <div
                key={index}
                className="p-4 rounded-lg bg-white/5 border border-white/10"
              >
                <div className="flex items-start gap-3">
                  <span className="text-2xl flex-shrink-0">{tip.icon}</span>
                  <p className="text-sm text-slate-200">{tip.tip}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-slate-500 text-center">
        {t('prediction.disclaimer')}
      </p>
    </div>
  )
}
