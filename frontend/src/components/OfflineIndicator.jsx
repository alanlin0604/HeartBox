import { useState, useEffect } from 'react'
import { useLang } from '../context/LanguageContext'

/**
 * OfflineIndicator - Shows a banner when user goes offline
 * Automatically hides when connection is restored
 */
export default function OfflineIndicator() {
  const { t } = useLang()
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  const [showBanner, setShowBanner] = useState(!navigator.onLine)

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true)
      // Show "back online" briefly, then hide
      setShowBanner(true)
      setTimeout(() => setShowBanner(false), 3000)
    }

    const handleOffline = () => {
      setIsOnline(false)
      setShowBanner(true)
    }

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  if (!showBanner) return null

  return (
    <div
      className={`fixed top-0 left-0 right-0 z-[100] px-4 py-2 text-sm text-center transition-all ${
        isOnline
          ? 'bg-green-500 text-white'
          : 'bg-yellow-500/90 text-gray-900'
      }`}
      role="alert"
      aria-live="polite"
    >
      {isOnline ? (
        <>
          <span className="mr-2">✓</span>
          {t('offline.backOnline')}
        </>
      ) : (
        <>
          <span className="mr-2">⚠️</span>
          {t('offline.youAreOffline')}
          <span className="ml-2 opacity-75">{t('offline.someFeaturesMayNotWork')}</span>
        </>
      )}
    </div>
  )
}
