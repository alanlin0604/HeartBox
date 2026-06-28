import { useState, useEffect, memo } from 'react'
import { Link } from 'react-router-dom'
import { getAlerts } from '../api/alerts'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'

const SEVERITY_STYLES = {
  high: 'bg-red-500/25 border-red-500/50 text-[var(--text-primary)]',
  medium: 'bg-amber-500/25 border-amber-500/50 text-amber-500',
}

export default memo(function AlertBanner() {
  const { t } = useLang()
  const toast = useToast()
  const [alerts, setAlerts] = useState([])
  const [dismissed, setDismissed] = useState([])

  useEffect(() => {
    let cancelled = false
    getAlerts()
      .then((res) => { if (!cancelled) setAlerts(res.data.alerts || []) })
      .catch(() => {
        if (!cancelled) toast?.error(t('common.operationFailed'))
      })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const visibleAlerts = alerts.filter((_, i) => !dismissed.includes(i))
  if (visibleAlerts.length === 0) return null

  return (
    <div className="space-y-2">
      {alerts.map((alert, i) => {
        if (dismissed.includes(i)) return null
        const style = SEVERITY_STYLES[alert.severity] || SEVERITY_STYLES.medium
        return (
          <div
            key={`${alert.type}-${i}`}
            className={`rounded-xl border p-4 flex items-start gap-3 ${style}`}
          >
            <img
              src="/icons/alert.svg"
              alt=""
              aria-hidden="true"
              className="w-7 h-7 object-contain mt-0.5 flex-shrink-0"
            />
            <div className="flex-1">
              <p className="text-base font-bold">
                {t(`alert.${alert.type}.title`)}
              </p>
              <p className="text-sm mt-1">
                {alert.type === 'consecutive_negative' &&
                  t('alert.consecutive_negative.desc', { count: alert.data.count })}
                {alert.type === 'high_stress' &&
                  t('alert.high_stress.desc', { avg: alert.data.avg_stress })}
                {alert.type === 'sudden_drop' &&
                  t('alert.sudden_drop.desc', { drop: alert.data.drop })}
              </p>
              <div className="flex items-center gap-3 mt-2">
                <p className="text-sm font-medium opacity-80">{t('alert.recommendation')}</p>
                <Link
                  to="/learn"
                  className="text-sm font-medium underline opacity-90 hover:opacity-100"
                >
                  {t('alert.exploreResources')}
                </Link>
              </div>
            </div>
            <button
              onClick={() => setDismissed([...dismissed, i])}
              className="text-sm opacity-50 hover:opacity-100 p-2 -m-2"
              aria-label={t('aria.dismiss')}
            >
              ✕
            </button>
          </div>
        )
      })}
    </div>
  )
})
