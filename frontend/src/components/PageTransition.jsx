/**
 * Enhanced PageTransition Component
 *
 * Features:
 * - Multiple transition modes (fade, slide, scale)
 * - Directional slides (left, right, up, down)
 * - Reduced motion support
 * - Customizable duration and easing
 * - Maintains scroll position option
 */

import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'

// Check for reduced motion preference
const prefersReducedMotion = () => {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

// Transition variants
const transitionVariants = {
  // Fade transition (simple, accessible)
  fade: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
  },

  // Slide up (default, natural feel)
  slideUp: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -20 },
  },

  // Slide down
  slideDown: {
    initial: { opacity: 0, y: -20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: 20 },
  },

  // Slide left (forward navigation)
  slideLeft: {
    initial: { opacity: 0, x: 50 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -50 },
  },

  // Slide right (backward navigation)
  slideRight: {
    initial: { opacity: 0, x: -50 },
    animate: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: 50 },
  },

  // Scale (zoom effect)
  scale: {
    initial: { opacity: 0, scale: 0.95 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 1.05 },
  },
}

// Easing presets
const easingPresets = {
  smooth: [0.25, 0.1, 0.25, 1],
  easeOut: [0, 0, 0.2, 1],
  easeInOut: [0.4, 0, 0.2, 1],
  anticipate: [0.16, 1, 0.3, 1],
}

export default function PageTransition({
  children,
  mode = 'slideUp',
  duration = 0.3,
  easing = 'smooth',
  maintainScroll = false,
}) {
  const [shouldAnimate, setShouldAnimate] = useState(true)

  // Check for reduced motion preference
  useEffect(() => {
    setShouldAnimate(!prefersReducedMotion())

    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)')
    const handleChange = (e) => setShouldAnimate(!e.matches)

    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  // Scroll to top on page change (unless maintainScroll is true)
  useEffect(() => {
    if (!maintainScroll) {
      window.scrollTo(0, 0)
    }
  }, [maintainScroll])

  const variants = shouldAnimate
    ? transitionVariants[mode] || transitionVariants.slideUp
    : transitionVariants.fade

  const transitionConfig = {
    duration: shouldAnimate ? duration : 0.01,
    ease: easingPresets[easing] || easingPresets.smooth,
  }

  return (
    <motion.div
      initial="initial"
      animate="animate"
      exit="exit"
      variants={variants}
      transition={transitionConfig}
      style={{ width: '100%', minHeight: '100%' }}
    >
      {children}
    </motion.div>
  )
}

// Preset configurations for common use cases
export const pageTransitionPresets = {
  default: { mode: 'slideUp', duration: 0.3 },
  fast: { mode: 'fade', duration: 0.15 },
  smooth: { mode: 'slideUp', duration: 0.4, easing: 'smooth' },
  forward: { mode: 'slideLeft', duration: 0.3 },
  backward: { mode: 'slideRight', duration: 0.3 },
  modal: { mode: 'scale', duration: 0.25 },
}
