import { useEffect, useState, useMemo } from 'react'
import { useLang } from '../context/LanguageContext'
import { getAchievements } from '../api/achievements'
import LoadingSpinner from '../components/LoadingSpinner'
import DashboardSection from '../components/DashboardSection'
import { useToast } from '../context/ToastContext'
import { LOCALE_MAP } from '../utils/locales'

const CATEGORIES = [
  'all',
  'writing', 'consistency', 'mood',
  'social', 'friends', 'community',
  'wellness', 'health', 'explore', 'meta',
]

export default function AchievementsPage() {
  const { t, lang } = useLang()
  const toast = useToast()
  const [achievements, setAchievements] = useState([])
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState('all')

  useEffect(() => {
    document.title = `${t('achievement.title')} — ${t('app.name')}`
  }, [t])

  // Show current state on mount. New unlocks are surfaced as real-time
  // toasts via the notifications WebSocket (see NotificationBell), so we
  // don't need to also run /check on mount — that path runs _get_progress
  // again (~15 queries / 400 ms) and the data is already up to date here.
  useEffect(() => {
    let cancelled = false
    getAchievements()
      .then((res) => { if (!cancelled) setAchievements(res.data) })
      .catch(() => { if (!cancelled) toast?.error(t('achievement.checkFailed')) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [toast, t])

  const filtered = useMemo(() => (
    category === 'all'
      ? achievements
      : achievements.filter((a) => a.category === category)
  ), [category, achievements])

  // Split into two visual buckets so the user immediately sees what
  // they've earned vs what they're still working toward — was a single
  // grid before, which buried unlocked badges among 70+ in-progress
  // ones (we crossed 100 total on 2026-05-24). In-progress sorted by
  // proximity to threshold so the next-easy-win is on top.
  const unlocked = useMemo(() => filtered.filter((a) => a.unlocked), [filtered])
  const inProgress = useMemo(() => {
    return filtered
      .filter((a) => !a.unlocked)
      .sort((a, b) => (b.current / b.threshold) - (a.current / a.threshold))
  }, [filtered])

  const unlockedCount = achievements.filter((a) => a.unlocked).length
  const totalCount = achievements.length
  const percent = totalCount > 0 ? Math.round((unlockedCount / totalCount) * 100) : 0

  if (loading) return <LoadingSpinner />

  return (
    <div className="space-y-8 mt-4 pb-8">
      {/* Header with overall progress bar \u2014 replaces the bare "12/107"
          counter with a visual completion bar so users get an at-a-glance
          sense of how far they are. */}
      <div className="glass-card p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">{t('achievement.title')}</h1>
          <span className="text-sm opacity-70">
            {unlockedCount}/{totalCount} <span className="opacity-50">({percent}%)</span>
          </span>
        </div>
        <div className="w-full h-2 rounded-full bg-white/10 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-yellow-500 to-amber-400 transition-all duration-500"
            style={{ width: `${percent}%` }}
          />
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
                ? 'bg-orange-500/30 text-orange-500'
                : 'opacity-60 hover:opacity-100'
            }`}
          >
            {t(`achievement.cat_${cat}`)}
          </button>
        ))}
      </div>

      {/* === Unlocked section === */}
      {unlocked.length > 0 && (
        <DashboardSection
          id="ach-unlocked"
          title={t('achievement.section.unlocked')}
          subtitle={`${unlocked.length}`}
        >
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {unlocked.map((a) => <AchievementCard key={a.id} a={a} t={t} lang={lang} />)}
          </div>
        </DashboardSection>
      )}

      {/* === In-progress section === */}
      {inProgress.length > 0 && (
        <DashboardSection
          id="ach-progress"
          title={t('achievement.section.inProgress')}
          subtitle={`${inProgress.length}`}
        >
          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
            {inProgress.map((a) => <AchievementCard key={a.id} a={a} t={t} lang={lang} />)}
          </div>
        </DashboardSection>
      )}

      {filtered.length === 0 && (
        <div className="text-center py-12 opacity-50">
          {t('achievement.noAchievements')}
        </div>
      )}
    </div>
  )
}

function AchievementCard({ a, t, lang }) {
  return (
    <div
      className={`glass-card p-5 space-y-3 transition-all ${
        a.unlocked
          ? 'border-yellow-500/40 shadow-[0_0_15px_rgba(234,179,8,0.15)]'
          : 'opacity-75'
      }`}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{a.unlocked ? getIcon(a.icon) : '\u{1F512}'}</span>
          <div>
            <h3 className="font-semibold text-sm">{t(`achievement.${a.id}`)}</h3>
            <p className="text-xs text-slate-400">{t(`achievement.${a.id}_desc`)}</p>
          </div>
        </div>
        {a.unlocked && (
          <span className="text-green-500 text-xs font-medium whitespace-nowrap">
            {'\u2713'} {t('achievement.unlocked')}
          </span>
        )}
      </div>
      <div>
        <div className="flex justify-between text-xs text-slate-400 mb-1">
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
                : 'bg-gradient-to-r from-orange-500 to-rose-500'
            }`}
            style={{ width: `${Math.min((a.current / a.threshold) * 100, 100)}%` }}
          />
        </div>
      </div>
    </div>
  )
}

function getIcon(iconName) {
  const icons = {
    // Original set (matches the first batch of ACHIEVEMENT_DEFINITIONS)
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
    // Friends / community / health / wellness (existing newer batch)
    user_plus: '\u{1F465}',
    users: '\u{1F46A}',
    gift: '\u{1F381}',
    message_heart: '\u{1F496}',
    megaphone: '\u{1F4E3}',
    hands_helping: '\u{1F91D}',
    sparkle_heart: '\u{1F495}',
    bed: '\u{1F6CF}\u{FE0F}',
    moon_stars: '\u{1F31C}',
    star_filled: '\u{2B50}',
    watch: '\u{231A}',
    footprints: '\u{1F463}',
    target: '\u{1F3AF}',
    flame_small: '\u{1F525}',
    crown: '\u{1F451}',
    lungs: '\u{1FAC1}',
    lotus: '\u{1FAB7}',
    clipboard_check: '\u{1F4CB}',
    graph_up: '\u{1F4C8}',
    layout: '\u{1F5C2}\u{FE0F}',
    robot_star: '\u{1F916}',
    medal_bronze: '\u{1F949}',
    medal_gold: '\u{1F947}',
    // 2026-05-24 expansion — 55 new icons
    trophy_silver: '\u{1F948}',
    trophy_gold: '\u{1F3C6}',
    scroll_long: '\u{1F4DC}',
    sun_morning: '\u{1F305}',
    moon_evening: '\u{1F30C}',
    owl: '\u{1F989}',
    photo_stack: '\u{1F5BC}\u{FE0F}',
    book_open: '\u{1F4D6}',
    calendar_full: '\u{1F5D3}\u{FE0F}',
    flame_blue: '\u{1F525}',
    flame_purple: '\u{1F525}',
    flame_diamond: '\u{1F48E}',
    crown_gold: '\u{1F451}',
    phoenix: '\u{1F985}',
    smile_big: '\u{1F60A}',
    leaf_zen: '\u{1F343}',
    rainbow_full: '\u{1F308}',
    brain_star: '\u{1F9E0}',
    bed_clouds: '\u{1F6CC}',
    bed_stars: '\u{1F6CC}',
    log_sleep: '\u{1F4D3}',
    crescent_moon: '\u{1F319}',
    sneaker_streak: '\u{1F45F}',
    sneaker_gold: '\u{1F3C5}',
    watch_pulse: '\u{231A}',
    health_grid: '\u{1F9EC}',
    target_3: '\u{1F3AF}',
    target_5: '\u{1F3AF}',
    lungs_air: '\u{1FAC1}',
    lungs_deep: '\u{1FAC1}',
    lotus_open: '\u{1FAB7}',
    wellness_crown: '\u{1F451}',
    wind_streak: '\u{1F4A8}',
    mosaic: '\u{1F9E9}',
    tags_full: '\u{1F3F7}\u{FE0F}',
    compass_star: '\u{1F9ED}',
    activity_grid: '\u{1F3DF}\u{FE0F}',
    weather_full: '\u{1F324}\u{FE0F}',
    clipboard_star: '\u{1F4CB}',
    pin_stack: '\u{1F4CC}',
    robot_pro: '\u{1F916}',
    robot_master: '\u{1F47E}',
    robot_streak: '\u{1F916}',
    users_group: '\u{1F46A}',
    users_crowd: '\u{1F465}',
    gift_stack: '\u{1F381}',
    message_heart_full: '\u{1F49E}',
    gift_received: '\u{1F389}',
    megaphone_5: '\u{1F4E3}',
    megaphone_pro: '\u{1F4E3}',
    sparkle_star: '\u{1F31F}',
    calendar_active: '\u{1F4C5}',
    thumbs_pro: '\u{1F44D}',
    medal_silver: '\u{1F948}',
    medal_diamond: '\u{1F48E}',
  }
  return icons[iconName] || '\u{2B50}'
}
