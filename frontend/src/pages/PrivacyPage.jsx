import { Link, useNavigate } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'
import { Card, Button } from '../components/ui'

export default function PrivacyPage() {
  const { t } = useLang()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card variant="default" padding="lg" className="w-full max-w-3xl space-y-6" animate staggerDelay={0.1}>
        <h1 className="text-2xl font-bold bg-gradient-to-r from-orange-500 to-rose-500 bg-clip-text text-transparent">
          {t('privacy.heading')}
        </h1>
        <p className="text-sm text-slate-400">{t('privacy.lastUpdated')}</p>

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

        <section className="space-y-2" id="health-data">
          <h2 className="text-lg font-semibold">{t('privacy.s7Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s7Intro')}</p>
          <ul className="text-sm opacity-80 list-disc list-inside space-y-1">
            <li>{t('privacy.s7Type1')}</li>
            <li>{t('privacy.s7Type2')}</li>
            <li>{t('privacy.s7Type3')}</li>
            <li>{t('privacy.s7Type4')}</li>
            <li>{t('privacy.s7Type5')}</li>
            <li>{t('privacy.s7Type6')}</li>
          </ul>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s7Purpose')}</p>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s7Sharing')}</p>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s7Retention')}</p>
        </section>

        <div className="pt-4 flex gap-4 text-sm">
          <Link to="/terms">
            <Button variant="ghost" size="sm">
              {t('legal.terms')}
            </Button>
          </Link>
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
            {t('legal.back')}
          </Button>
        </div>
      </Card>
    </div>
  )
}
