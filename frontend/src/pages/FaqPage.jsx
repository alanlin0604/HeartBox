import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'

const FAQ_KEYS = ['privacy', 'aiSafety', 'data', 'crisis', 'free', 'delete', 'languages']

/**
 * Public /faq with collapsible questions. Question / answer text lives
 * entirely in locale JSON so non-engineering teammates can edit copy
 * without a PR.
 */
export default function FaqPage() {
  const { t } = useLang()
  const [open, setOpen] = useState(null)
  useEffect(() => { document.title = `${t('faq.title')} — ${t('app.name')}` }, [t])
  return (
    <div className="min-h-screen max-w-2xl mx-auto px-4 py-12 space-y-8">
      <header className="space-y-2 text-center">
        <h1 className="text-3xl font-bold">{t('faq.title')}</h1>
        <p className="opacity-70 text-sm">{t('faq.subtitle')}</p>
      </header>
      <div className="space-y-3">
        {FAQ_KEYS.map((k) => (
          <details
            key={k}
            open={open === k}
            onToggle={(e) => setOpen(e.currentTarget.open ? k : null)}
            className="rounded-lg border border-white/10 bg-white/5 p-4 transition-colors"
          >
            <summary className="cursor-pointer font-medium select-none">
              {t(`faq.q.${k}`)}
            </summary>
            <p className="text-sm opacity-80 leading-relaxed pt-3">{t(`faq.a.${k}`)}</p>
          </details>
        ))}
      </div>
      <footer className="text-sm text-center pt-6 border-t border-white/10 space-x-4">
        <Link to="/about" className="underline opacity-70 hover:opacity-100">{t('about.title')}</Link>
        <Link to="/privacy" className="underline opacity-70 hover:opacity-100">{t('legal.privacy')}</Link>
        <Link to="/terms" className="underline opacity-70 hover:opacity-100">{t('legal.terms')}</Link>
      </footer>
    </div>
  )
}
