/**
 * Animation Utilities for HeartBox
 * Unified Framer Motion animation configurations
 *
 * Usage:
 * import { fadeIn, slideUp, scaleIn } from '../utils/animations'
 *
 * <motion.div {...fadeIn}>Content</motion.div>
 */

// ==================== Spring Configurations ====================

export const springConfig = {
  type: 'spring',
  stiffness: 400,
  damping: 30,
}

export const springConfigSlow = {
  type: 'spring',
  stiffness: 300,
  damping: 25,
}

export const springConfigBouncy = {
  type: 'spring',
  stiffness: 500,
  damping: 20,
}

// ==================== Easing Functions ====================

export const easeOut = [0, 0, 0.2, 1]
export const easeIn = [0.4, 0, 1, 1]
export const easeInOut = [0.4, 0, 0.2, 1]
export const easeSmooth = [0.25, 0.1, 0.25, 1]
export const easeBounce = [0.34, 1.56, 0.64, 1]

// ==================== Basic Animations ====================

/**
 * Fade In (opacity 0 → 1)
 */
export const fadeIn = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: { duration: 0.3, ease: easeOut }
}

/**
 * Fade In with slight upward movement
 */
export const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 },
  transition: { duration: 0.3, ease: easeSmooth }
}

/**
 * Fade In with downward movement
 */
export const fadeInDown = {
  initial: { opacity: 0, y: -20 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: 20 },
  transition: { duration: 0.3, ease: easeSmooth }
}

/**
 * Scale In (zoom effect)
 */
export const scaleIn = {
  initial: { scale: 0.9, opacity: 0 },
  animate: { scale: 1, opacity: 1 },
  exit: { scale: 0.9, opacity: 0 },
  transition: springConfig
}

/**
 * Scale In with bounce
 */
export const scaleInBounce = {
  initial: { scale: 0.8, opacity: 0 },
  animate: { scale: 1, opacity: 1 },
  exit: { scale: 0.8, opacity: 0 },
  transition: { ...springConfigBouncy, duration: 0.5 }
}

// ==================== Directional Slides ====================

/**
 * Slide Up from bottom
 */
export const slideUp = {
  initial: { y: 50, opacity: 0 },
  animate: { y: 0, opacity: 1 },
  exit: { y: -50, opacity: 0 },
  transition: { duration: 0.3, ease: easeSmooth }
}

/**
 * Slide Down from top
 */
export const slideDown = {
  initial: { y: -50, opacity: 0 },
  animate: { y: 0, opacity: 1 },
  exit: { y: 50, opacity: 0 },
  transition: { duration: 0.3, ease: easeSmooth }
}

/**
 * Slide In from Left
 */
export const slideInLeft = {
  initial: { x: -50, opacity: 0 },
  animate: { x: 0, opacity: 1 },
  exit: { x: 50, opacity: 0 },
  transition: { duration: 0.3, ease: easeSmooth }
}

/**
 * Slide In from Right
 */
export const slideInRight = {
  initial: { x: 50, opacity: 0 },
  animate: { x: 0, opacity: 1 },
  exit: { x: -50, opacity: 0 },
  transition: { duration: 0.3, ease: easeSmooth }
}

// ==================== Specialized Animations ====================

/**
 * Modal / Overlay entrance
 */
export const modalVariants = {
  hidden: {
    opacity: 0,
    scale: 0.95,
    y: 20
  },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: springConfig
  },
  exit: {
    opacity: 0,
    scale: 0.95,
    y: 20,
    transition: { duration: 0.2 }
  }
}

/**
 * Backdrop fade
 */
export const backdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
  exit: { opacity: 0 }
}

/**
 * List item stagger (use with staggerChildren)
 */
export const listContainerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1
    }
  }
}

export const listItemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.3, ease: easeOut }
  }
}

/**
 * Card hover effect
 */
export const cardHover = {
  rest: { scale: 1, y: 0 },
  hover: {
    scale: 1.02,
    y: -4,
    transition: { duration: 0.2, ease: easeOut }
  },
  tap: {
    scale: 0.98,
    transition: { duration: 0.1 }
  }
}

/**
 * Button press effect
 */
export const buttonPress = {
  whileHover: { scale: 1.02, y: -2 },
  whileTap: { scale: 0.98 },
  transition: springConfig
}

// ==================== Page Transitions ====================

/**
 * Page transition (for route changes)
 */
export const pageTransition = {
  initial: { opacity: 0, x: -20 },
  animate: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: 20 },
  transition: { duration: 0.3, ease: easeSmooth }
}

/**
 * Page fade transition (simple)
 */
export const pageFade = {
  initial: { opacity: 0 },
  animate: { opacity: 1 },
  exit: { opacity: 0 },
  transition: { duration: 0.2 }
}

// ==================== Helper Functions ====================

/**
 * Create stagger delay for multiple items
 * @param {number} index - Item index
 * @param {number} delay - Base delay in seconds
 */
export const staggerDelay = (index, delay = 0.05) => ({
  transition: { delay: index * delay }
})

/**
 * Create responsive duration (shorter on mobile)
 */
export const responsiveDuration = (desktop = 0.3, mobile = 0.2) => {
  if (typeof window === 'undefined') return desktop
  return window.innerWidth < 768 ? mobile : desktop
}

// ==================== CSS Animation Classes ====================

/**
 * Use these with Tailwind @apply or className
 */
export const cssAnimations = {
  fadeIn: 'animate-fade-in',
  fadeOut: 'animate-fade-out',
  slideUp: 'animate-slide-up',
  slideDown: 'animate-slide-down',
  scaleIn: 'animate-scale-in',
  spin: 'animate-spin',
  pulse: 'animate-pulse',
  bounce: 'animate-bounce',
}

// ==================== Prefers Reduced Motion ====================

/**
 * Check if user prefers reduced motion
 */
export const prefersReducedMotion = () => {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/**
 * Get appropriate animation based on user preference
 * @param {object} normalAnimation - Full animation
 * @param {object} reducedAnimation - Reduced motion fallback (optional)
 */
export const getAnimation = (normalAnimation, reducedAnimation = fadeIn) => {
  return prefersReducedMotion() ? reducedAnimation : normalAnimation
}
