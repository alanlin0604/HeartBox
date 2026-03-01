import { useEffect } from 'react'
import { useLang } from '../context/LanguageContext'

const FEATURES = [
  { icon: '/icons/日誌.png', titleKey: 'nav.journal', descKey: 'guide.journalDesc' },
  { icon: '/icons/心情週報月報.png', titleKey: 'nav.dashboard', descKey: 'guide.dashboardDesc' },
  { icon: '/icons/問卷評估.png', titleKey: 'nav.assessments', descKey: 'guide.assessmentsDesc' },
  { icon: '/icons/每週報告.png', titleKey: 'nav.weeklySummary', descKey: 'guide.weeklySummaryDesc' },
  { icon: '/icons/呼吸與冥想.png', titleKey: 'nav.breathe', descKey: 'guide.breatheDesc' },
  { icon: '/icons/學習.png', titleKey: 'nav.learn', descKey: 'guide.learnDesc' },
  { icon: '/icons/諮商師.png', titleKey: 'nav.counselors', descKey: 'guide.counselorsDesc' },
  { icon: '/icons/AI 聊天.png', titleKey: 'nav.aiChat', descKey: 'guide.aiChatDesc' },
  { icon: '/icons/成就.png', titleKey: 'nav.achievements', descKey: 'guide.achievementsDesc' },
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
        <p className="text-sm opacity-60">{t('guide.subtitle')}</p>
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
              <p className="text-sm opacity-70 mt-1">{t(f.descKey)}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
