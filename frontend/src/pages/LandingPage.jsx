import { Link } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'

export default function LandingPage() {
  const { t } = useLang()

  const features = [
    { icon: '/icons/日誌.png', titleKey: 'landing.featureJournal', descKey: 'landing.featureJournalDesc' },
    { icon: '/icons/AI 聊天.png', titleKey: 'landing.featureAI', descKey: 'landing.featureAIDesc' },
    { icon: '/icons/心情週報月報.png', titleKey: 'landing.featureAnalytics', descKey: 'landing.featureAnalyticsDesc' },
    { icon: '/icons/呼吸與冥想.png', titleKey: 'landing.featureBreathe', descKey: 'landing.featureBreatheDesc' },
    { icon: '/icons/諮商師.png', titleKey: 'landing.featureCounselor', descKey: 'landing.featureCounselorDesc' },
    { icon: '/icons/問卷評估.png', titleKey: 'landing.featureAssessment', descKey: 'landing.featureAssessmentDesc' },
  ]

  return (
    <div className="min-h-screen flex flex-col">
      {/* JSON-LD */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify({
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": "HeartBox",
        "description": t('landing.subtitle'),
        "url": "https://heartbox.pages.dev",
        "applicationCategory": "HealthApplication",
        "operatingSystem": "Web",
        "offers": {
          "@type": "Offer",
          "price": "0",
          "priceCurrency": "TWD"
        }
      })}} />

      {/* Hero */}
      <header className="flex flex-col items-center justify-center text-center px-4 pt-16 pb-12">
        <img src="/logo.png" alt="HeartBox" className="w-20 h-20 mb-4" />
        <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent mb-4">
          {t('landing.title')}
        </h1>
        <p className="text-lg md:text-xl opacity-70 max-w-2xl mb-8">{t('landing.subtitle')}</p>
        <div className="flex gap-4 flex-wrap justify-center">
          <Link to="/register" className="btn-primary text-lg px-8 py-3">{t('landing.getStarted')}</Link>
          <a href="#features" className="btn-secondary text-lg px-8 py-3">{t('landing.learnMore')}</a>
        </div>
      </header>

      {/* Features */}
      <section id="features" className="max-w-6xl mx-auto px-4 py-12">
        <h2 className="text-2xl font-bold text-center mb-8">{t('landing.featuresTitle')}</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <div key={i} className="glass p-6 text-center space-y-3 hover:scale-[1.02] transition-transform">
              <img src={f.icon} alt="" className="w-12 h-12 mx-auto" />
              <h3 className="text-lg font-semibold">{t(f.titleKey)}</h3>
              <p className="text-sm opacity-70">{t(f.descKey)}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Pricing Preview */}
      <section className="max-w-4xl mx-auto px-4 py-12 text-center">
        <h2 className="text-2xl font-bold mb-4">{t('landing.pricingTitle')}</h2>
        <p className="opacity-70 mb-6">{t('landing.pricingDesc')}</p>
        <Link to="/pricing" className="btn-secondary">{t('landing.viewPricing')}</Link>
      </section>

      {/* Footer */}
      <footer className="text-center text-xs opacity-40 py-6 space-x-4 mt-auto">
        <Link to="/privacy" className="hover:opacity-70">{t('legal.privacy')}</Link>
        <Link to="/terms" className="hover:opacity-70">{t('legal.terms')}</Link>
        <span>&copy; {new Date().getFullYear()} HeartBox</span>
      </footer>
    </div>
  )
}
