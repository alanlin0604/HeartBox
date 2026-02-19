import { useEffect } from 'react'
import { useLang } from '../context/LanguageContext'

const FEATURES = [
  { icon: '\u{1F4DD}', titleKey: 'nav.journal', descKey: 'guide.journalDesc' },
  { icon: '\u{1F4CA}', titleKey: 'nav.dashboard', descKey: 'guide.dashboardDesc' },
  { icon: '\u{1F4CB}', titleKey: 'nav.assessments', descKey: 'guide.assessmentsDesc' },
  { icon: '\u{1F4C5}', titleKey: 'nav.weeklySummary', descKey: 'guide.weeklySummaryDesc' },
  { icon: '\u{1F9D8}', titleKey: 'nav.breathe', descKey: 'guide.breatheDesc' },
  { icon: '\u{1F4DA}', titleKey: 'nav.learn', descKey: 'guide.learnDesc' },
  { icon: '\u{1F4AC}', titleKey: 'nav.counselors', descKey: 'guide.counselorsDesc' },
  { icon: '\u{1F916}', titleKey: 'nav.aiChat', descKey: 'guide.aiChatDesc' },
  { icon: '\u{1F3C6}', titleKey: 'nav.achievements', descKey: 'guide.achievementsDesc' },
  { icon: '\u2699\uFE0F', titleKey: 'settings.title', descKey: 'guide.settingsDesc' },
]

export default function GuidePage() {
  const { t } = useLang()

  useEffect(() => {
    document.title = `${t('nav.guide')} \u2014 ${t('app.name')}`
  }, [t])

  return (
    <div className="space-y-6 mt-4 max-w-2xl mx-auto">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold">{t('guide.title')}</h1>
        <p className="text-sm opacity-60">{t('guide.subtitle')}</p>
      </div>

      <div className="space-y-3">
        {FEATURES.map((f) => (
          <div key={f.titleKey} className="glass p-4 flex items-start gap-4">
            <span className="text-2xl mt-0.5">{f.icon}</span>
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold">{t(f.titleKey)}</h3>
              <p className="text-sm opacity-70 mt-1">{t(f.descKey)}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
