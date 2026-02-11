import { Link } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'

export default function TermsPage() {
  const { t } = useLang()

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="glass p-8 w-full max-w-3xl space-y-6">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent">
          {t('terms.heading')}
        </h1>
        <p className="text-sm opacity-60">{t('terms.lastUpdated')}</p>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s1Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('terms.s1Body')}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s2Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed font-medium text-yellow-500/90">
            {t('terms.s2Body')}
          </p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s3Title')}</h2>
          <ul className="text-sm opacity-80 list-disc list-inside space-y-1">
            <li>{t('terms.s3Item1')}</li>
            <li>{t('terms.s3Item2')}</li>
            <li>{t('terms.s3Item3')}</li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s4Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('terms.s4Body')}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s5Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('terms.s5Body')}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s6Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('terms.s6Body')}</p>
        </section>

        <div className="pt-4 flex gap-4 text-sm">
          <Link to="/privacy" className="text-purple-500 hover:text-purple-400">
            {t('legal.privacy')}
          </Link>
          <Link to="/login" className="text-purple-500 hover:text-purple-400">
            {t('legal.backToLogin')}
          </Link>
        </div>
      </div>
    </div>
  )
}
