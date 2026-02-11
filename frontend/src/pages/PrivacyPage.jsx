import { Link, useNavigate } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'

export default function PrivacyPage() {
  const { t } = useLang()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="glass p-8 w-full max-w-3xl space-y-6">
        <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent">
          {t('privacy.heading')}
        </h1>
        <p className="text-sm opacity-60">{t('privacy.lastUpdated')}</p>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s1Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s1Body')}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s2Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s2Body')}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s3Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s3Body')}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s4Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s4Body')}</p>
          <ul className="text-sm opacity-80 list-disc list-inside space-y-1">
            <li>{t('privacy.s4Item1')}</li>
            <li>{t('privacy.s4Item2')}</li>
          </ul>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s5Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s5Body')}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s6Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s6Body')}</p>
        </section>

        <div className="pt-4 flex gap-4 text-sm">
          <Link to="/terms" className="text-purple-500 hover:text-purple-400">
            {t('legal.terms')}
          </Link>
          <button onClick={() => navigate(-1)} className="text-purple-500 hover:text-purple-400 cursor-pointer">
            {t('legal.back')}
          </button>
        </div>
      </div>
    </div>
  )
}
