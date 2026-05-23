import { useState } from 'react'
import { useLang } from '../context/LanguageContext'
import { updateProfile } from '../api/auth'
import { createNote } from '../api/notes'
import { useToast } from '../context/ToastContext'

/**
 * First-launch onboarding. Walks the user through the four headline features
 * (journal / AI / dashboard / Health Connect) before asking them to write
 * their first journal entry inline.
 *
 * Skipping is allowed at every step but the default flow ends in "write
 * something now" because retention curves for mood-journaling apps live and
 * die on day-1 first action.
 */
export default function OnboardingModal({ onComplete }) {
  const { t } = useLang()
  const toast = useToast()
  const [step, setStep] = useState(0)
  const [firstNote, setFirstNote] = useState('')
  const [saving, setSaving] = useState(false)

  // Feature intro slides — concrete UI cues ("點下方『日誌』tab") work better
  // than abstract feature descriptions because new users won't scan the UI
  // until told where to look.
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
  const totalSteps = intro.length + 1 // +1 for the inline first-note step

  const finish = async () => {
    try {
      await updateProfile({ onboarding_completed: true })
    } catch { /* ignore */ }
    onComplete()
  }

  const handleSaveFirst = async () => {
    if (!firstNote.trim()) {
      await finish()
      return
    }
    setSaving(true)
    try {
      await createNote(firstNote.trim())
      toast?.success(t('onboarding.firstNoteSaved'))
    } catch {
      toast?.error(t('common.operationFailed'))
    } finally {
      setSaving(false)
      await finish()
    }
  }

  if (step < intro.length) {
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
        <StepDots count={totalSteps} active={step} />
        <div className="flex justify-between">
          {step > 0 ? (
            <button onClick={() => setStep(step - 1)} className="btn-secondary">{t('common.goBack')}</button>
          ) : <div />}
          <div className="flex gap-2">
            <button onClick={finish} className="btn-secondary text-sm opacity-70">
              {t('onboarding.skip')}
            </button>
            <button onClick={() => setStep(step + 1)} className="btn-primary">{t('onboarding.next')}</button>
          </div>
        </div>
      </Shell>
    )
  }

  // Final step — write first journal entry inline
  return (
    <Shell>
      <h2 className="text-xl font-bold">{t('onboarding.firstNoteTitle')}</h2>
      <p className="opacity-70 text-sm">{t('onboarding.firstNoteDesc')}</p>
      <textarea
        value={firstNote}
        onChange={(e) => setFirstNote(e.target.value)}
        placeholder={t('onboarding.firstNotePlaceholder')}
        rows={5}
        className="w-full p-3 rounded-lg bg-white/5 border border-white/10 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-orange-500/40"
        disabled={saving}
      />
      <StepDots count={totalSteps} active={totalSteps - 1} />
      <div className="flex justify-between">
        <button onClick={() => setStep(intro.length - 1)} className="btn-secondary" disabled={saving}>
          {t('common.goBack')}
        </button>
        <div className="flex gap-2">
          <button onClick={finish} className="btn-secondary" disabled={saving}>
            {t('onboarding.skip')}
          </button>
          <button onClick={handleSaveFirst} className="btn-primary" disabled={saving}>
            {saving ? t('common.loading') : t('onboarding.saveFirst')}
          </button>
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
