import { useEffect, useState } from 'react'
import { reminderAPI } from '../api/reminders'
import { useLang } from '../context/LanguageContext'

export default function StreakCounter({ compact = false }) {
  const { t } = useLang()
  const [streak, setStreak] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStreak()
  }, [])

  async function loadStreak() {
    try {
      setLoading(true)
      const data = await reminderAPI.getStreak()
      setStreak(data)
    } catch (err) {
      console.error('Failed to load streak:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className={`glass ${compact ? 'p-4' : 'p-6'}`}>
        <p className="text-sm text-slate-400">{t('loading')}</p>
      </div>
    )
  }

  if (!streak) return null

  const getStreakEmoji = (days) => {
    if (days >= 365) return '🌟'
    if (days >= 100) return '👑'
    if (days >= 60) return '🎯'
    if (days >= 30) return '🏆'
    if (days >= 14) return '💪'
    if (days >= 7) return '⭐'
    if (days >= 3) return '🔥'
    return '📝'
  }

  if (compact) {
    return (
      <div className="glass p-4 flex items-center gap-3">
        <span className="text-3xl">{getStreakEmoji(streak.current_streak)}</span>
        <div>
          <p className="text-2xl font-bold">{streak.current_streak}</p>
          <p className="text-xs text-slate-400">{t('streak.days')}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="glass p-6">
      <h2 className="text-lg font-semibold mb-4">{t('streak.title')}</h2>
      <div className="flex items-center justify-around gap-6">
        <div className="text-center">
          <div className="text-5xl mb-2">{getStreakEmoji(streak.current_streak)}</div>
          <p className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400">
            {streak.current_streak}
          </p>
          <p className="text-sm text-slate-400 mt-1">{t('streak.current')}</p>
        </div>

        <div className="h-16 w-px bg-white/10" />

        <div className="text-center">
          <div className="text-4xl mb-2">🏅</div>
          <p className="text-2xl font-semibold">{streak.longest_streak}</p>
          <p className="text-sm text-slate-400 mt-1">{t('streak.longest')}</p>
        </div>

        <div className="h-16 w-px bg-white/10" />

        <div className="text-center">
          <div className="text-4xl mb-2">📊</div>
          <p className="text-2xl font-semibold">{streak.total_entries}</p>
          <p className="text-sm text-slate-400 mt-1">{t('streak.total')}</p>
        </div>
      </div>

      {streak.current_streak > 0 && (
        <div className="mt-4 p-3 rounded-lg bg-gradient-to-r from-purple-500/10 to-pink-500/10 border border-purple-500/20">
          <p className="text-sm text-center">
            {streak.current_streak === 1
              ? t('streak.keepGoing')
              : t('streak.amazing', { days: streak.current_streak })}
          </p>
        </div>
      )}
    </div>
  )
}
