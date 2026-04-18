import { useState } from 'react'
import { useLang } from '../context/LanguageContext'
import { updateProfile } from '../api/auth'

export default function OnboardingModal({ onComplete }) {
  const { t } = useLang()
  const [step, setStep] = useState(0)

  const steps = [
    { titleKey: 'onboarding.welcomeTitle', descKey: 'onboarding.welcomeDesc', icon: '/logo.png' },
    { titleKey: 'onboarding.journalTitle', descKey: 'onboarding.journalDesc', icon: '/icons/日誌.webp' },
    { titleKey: 'onboarding.exploreTitle', descKey: 'onboarding.exploreDesc', icon: '/icons/功能指南.webp' },
  ]

  const handleComplete = async () => {
    try {
      await updateProfile({ onboarding_completed: true })
    } catch { /* ignore */ }
    onComplete()
  }

  const current = steps[step]
  const isLast = step === steps.length - 1

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="popup-panel p-6 w-full max-w-md space-y-6 text-center" role="dialog" aria-modal="true">
        <img src={current.icon} alt="" className="w-16 h-16 mx-auto" />
        <h2 className="text-xl font-bold">{t(current.titleKey)}</h2>
        <p className="opacity-70">{t(current.descKey)}</p>

        {/* Step indicators */}
        <div className="flex justify-center gap-2">
          {steps.map((_, i) => (
            <div key={i} className={`w-2 h-2 rounded-full ${i === step ? 'bg-purple-500' : 'bg-gray-400/30'}`} />
          ))}
        </div>

        <div className="flex justify-between">
          {step > 0 ? (
            <button onClick={() => setStep(step - 1)} className="btn-secondary">{t('common.goBack')}</button>
          ) : (
            <div />
          )}
          {isLast ? (
            <button onClick={handleComplete} className="btn-primary">{t('onboarding.complete')}</button>
          ) : (
            <button onClick={() => setStep(step + 1)} className="btn-primary">{t('onboarding.next')}</button>
          )}
        </div>
      </div>
    </div>
  )
}
