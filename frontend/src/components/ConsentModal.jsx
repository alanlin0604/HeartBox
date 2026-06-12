import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { submitConsent } from '../api/auth'

/**
 * Post-launch 3-step consent gate. Added 2026-06-02 per thesis-advisor
 * feedback: users must explicitly opt in (or out) of AI training data
 * use, and minors (13-17) need a guardian email confirmation before the
 * account unlocks.
 *
 * Flow:
 *   Step 1 — privacy summary + ToS acceptance (required)
 *   Step 2 — AI training opt-in (independent, declinable)
 *   Step 3 — age band (18+ / 13-17 / under 13)
 *            13-17 prompts for guardian_email; under_13 hard-blocks.
 *
 * Backdrop is non-dismissable (no close button, no escape) — this is a
 * gate, not a notification. ConsentModal returns null after the user
 * submits and AuthContext refreshes the profile.
 */
export default function ConsentModal({ onComplete }) {
  const { t } = useLang()
  const { refreshUser } = useAuth()
  const toast = useToast()

  const [step, setStep] = useState(0)
  const [acceptsTerms, setAcceptsTerms] = useState(false)
  const [consentAi, setConsentAi] = useState(false)
  const [ageBand, setAgeBand] = useState('')
  const [guardianEmail, setGuardianEmail] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const canAdvanceFromStep1 = acceptsTerms
  const canSubmit = ageBand && (ageBand !== '13_17' || guardianEmail.trim().length > 3)

  const handleSubmit = async () => {
    if (submitting) return
    if (!canSubmit) return
    setSubmitting(true)
    try {
      await submitConsent({
        acceptsTerms,
        consentAiTraining: consentAi,
        ageBand,
        guardianEmail: guardianEmail.trim(),
      })
      await refreshUser()
      if (ageBand === '13_17') {
        toast?.success(t('consent.guardianEmailSent'))
      } else {
        toast?.success(t('consent.thanks'))
      }
      onComplete?.()
    } catch (err) {
      const code = err?.response?.data?.detail || ''
      if (code === 'consent.under_13_not_allowed') {
        toast?.error(t('consent.under13NotAllowed'))
      } else {
        toast?.error(t('consent.submitFailed'))
      }
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm">
      <div className="popup-panel p-6 w-full max-w-lg space-y-5" role="dialog" aria-modal="true">
        <header className="flex items-center gap-3 pb-3 border-b border-[var(--card-border)]">
          <img src="/logo.png" alt="" className="w-10 h-10 object-contain" />
          <div>
            <h2 className="text-lg font-bold">{t('consent.title')}</h2>
            <p className="text-xs opacity-60">{t('consent.subtitle')}</p>
          </div>
        </header>

        <StepDots count={3} active={step} />

        {step === 0 && (
          <section className="space-y-3 text-sm">
            <h3 className="font-semibold">{t('consent.step1Title')}</h3>
            <ul className="space-y-1.5 opacity-80 pl-4 list-disc">
              <li>{t('consent.s1WeCollect')}</li>
              <li>{t('consent.s1WeStore')}</li>
              <li>{t('consent.s1WeNever')}</li>
            </ul>
            <div className="flex gap-3 pt-2 text-xs">
              <Link to="/privacy" target="_blank" className="underline opacity-70 hover:opacity-100">
                {t('legal.privacy')}
              </Link>
              <Link to="/terms" target="_blank" className="underline opacity-70 hover:opacity-100">
                {t('legal.terms')}
              </Link>
            </div>
            <label className="flex items-start gap-2 mt-3 cursor-pointer">
              <input
                type="checkbox"
                checked={acceptsTerms}
                onChange={(e) => setAcceptsTerms(e.target.checked)}
                className="mt-0.5 w-4 h-4 accent-orange-500"
              />
              <span className="text-sm">{t('consent.s1Accept')}</span>
            </label>
          </section>
        )}

        {step === 1 && (
          <section className="space-y-3 text-sm">
            <h3 className="font-semibold">{t('consent.step2Title')}</h3>
            <p className="opacity-75">{t('consent.s2Desc')}</p>
            <div className="rounded-lg border border-orange-500/30 bg-orange-500/5 p-3 space-y-2 text-xs">
              <p className="font-medium opacity-90">{t('consent.s2WhatWeDo')}</p>
              <ul className="space-y-1 opacity-75 pl-4 list-disc">
                <li>{t('consent.s2Anonymize')}</li>
                <li>{t('consent.s2NoIdentity')}</li>
                <li>{t('consent.s2OptOutAnytime')}</li>
              </ul>
            </div>
            <div className="space-y-2 pt-1">
              <label className="flex items-start gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="ai-consent"
                  checked={consentAi === true}
                  onChange={() => setConsentAi(true)}
                  className="mt-0.5 w-4 h-4 accent-orange-500"
                />
                <span>{t('consent.s2OptIn')}</span>
              </label>
              <label className="flex items-start gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="ai-consent"
                  checked={consentAi === false}
                  onChange={() => setConsentAi(false)}
                  className="mt-0.5 w-4 h-4 accent-orange-500"
                />
                <span>{t('consent.s2OptOut')}</span>
              </label>
            </div>
            <p className="text-xs opacity-50 pt-1">{t('consent.s2NoImpact')}</p>
          </section>
        )}

        {step === 2 && (
          <section className="space-y-3 text-sm">
            <h3 className="font-semibold">{t('consent.step3Title')}</h3>
            <p className="opacity-75">{t('consent.s3Desc')}</p>
            <div className="space-y-2 pt-1">
              {[
                { value: '18_plus',  label: t('consent.s3Adult') },
                { value: '13_17',    label: t('consent.s3Minor') },
                { value: 'under_13', label: t('consent.s3Under13') },
              ].map(opt => (
                <label key={opt.value} className="flex items-start gap-2 cursor-pointer">
                  <input
                    type="radio"
                    name="age-band"
                    checked={ageBand === opt.value}
                    onChange={() => setAgeBand(opt.value)}
                    className="mt-0.5 w-4 h-4 accent-orange-500"
                  />
                  <span>{opt.label}</span>
                </label>
              ))}
            </div>
            {ageBand === '13_17' && (
              <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 space-y-2">
                <p className="text-xs opacity-80">{t('consent.s3GuardianExplain')}</p>
                <input
                  type="email"
                  value={guardianEmail}
                  onChange={(e) => setGuardianEmail(e.target.value)}
                  placeholder={t('consent.s3GuardianEmailPlaceholder')}
                  className="w-full p-2 rounded-md bg-white/5 border border-white/15 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/40"
                />
              </div>
            )}
            {ageBand === 'under_13' && (
              <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-3 text-xs text-red-400">
                {t('consent.s3Under13Block')}
              </div>
            )}
          </section>
        )}

        <footer className="flex justify-between pt-3 border-t border-[var(--card-border)]">
          {step > 0 ? (
            <button
              onClick={() => setStep(step - 1)}
              disabled={submitting}
              className="btn-secondary text-sm"
            >
              {t('common.goBack')}
            </button>
          ) : <div />}
          {step < 2 ? (
            <button
              onClick={() => setStep(step + 1)}
              disabled={step === 0 && !canAdvanceFromStep1}
              className="btn-primary text-sm disabled:opacity-50"
            >
              {t('common.next')}
            </button>
          ) : (
            <button
              onClick={handleSubmit}
              disabled={!canSubmit || ageBand === 'under_13' || submitting}
              className="btn-primary text-sm disabled:opacity-50"
            >
              {submitting ? t('common.loading') : t('consent.submit')}
            </button>
          )}
        </footer>
      </div>
    </div>
  )
}

function StepDots({ count, active }) {
  return (
    <div className="flex justify-center gap-2">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className={`h-2 rounded-full transition-all ${i === active ? 'w-6 bg-orange-500' : 'w-2 bg-gray-400/30'}`}
        />
      ))}
    </div>
  )
}
