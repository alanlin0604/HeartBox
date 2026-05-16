import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'

/**
 * Public /about page. Mostly content-driven via locale keys so the
 * owner can update copy without code changes. Three sections — mission,
 * how it works, who we are — kept short and skim-friendly.
 */
export default function AboutPage() {
  const { t } = useLang()
  useEffect(() => { document.title = `${t('about.title')} — ${t('app.name')}` }, [t])
  return (
    <div className="min-h-screen max-w-3xl mx-auto px-4 py-12 space-y-12">
      <header className="space-y-2 text-center">
        <h1 className="text-3xl font-bold">{t('about.title')}</h1>
        <p className="opacity-70 text-sm">{t('about.tagline')}</p>
      </header>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">{t('about.missionTitle')}</h2>
        <p className="leading-relaxed">{t('about.missionBody')}</p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">{t('about.howTitle')}</h2>
        <p className="leading-relaxed">{t('about.howBody')}</p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-semibold">{t('about.teamTitle')}</h2>
        <p className="leading-relaxed">{t('about.teamBody')}</p>
      </section>

      <footer className="text-sm text-center pt-6 border-t border-white/10 space-x-4">
        <Link to="/privacy" className="underline opacity-70 hover:opacity-100">{t('legal.privacy')}</Link>
        <Link to="/terms" className="underline opacity-70 hover:opacity-100">{t('legal.terms')}</Link>
        <Link to="/faq" className="underline opacity-70 hover:opacity-100">{t('faq.title')}</Link>
      </footer>
    </div>
  )
}
