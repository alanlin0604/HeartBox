import { memo, useEffect, useState, useRef } from 'react'
import { useLocation } from 'react-router-dom'

/**
 * Page transition wrapper with fade + slide animation
 * Respects prefers-reduced-motion for accessibility
 *
 * Usage:
 * <PageTransition>
 *   <YourPageContent />
 * </PageTransition>
 */
export default memo(function PageTransition({ children, direction = 'forward' }) {
  const location = useLocation()
  const [displayLocation, setDisplayLocation] = useState(location)
  const [transitionStage, setTransitionStage] = useState('enter')
  const timeoutRef = useRef(null)

  useEffect(() => {
    // Check if user prefers reduced motion
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (prefersReducedMotion) {
      // Skip animation, update immediately
      setDisplayLocation(location)
      setTransitionStage('enter')
      return
    }

    if (location.pathname !== displayLocation.pathname) {
      // Start exit transition
      setTransitionStage('exit')

      // Wait for exit animation, then update content
      timeoutRef.current = setTimeout(() => {
        setDisplayLocation(location)
        setTransitionStage('enter')
      }, 200) // Match CSS transition duration
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [location, displayLocation])

  // Determine animation direction based on navigation
  const animationClass = direction === 'forward' ? 'slide-forward' : 'slide-backward'

  return (
    <div
      className={`page-transition ${transitionStage} ${animationClass}`}
      style={{
        opacity: transitionStage === 'enter' ? 1 : 0,
        transform: transitionStage === 'enter' ? 'translateX(0)' :
                   direction === 'forward' ? 'translateX(20px)' : 'translateX(-20px)',
        transition: 'opacity var(--duration-normal) var(--easing-standard), transform var(--duration-normal) var(--easing-standard)',
      }}
    >
      {children}
    </div>
  )
})

/**
 * Minimal page fade transition (no slide)
 * Use for simple transitions or when direction is unclear
 */
export const PageFade = memo(function PageFade({ children }) {
  const location = useLocation()
  const [isVisible, setIsVisible] = useState(true)

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReducedMotion) return

    setIsVisible(false)
    const timeout = setTimeout(() => setIsVisible(true), 50)
    return () => clearTimeout(timeout)
  }, [location.pathname])

  return (
    <div
      style={{
        opacity: isVisible ? 1 : 0,
        transition: 'opacity var(--duration-fast) var(--easing-standard)',
      }}
    >
      {children}
    </div>
  )
})
