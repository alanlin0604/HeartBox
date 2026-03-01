import { useEffect, useState } from 'react'
import { useLang } from '../context/LanguageContext'
import { getAchievements, checkAchievements } from '../api/achievements'
import LoadingSpinner from '../components/LoadingSpinner'
import { useToast } from '../context/ToastContext'
import { LOCALE_MAP } from '../utils/locales'

const CATEGORIES = ['all', 'writing', 'consistency', 'mood', 'social', 'explore', 'wellness']

export default function AchievementsPage() {
  const { t, lang } = useLang()
  const toast = useToast()
  const [achievements, setAchievements] = useState([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState('all')
  const [checking, setChecking] = useState(false)

  useEffect(() => {
    document.title = `${t('achievement.title')} — ${t('app.name')}`
  }, [t])

  useEffect(() => {
    loadAchievements()
  }, [])

  const loadAchievements = async () => {
    setLoading(true)
    try {
      const res = await getAchievements()
      setAchievements(res.data)
    } catch {
      toast?.error(t('common.operationFailed'))
    } finally {
      setLoading(false)
    }
  }

  const handleCheck = async () => {
    setChecking(true)
    try {
      const res = await checkAchievements()
      if (res.data.newly_unlocked?.length > 0) {
        toast?.success(
          `${t('achievement.newUnlock')} ${res.data.newly_unlocked.map((id) => t(`achievement.${id}`)).join(', ')}`
        )
      }
      await loadAchievements()
    } catch {
      toast?.error(t('common.operationFailed'))
    } finally {
      setChecking(false)
    }
  }

  const filtered = category === 'all'
    ? achievements
    : achievements.filter((a) => a.category === category)

  const unlockedCount = achievements.filter((a) => a.unlocked).length
  const totalCount = achievements.length

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-6 mt-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('achievement.title')}</h1>
        <div className="flex items-center gap-3">
          <span className="text-sm opacity-60">
            {unlockedCount}/{totalCount}
          </span>
          <button
            onClick={handleCheck}
            disabled={checking}
            className="btn-secondary text-sm"
          >
            {checking ? t('common.loading') : t('achievement.checkNow')}
          </button>
        </div>
      </div>

      {/* Category tabs */}
      <div className="glass p-2 flex gap-2 flex-wrap">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            onClick={() => setCategory(cat)}
            className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
              category === cat
                ? 'bg-purple-500/30 text-purple-500'
                : 'opacity-60 hover:opacity-100'
            }`}
          >
            {t(`achievement.cat_${cat}`)}
          </button>
        ))}
      </div>

      {/* Achievement grid */}
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
        {filtered.map((a) => (
          <div
            key={a.id}
            className={`glass-card p-5 space-y-3 transition-all ${
              a.unlocked
                ? 'border-yellow-500/40 shadow-[0_0_15px_rgba(234,179,8,0.15)]'
                : 'opacity-70'
            }`}
          >
            {/* Top row */}
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <span className="text-2xl">{a.unlocked ? getIcon(a.icon) : '\u{1F512}'}</span>
                <div>
                  <h3 className="font-semibold text-sm">
                    {t(`achievement.${a.id}`)}
                  </h3>
                  <p className="text-xs opacity-50">
                    {t(`achievement.${a.id}_desc`)}
                  </p>
                </div>
              </div>
              {a.unlocked && (
                <span className="text-green-500 text-xs font-medium whitespace-nowrap">
                  {'\u2713'} {t('achievement.unlocked')}
                </span>
              )}
            </div>

            {/* Progress bar */}
            <div>
              <div className="flex justify-between text-xs opacity-50 mb-1">
                <span>{a.current}/{a.threshold}</span>
                {a.unlocked && a.unlocked_at && (
                  <span>{new Date(a.unlocked_at).toLocaleDateString(LOCALE_MAP[lang] || lang)}</span>
                )}
              </div>
              <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all duration-500 ${
                    a.unlocked
                      ? 'bg-gradient-to-r from-yellow-500 to-amber-400'
                      : 'bg-gradient-to-r from-purple-500 to-pink-500'
                  }`}
                  style={{ width: `${Math.min((a.current / a.threshold) * 100, 100)}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12 opacity-50">
          {t('achievement.noAchievements')}
        </div>
      )}
    </div>
  )
}

function getIcon(iconName) {
  const icons = {
    pencil: '\u{270F}\u{FE0F}',
    notebook: '\u{1F4D3}',
    books: '\u{1F4DA}',
    trophy: '\u{1F3C6}',
    scroll: '\u{1F4DC}',
    fire: '\u{1F525}',
    flame: '\u{1F525}',
    calendar: '\u{1F4C5}',
    compass: '\u{1F9ED}',
    sun: '\u{2600}\u{FE0F}',
    trending_up: '\u{1F4C8}',
    brain: '\u{1F9E0}',
    share: '\u{1F517}',
    calendar_check: '\u{1F4CB}',
    robot: '\u{1F916}',
    chat_dots: '\u{1F4AC}',
    moon: '\u{1F319}',
    sunrise: '\u{1F305}',
    pin: '\u{1F4CC}',
    medal: '\u{1F3C5}',
    camera: '\u{1F4F7}',
    sparkles: '\u{2728}',
    calendar_star: '\u{1F31F}',
    leaf: '\u{1F33F}',
    rainbow: '\u{1F308}',
    handshake: '\u{1F91D}',
    mailbox: '\u{1F4EC}',
    tags: '\u{1F3F7}\u{FE0F}',
    cloud_sun: '\u{26C5}',
    heart: '\u{2764}\u{FE0F}',
  }
  return icons[iconName] || '\u{2B50}'
}
