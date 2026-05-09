import { Link, useNavigate } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'
import { Card, Button } from '../components/ui'

export default function TermsPage() {
  const { t } = useLang()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card variant="default" padding="lg" className="w-full max-w-3xl space-y-6" animate staggerDelay={0.1}>
        <h1 className="text-2xl font-bold bg-gradient-to-r from-orange-500 to-rose-500 bg-clip-text text-transparent">
          {t('terms.heading')}
        </h1>
        <p className="text-sm text-slate-400">{t('terms.lastUpdated')}</p>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s1Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('terms.s1Body')}</p>
        </section>

        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s2Title')}</h2>
          <p className="text-sm leading-relaxed font-bold text-red-500">
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
          <Link to="/privacy">
            <Button variant="ghost" size="sm">
              {t('legal.privacy')}
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
