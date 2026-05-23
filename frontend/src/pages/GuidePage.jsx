import { useEffect } from 'react'
import { useLang } from '../context/LanguageContext'

const FEATURES = [
  { icon: '/icons/nav-journal.svg', titleKey: 'nav.journal', descKey: 'guide.journalDesc' },
  { icon: '/icons/mood-report.svg', titleKey: 'nav.dashboard', descKey: 'guide.dashboardDesc' },
  { icon: '/icons/survey.svg', titleKey: 'nav.assessments', descKey: 'guide.assessmentsDesc' },
  { icon: '/icons/weekly-report.svg', titleKey: 'nav.weeklySummary', descKey: 'guide.weeklySummaryDesc' },
  { icon: '/icons/breathing.svg', titleKey: 'nav.breathe', descKey: 'guide.breatheDesc' },
  { icon: '/icons/learning.svg', titleKey: 'nav.learn', descKey: 'guide.learnDesc' },
  { icon: '/icons/ai-chat.svg', titleKey: 'nav.aiChat', descKey: 'guide.aiChatDesc' },
  { icon: '/icons/achievement.svg', titleKey: 'nav.achievements', descKey: 'guide.achievementsDesc' },
  { icon: '\u2699\uFE0F', titleKey: 'settings.title', descKey: 'guide.settingsDesc', isEmoji: true },
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
        <p className="text-sm text-slate-400">{t('guide.subtitle')}</p>
      </div>

      <div className="space-y-3">
        {FEATURES.map((f) => (
          <div key={f.titleKey} className="glass p-4 flex items-start gap-4">
            {f.isEmoji
              ? <span className="text-2xl mt-0.5">{f.icon}</span>
              : <img src={f.icon} alt="" className="w-9 h-9 object-contain mt-0.5" />
            }
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold">{t(f.titleKey)}</h3>
              <p className="text-sm text-slate-400 mt-1">{t(f.descKey)}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
