import { Link } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'
import { Button, Card } from '../components/ui'
import { isReturningUser } from '../utils/tokenStorage'

export default function LandingPage() {
  const { t } = useLang()
  const returning = isReturningUser()
  const ctaTo = returning ? '/login' : '/register'
  const ctaLabel = returning ? t('login.submit') : t('landing.getStarted')

  const features = [
    { icon: '/icons/日誌.webp', titleKey: 'landing.featureJournal', descKey: 'landing.featureJournalDesc' },
    { icon: '/icons/AI 聊天.webp', titleKey: 'landing.featureAI', descKey: 'landing.featureAIDesc' },
    { icon: '/icons/心情週報月報.webp', titleKey: 'landing.featureAnalytics', descKey: 'landing.featureAnalyticsDesc' },
    { icon: '/icons/呼吸與冥想.webp', titleKey: 'landing.featureBreathe', descKey: 'landing.featureBreatheDesc' },
    { icon: '/icons/諮商師.webp', titleKey: 'landing.featureCounselor', descKey: 'landing.featureCounselorDesc' },
    { icon: '/icons/問卷評估.webp', titleKey: 'landing.featureAssessment', descKey: 'landing.featureAssessmentDesc' },
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

      {/* Hero Section - Modern Design */}
      <header className="relative flex flex-col items-center justify-center text-center px-4 pt-20 pb-16 sm:pt-24 sm:pb-20 overflow-hidden">
        {/* Decorative gradient orbs */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-gradient-to-br from-orange-500/20 to-rose-500/20 rounded-full blur-3xl -z-10" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-gradient-to-br from-blue-500/20 to-orange-500/20 rounded-full blur-3xl -z-10" />

        {/* Logo with subtle animation */}
        <div className="mb-6 animate-scale-in">
          <img
            src="/logo.png"
            alt="HeartBox"
            className="w-24 h-24 drop-shadow-[0_0_20px_rgba(251, 146, 60,0.3)]"
          />
        </div>

        {/* Title with gradient text */}
        <h1 className="text-5xl sm:text-6xl md:text-7xl font-bold mb-6 animate-fade-in">
          <span className="gradient-text">
            {t('landing.title')}
          </span>
        </h1>

        {/* Subtitle */}
        <p className="text-lg sm:text-xl md:text-2xl text-[var(--text-secondary)] max-w-3xl mb-10 leading-relaxed animate-fade-in" style={{ animationDelay: '100ms' }}>
          {t('landing.subtitle')}
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 animate-fade-in" style={{ animationDelay: '200ms' }}>
          <Link to={ctaTo}>
            <Button size="lg" className="min-w-[160px]">
              ✨ {ctaLabel}
            </Button>
          </Link>
          <a href="#features">
            <Button variant="secondary" size="lg" className="min-w-[160px]">
              {t('landing.learnMore')}
            </Button>
          </a>
        </div>
      </header>

      {/* Features Section - Card Grid */}
      <section id="features" className="max-w-7xl mx-auto px-4 py-16 sm:py-20">
        <div className="text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold mb-4">
            {t('landing.featuresTitle')}
          </h2>
          <div className="w-20 h-1 bg-gradient-to-r from-orange-500 to-rose-500 mx-auto rounded-full" />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <Card
              key={i}
              hover
              padding="lg"
              className="text-center group"
              style={{
                animationDelay: `${i * 50}ms`,
                animation: 'scale-in var(--duration-normal) var(--ease-smooth) backwards'
              }}
            >
              <div className="mb-4 transform group-hover:scale-110 transition-transform duration-300">
                <img
                  src={f.icon}
                  alt=""
                  className="w-16 h-16 mx-auto drop-shadow-lg"
                  loading="lazy"
                  decoding="async"
                />
              </div>
              <h3 className="text-xl font-semibold mb-3 text-[var(--text-primary)]">
                {t(f.titleKey)}
              </h3>
              <p className="text-sm text-[var(--text-secondary)] leading-relaxed">
                {t(f.descKey)}
              </p>
            </Card>
          ))}
        </div>
      </section>

      {/* Pricing Preview Section */}
      <section className="max-w-4xl mx-auto px-4 py-16 sm:py-20">
        <Card padding="lg" className="text-center">
          <h2 className="text-3xl font-bold mb-4 text-[var(--text-primary)]">
            {t('landing.pricingTitle')}
          </h2>
          <p className="text-lg text-[var(--text-secondary)] mb-8 max-w-2xl mx-auto">
            {t('landing.pricingDesc')}
          </p>
          <Link to="/pricing">
            <Button variant="outline" size="lg">
              {t('landing.viewPricing')} →
            </Button>
          </Link>
        </Card>
      </section>

      {/* Footer */}
      <footer className="text-center py-8 mt-auto border-t border-[var(--border-primary)]">
        <div className="flex flex-wrap justify-center gap-6 mb-4 text-sm text-[var(--text-tertiary)]">
          <Link to="/privacy" className="hover:text-[var(--color-primary-400)] transition-colors">
            {t('legal.privacy')}
          </Link>
          <Link to="/terms" className="hover:text-[var(--color-primary-400)] transition-colors">
            {t('legal.terms')}
          </Link>
        </div>
        <p className="text-xs text-[var(--text-muted)]">
          &copy; {new Date().getFullYear()} HeartBox. All rights reserved.
        </p>
      </footer>
    </div>
  )
}
