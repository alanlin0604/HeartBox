import { useEffect, useState } from 'react'
import { useLang } from '../context/LanguageContext'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { getPlans, getMySubscription, subscribe } from '../api/subscription'

export default function PricingPage() {
  const { t } = useLang()
  const { user } = useAuth()
  const toast = useToast()
  const [plans, setPlans] = useState([])
  const [currentSub, setCurrentSub] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    document.title = `${t('subscription.pricingTitle')} — HeartBox`
    Promise.all([
      getPlans().catch(() => ({ data: { results: [] } })),
      user ? getMySubscription().catch(() => ({ data: {} })) : Promise.resolve({ data: {} }),
    ]).then(([plansRes, subRes]) => {
      setPlans(plansRes.data.results || plansRes.data || [])
      setCurrentSub(subRes.data)
      setLoading(false)
    })
  }, [t, user])

  const handleSubscribe = async (planId) => {
    try {
      const { data } = await subscribe(planId)
      setCurrentSub(data)
      toast?.success(t('subscription.subscribed'))
    } catch {
      toast?.error(t('subscription.subscribeFailed'))
    }
  }

  const tierColors = {
    free: 'border-gray-500/30',
    pro: 'border-purple-500/50',
    counselor: 'border-pink-500/50',
  }

  if (loading) return <div className="text-center py-12 opacity-60">{t('common.loading')}</div>

  return (
    <div className="space-y-6 mt-4 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-center">{t('subscription.pricingTitle')}</h1>
      <p className="text-center opacity-70">{t('subscription.pricingDesc')}</p>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {plans.map(plan => (
          <div key={plan.id} className={`glass p-6 space-y-4 border-2 ${tierColors[plan.tier] || ''} ${currentSub?.plan === plan.id ? 'ring-2 ring-purple-500' : ''}`}>
            <h2 className="text-xl font-bold text-center">{plan.name}</h2>
            <div className="text-center">
              <span className="text-3xl font-bold">{plan.price > 0 ? `${plan.currency} ${plan.price}` : t('subscription.free')}</span>
              {plan.price > 0 && <span className="text-sm opacity-60">/{t('subscription.month')}</span>}
            </div>
            <ul className="space-y-2 text-sm">
              {(plan.features || []).map((f, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-green-500 mt-0.5">✓</span>
                  <span>{f}</span>
                </li>
              ))}
            </ul>
            {user && (
              <button
                onClick={() => handleSubscribe(plan.id)}
                disabled={currentSub?.plan === plan.id}
                className={currentSub?.plan === plan.id ? 'btn-secondary w-full opacity-60' : 'btn-primary w-full'}
              >
                {currentSub?.plan === plan.id ? t('subscription.current') : t('subscription.subscribe')}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
