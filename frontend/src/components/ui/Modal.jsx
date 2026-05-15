/**
 * Modern Modal Component with Mobile Enhancements
 * Follows HeartBox Design System - Glassmorphism with smooth animations
 *
 * Features:
 * - Swipe-to-dismiss on mobile (drag down to close)
 * - Improved backdrop contrast (70% black for better legibility)
 * - Exit animations
 * - Focus management and restoration
 * - Full keyboard accessibility
 * - Reduced motion support
 */

import { useEffect, useRef } from 'react'
import { createPortal } from 'react-dom'
import { motion, AnimatePresence } from 'framer-motion'

export default function Modal({
  open: openProp,
  isOpen,
  onClose,
  title,
  children,
  footer,
  size = 'md',
  closeOnBackdrop = true,
  showCloseButton = true,
  swipeToDismiss = true,
  className = ''
}) {
  // Accept either `open` or `isOpen` — the codebase has both styles
  // (MetricsManager/WidgetSettings/CommunityPage/PersonalDashboardPage
  // use isOpen; older callers use open). Without this alias, those
  // modals silently never render.
  const open = openProp ?? isOpen ?? false
  const modalRef = useRef(null)
  const previousFocusRef = useRef(null)

  // Save previous focus and restore on close.
  // Guard against restoring to an element that's been removed from the DOM
  // (e.g. the trigger lived inside a list item that re-rendered) — focusing
  // a detached node throws in some browsers.
  useEffect(() => {
    if (open) {
      previousFocusRef.current = document.activeElement
    } else if (previousFocusRef.current) {
      const target = previousFocusRef.current
      if (target.isConnected && typeof target.focus === 'function') {
        try { target.focus() } catch { /* element no longer focusable */ }
      }
      previousFocusRef.current = null
    }
  }, [open])

  // Close on Escape key
  useEffect(() => {
    if (!open) return

    const handleEscape = (e) => {
      if (e.key === 'Escape' && onClose) {
        onClose()
      }
    }

    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [open, onClose])

  // Focus trap
  useEffect(() => {
    if (!open || !modalRef.current) return

    const focusableElements = modalRef.current.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    const firstElement = focusableElements[0]
    const lastElement = focusableElements[focusableElements.length - 1]

    const handleTab = (e) => {
      if (e.key !== 'Tab') return

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          lastElement?.focus()
          e.preventDefault()
        }
      } else {
        if (document.activeElement === lastElement) {
          firstElement?.focus()
          e.preventDefault()
        }
      }
    }

    // Focus first element after a short delay to ensure modal is rendered
    setTimeout(() => firstElement?.focus(), 50)

    document.addEventListener('keydown', handleTab)
    return () => document.removeEventListener('keydown', handleTab)
  }, [open])

  // Prevent scroll when modal is open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [open])

  const sizes = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
    full: 'max-w-full mx-4'
  }

  const handleBackdropClick = (e) => {
    if (closeOnBackdrop && e.target === e.currentTarget && onClose) {
      onClose()
    }
  }

  // Handle swipe-to-dismiss
  const handleDragEnd = (event, info) => {
    if (!swipeToDismiss || !onClose) return

    // If dragged down more than 150px, close the modal
    if (info.offset.y > 150) {
      onClose()
    }
  }

  // Animation variants
  const backdropVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1 },
    exit: { opacity: 0 }
  }

  const modalVariants = {
    hidden: {
      opacity: 0,
      scale: 0.95,
      y: 20
    },
    visible: {
      opacity: 1,
      scale: 1,
      y: 0,
      transition: {
        type: 'spring',
        stiffness: 300,
        damping: 30
      }
    },
    exit: {
      opacity: 0,
      scale: 0.95,
      y: 20,
      transition: {
        duration: 0.2
      }
    }
  }

  const modalContent = (
    <AnimatePresence mode="wait">
      {open && (
        <div
          className="fixed inset-0 z-[var(--z-modal)] flex items-center justify-center p-4"
          onClick={handleBackdropClick}
          role="dialog"
          aria-modal="true"
          aria-labelledby={title ? "modal-title" : undefined}
          aria-describedby="modal-body"
        >
          {/* Backdrop - improved contrast (70% instead of 60%) */}
          <motion.div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            variants={backdropVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            transition={{ duration: 0.2 }}
          />

          {/* Modal */}
          <motion.div
            ref={modalRef}
            className={`
              relative w-full ${sizes[size]}
              bg-[var(--glass-bg)] backdrop-blur-xl
              border border-[var(--glass-border)]
              rounded-2xl shadow-[var(--glass-shadow-lg)]
              max-h-[90vh] overflow-y-auto
              ${className}
            `.trim().replace(/\s+/g, ' ')}
            variants={modalVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            drag={swipeToDismiss ? "y" : false}
            dragConstraints={{ top: 0, bottom: 300 }}
            dragElastic={{ top: 0, bottom: 0.8 }}
            onDragEnd={handleDragEnd}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Swipe indicator (mobile) */}
            {swipeToDismiss && (
              <div
                className="flex justify-center pt-3 pb-1 cursor-grab active:cursor-grabbing md:hidden"
                aria-hidden="true"
              >
                <div className="w-12 h-1 bg-white/20 rounded-full" />
              </div>
            )}

            {/* Header */}
            {(title || showCloseButton) && (
              <div className="flex items-center justify-between p-6 border-b border-[var(--border-primary)]">
                {title && (
                  <h2
                    id="modal-title"
                    className="text-xl font-semibold text-[var(--text-primary)]"
                  >
                    {title}
                  </h2>
                )}
                {showCloseButton && (
                  <button
                    onClick={onClose}
                    type="button"
                    className="ml-auto min-h-[44px] min-w-[44px] flex items-center justify-center rounded-lg hover:bg-[var(--surface-primary)] transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary-400)]"
                    aria-label="Close modal"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            )}

            {/* Content */}
            <div id="modal-body" className="p-6">
              {children}
            </div>

            {/* Footer */}
            {footer && (
              <div className="flex items-center justify-end gap-3 p-6 border-t border-[var(--border-primary)]">
                {footer}
              </div>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )

  return createPortal(modalContent, document.body)
}
