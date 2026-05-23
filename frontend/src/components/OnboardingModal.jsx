import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'
import { useAuth } from '../context/AuthContext'
import { updateProfile } from '../api/auth'
import { useToast } from '../context/ToastContext'

/**
 * First-launch onboarding. Walks the user through the five headline features
 * (welcome / journal / AI / dashboard / health) and then drops them on the
 * Journal page with a hint toast — no inline editor (kept the flow shorter
 * after users reported it felt long pre-Play-Store launch).
 *
 * Bug 2026-05-24: clicking "重看介紹" in Settings re-flipped onboarding_completed
 * back to false on the backend but no one refreshed AuthContext after finish(),
 * so AuthContext kept user.onboarding_completed === false even after the modal
 * closed. Any subsequent React re-render that re-ran Layout's effect re-opened
 * the modal. Fix: refreshUser() in finish() to keep AuthContext in sync.
 */
export default function OnboardingModal({ onComplete }) {
  const { t } = useLang()
  const { refreshUser } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const [step, setStep] = useState(0)
  const [finishing, setFinishing] = useState(false)

  const intro = [
    {
      titleKey: 'onboarding.welcomeTitle',
      descKey: 'onboarding.welcomeDesc',
      hintKey: null,
      icon: '/logo.png',
    },
    {
      titleKey: 'onboarding.journalTitle',
      descKey: 'onboarding.journalDesc',
      hintKey: 'onboarding.journalHint',
      icon: '/icons/nav-journal.svg',
    },
    {
      titleKey: 'onboarding.aiTitle',
      descKey: 'onboarding.aiDesc',
      hintKey: 'onboarding.aiHint',
      icon: '/icons/ai-chat.svg',
    },
    {
      titleKey: 'onboarding.dashboardTitle',
      descKey: 'onboarding.dashboardDesc',
      hintKey: 'onboarding.dashboardHint',
      icon: '/icons/mood-report.svg',
    },
    {
      titleKey: 'onboarding.healthTitle',
      descKey: 'onboarding.healthDesc',
      hintKey: 'onboarding.healthHint',
      icon: '/icons/breathing.svg',
    },
  ]

  const isLastStep = step === intro.length - 1

  const finish = async ({ navigateToJournal = false } = {}) => {
    if (finishing) return
    setFinishing(true)
    try {
      await updateProfile({ onboarding_completed: true })
    } catch { /* ignore */ }
    // Refresh AuthContext so user.onboarding_completed reflects the new value;
    // otherwise Layout's effect would re-open this modal on the next re-render.
    try {
      await refreshUser()
    } catch { /* ignore */ }
    onComplete()
    if (navigateToJournal) {
      navigate('/')
      toast?.success(t('onboarding.firstNoteHint'))
    }
  }

  const current = intro[step]
  return (
    <Shell>
      <img src={current.icon} alt="" className="w-16 h-16 mx-auto object-contain" />
      <h2 className="text-xl font-bold">{t(current.titleKey)}</h2>
      <p className="opacity-70">{t(current.descKey)}</p>
      {current.hintKey && (
        <div className="text-xs px-3 py-2 rounded-lg bg-orange-500/10 border border-orange-500/30 text-orange-300/90">
          👉 {t(current.hintKey)}
        </div>
      )}
      <StepDots count={intro.length} active={step} />
      <div className="flex justify-between">
        {step > 0 ? (
          <button onClick={() => setStep(step - 1)} className="btn-secondary" disabled={finishing}>{t('common.goBack')}</button>
        ) : <div />}
        <div className="flex gap-2">
          {!isLastStep && (
            <button onClick={() => finish()} className="btn-secondary text-sm opacity-70" disabled={finishing}>
              {t('onboarding.skip')}
            </button>
          )}
          {isLastStep ? (
            <button onClick={() => finish({ navigateToJournal: true })} className="btn-primary" disabled={finishing}>
              {finishing ? t('common.loading') : t('onboarding.complete')}
            </button>
          ) : (
            <button onClick={() => setStep(step + 1)} className="btn-primary">{t('onboarding.next')}</button>
          )}
        </div>
      </div>
    </Shell>
  )
}

function Shell({ children }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="popup-panel p-6 w-full max-w-md space-y-5 text-center" role="dialog" aria-modal="true">
        {children}
      </div>
    </div>
  )
}

function StepDots({ count, active }) {
  return (
    <div className="flex justify-center gap-2">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className={`h-2 rounded-full transition-all ${i === active ? 'w-6 bg-orange-500' : 'w-2 bg-gray-400/30'}`} />
      ))}
    </div>
  )
}
