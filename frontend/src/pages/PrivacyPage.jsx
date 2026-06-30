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

        {/* §1 資料收集 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s1Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s1Body')}</p>
          <ul className="text-sm opacity-80 list-disc list-inside space-y-1">
            <li>{t('privacy.s1ItemAccount')}</li>
            <li>{t('privacy.s1ItemJournal')}</li>
            <li>{t('privacy.s1ItemAi')}</li>
            <li>{t('privacy.s1ItemHealth')}</li>
            <li>{t('privacy.s1ItemSocial')}</li>
            <li>{t('privacy.s1ItemUsage')}</li>
            <li>{t('privacy.s1ItemPrefs')}</li>
          </ul>
        </section>

        {/* §2 資料加密 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s2Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s2Body')}</p>
        </section>

        {/* §3 AI 分析 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s3Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s3Body')}</p>
        </section>

        {/* §4 第三方服務 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s4Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s4Body')}</p>
          <ul className="text-sm opacity-80 list-disc list-inside space-y-1">
            <li>{t('privacy.s4Item1')}</li>
            <li>{t('privacy.s4Item2')}</li>
            <li>{t('privacy.s4Item3')}</li>
            <li>{t('privacy.s4Item4')}</li>
            <li>{t('privacy.s4Item5')}</li>
            <li>{t('privacy.s4Item6')}</li>
            <li>{t('privacy.s4Item7')}</li>
            <li>{t('privacy.s4Item8')}</li>
          </ul>
        </section>

        {/* §5 健康資料 */}
        <section className="space-y-2" id="health-data">
          <h2 className="text-lg font-semibold">{t('privacy.s5Title')}</h2>
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

        {/* §6 兒少特別保護 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s6Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s6Body')}</p>
          <ul className="text-sm opacity-80 list-disc list-inside space-y-1">
            <li>{t('privacy.s6ItemUnder13')}</li>
            <li>{t('privacy.s6Item1317')}</li>
            <li>{t('privacy.s6ItemNoAds')}</li>
          </ul>
        </section>

        {/* §7 危機介入機制 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s8Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s8Body')}</p>
          <ul className="text-sm opacity-80 list-disc list-inside space-y-1">
            <li>{t('privacy.s8ItemHotline')}</li>
            <li>{t('privacy.s8ItemAi')}</li>
            <li>{t('privacy.s8ItemNoReport')}</li>
            <li>{t('privacy.s8ItemLog')}</li>
          </ul>
        </section>

        {/* §8 帳號安全 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s9Title')}</h2>
          <ul className="text-sm opacity-80 list-disc list-inside space-y-1">
            <li>{t('privacy.s9ItemPassword')}</li>
            <li>{t('privacy.s9ItemLockout')}</li>
            <li>{t('privacy.s9Item2FA')}</li>
            <li>{t('privacy.s9ItemJwt')}</li>
          </ul>
        </section>

        {/* §9 使用者權利 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s10Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s10Body')}</p>
          <ul className="text-sm opacity-80 list-disc list-inside space-y-1">
            <li>{t('privacy.s10ItemExport')}</li>
            <li>{t('privacy.s10ItemDelete')}</li>
            <li>{t('privacy.s10ItemWithdrawAi')}</li>
            <li>{t('privacy.s10ItemWithdrawHealth')}</li>
            <li>{t('privacy.s10ItemEdit')}</li>
            <li>{t('privacy.s10ItemAccess')}</li>
          </ul>
        </section>

        {/* §10 Cookie 與本地儲存 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s11Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s11Body')}</p>
        </section>

        {/* §11 資料保留期間 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s12Title')}</h2>
          <ul className="text-sm opacity-80 list-disc list-inside space-y-1">
            <li>{t('privacy.s12ItemActive')}</li>
            <li>{t('privacy.s12ItemDeleted')}</li>
            <li>{t('privacy.s12ItemLogs')}</li>
          </ul>
        </section>

        {/* §12 政策變更與聯絡方式 */}
        <section className="space-y-2">
          <h2 className="text-lg font-semibold">{t('privacy.s13Title')}</h2>
          <p className="text-sm opacity-80 leading-relaxed">{t('privacy.s13Body')}</p>
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
