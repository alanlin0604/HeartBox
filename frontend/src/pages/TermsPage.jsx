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

        {/* §1 服務說明 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s1Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('terms.s1Body')}</p>
        </section>

        {/* §2 AI 免責聲明（紅色強調） */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s2Title')}</h2>
          <p className="text-sm leading-relaxed font-semibold text-red-500">
            {t('terms.s2Body')}
          </p>
        </section>

        {/* §3 使用者義務 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s3Title')}</h2>
          <ul className="text-sm opacity-80 list-disc list-inside space-y-1">
            <li>{t('terms.s3Item1')}</li>
            <li>{t('terms.s3Item2')}</li>
            <li>{t('terms.s3Item3')}</li>
            <li>{t('terms.s3Item4')}</li>
            <li>{t('terms.s3Item5')}</li>
          </ul>
        </section>

        {/* §4 兒少規範 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s4Title')}</h2>
          <ul className="text-sm opacity-80 list-disc list-inside space-y-1">
            <li>{t('terms.s4ItemUnder13')}</li>
            <li>{t('terms.s4Item1317')}</li>
            <li>{t('terms.s4ItemGuardian')}</li>
          </ul>
        </section>

        {/* §5 社群行為守則 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s5Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('terms.s5Body')}</p>
          <ul className="text-sm opacity-80 list-disc list-inside space-y-1">
            <li>{t('terms.s5ItemForbidden')}</li>
            <li>{t('terms.s5ItemAutoDetect')}</li>
            <li>{t('terms.s5ItemReport')}</li>
          </ul>
        </section>

        {/* §6 危機介入 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s6Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('terms.s6Body')}</p>
          <ul className="text-sm opacity-80 list-disc list-inside space-y-1">
            <li>{t('terms.s6ItemHotline')}</li>
            <li>{t('terms.s6ItemAi')}</li>
            <li>{t('terms.s6ItemNoReport')}</li>
            <li>{t('terms.s6ItemEmergency')}</li>
          </ul>
        </section>

        {/* §7 資料所有權 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s7Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('terms.s7Body')}</p>
        </section>

        {/* §8 服務可用性 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s8Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('terms.s8Body')}</p>
        </section>

        {/* §9 帳號終止 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s9Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('terms.s9Body')}</p>
        </section>

        {/* §10 服務變更 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s10Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('terms.s10Body')}</p>
        </section>

        {/* §11 準據法 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('terms.s11Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('terms.s11Body')}</p>
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
