import { memo } from 'react'
import { useLang } from '../context/LanguageContext'

const moodColors = {
  positive: 'bg-green-500/20 text-green-600 border-green-500/30',
  neutral: 'bg-yellow-500/20 text-yellow-600 border-yellow-500/30',
  negative: 'bg-red-500/20 text-red-600 border-red-500/30',
  unknown: 'bg-gray-500/20 opacity-60 border-gray-500/30',
}

const moodLabelKeys = {
  positive: 'mood.positive',
  neutral: 'mood.neutral',
  negative: 'mood.negative',
  unknown: 'mood.unknown',
}

function getMoodLevel(score) {
  if (score == null) return 'unknown'
  if (score >= 0.2) return 'positive'
  if (score >= -0.2) return 'neutral'
  return 'negative'
}

export default memo(function MoodBadge({ score }) {
  const { t } = useLang()
  const level = getMoodLevel(score)
  const color = moodColors[level]
  const label = t(moodLabelKeys[level])

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${color}`}>
      {label} {score != null && `(${score.toFixed(2)})`}
    </span>
  )
})
