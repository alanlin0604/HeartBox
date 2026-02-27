import { useEffect, useRef, useCallback, useState } from 'react'

export default function useIdleTimer({ timeout = 30 * 60 * 1000, warningDuration = 60 * 1000, onIdle, enabled = true }) {
  const [showWarning, setShowWarning] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const timerRef = useRef(null)
  const warningTimerRef = useRef(null)
  const countdownRef = useRef(null)

  const resetTimer = useCallback(() => {
    if (!enabled) return
    setShowWarning(false)
    setCountdown(0)

    if (timerRef.current) clearTimeout(timerRef.current)
    if (warningTimerRef.current) clearTimeout(warningTimerRef.current)
    if (countdownRef.current) clearInterval(countdownRef.current)

    timerRef.current = setTimeout(() => {
      setShowWarning(true)
      setCountdown(Math.ceil(warningDuration / 1000))

      countdownRef.current = setInterval(() => {
        setCountdown(prev => {
          if (prev <= 1) {
            clearInterval(countdownRef.current)
            onIdle?.()
            return 0
          }
          return prev - 1
        })
      }, 1000)

      warningTimerRef.current = setTimeout(() => {
        onIdle?.()
      }, warningDuration)
    }, timeout)
  }, [timeout, warningDuration, onIdle, enabled])

  useEffect(() => {
    if (!enabled) return

    const events = ['mousedown', 'keydown', 'touchstart', 'scroll', 'mousemove']
    events.forEach(e => document.addEventListener(e, resetTimer, { passive: true }))
    resetTimer()

    return () => {
      events.forEach(e => document.removeEventListener(e, resetTimer))
      if (timerRef.current) clearTimeout(timerRef.current)
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current)
      if (countdownRef.current) clearInterval(countdownRef.current)
    }
  }, [resetTimer, enabled])

  const dismissWarning = useCallback(() => {
    setShowWarning(false)
    if (warningTimerRef.current) clearTimeout(warningTimerRef.current)
    if (countdownRef.current) clearInterval(countdownRef.current)
    resetTimer()
  }, [resetTimer])

  return { showWarning, countdown, dismissWarning }
}
