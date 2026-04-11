/**
 * FeedbackToast Component
 *
 * 成功/錯誤反饋動畫組件
 * 使用 Framer Motion 提供流暢的動畫效果
 */

import { motion, AnimatePresence } from 'framer-motion'
import { useEffect } from 'react'

/**
 * @param {string} type - 類型：'success', 'error', 'info', 'warning'
 * @param {string} message - 訊息內容
 * @param {boolean} isVisible - 是否顯示
 * @param {Function} onClose - 關閉回調
 * @param {number} duration - 自動關閉時間（毫秒），0 表示不自動關閉
 * @param {string} position - 位置：'top', 'bottom', 'top-right', 'bottom-right'
 */
export default function FeedbackToast({
  type = 'success',
  message,
  isVisible = false,
  onClose,
  duration = 3000,
  position = 'top',
}) {
  useEffect(() => {
    if (isVisible && duration > 0) {
      const timer = setTimeout(() => {
        onClose?.()
      }, duration)
      return () => clearTimeout(timer)
    }
  }, [isVisible, duration, onClose])

  // 類型配置
  const typeConfig = {
    success: {
      bg: 'bg-[var(--color-success-500)]/95',
      icon: (
        <motion.svg
          className="w-6 h-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        >
          <motion.path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 13l4 4L19 7"
            initial={{ pathLength: 0 }}
            animate={{ pathLength: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          />
        </motion.svg>
      ),
    },
    error: {
      bg: 'bg-[var(--color-secondary-600)]/95',
      icon: (
        <motion.svg
          className="w-6 h-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          initial={{ scale: 0, rotate: -180 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M6 18L18 6M6 6l12 12"
          />
        </motion.svg>
      ),
    },
    info: {
      bg: 'bg-[var(--color-calm-500)]/95',
      icon: (
        <motion.svg
          className="w-6 h-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 300, damping: 20 }}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </motion.svg>
      ),
    },
    warning: {
      bg: 'bg-[var(--color-accent-500)]/95',
      icon: (
        <motion.svg
          className="w-6 h-6"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          initial={{ scale: 0, y: -10 }}
          animate={{ scale: 1, y: 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 15 }}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </motion.svg>
      ),
    },
  }

  // 位置樣式
  const positionStyles = {
    top: 'top-20 left-1/2 -translate-x-1/2',
    bottom: 'bottom-8 left-1/2 -translate-x-1/2',
    'top-right': 'top-20 right-8',
    'bottom-right': 'bottom-8 right-8',
  }

  const config = typeConfig[type] || typeConfig.success

  // 動畫變體
  const toastVariants = {
    hidden: {
      opacity: 0,
      y: position.includes('bottom') ? 50 : -50,
      scale: 0.3,
    },
    visible: {
      opacity: 1,
      y: 0,
      scale: 1,
    },
    exit: {
      opacity: 0,
      scale: 0.5,
      transition: { duration: 0.2 },
    },
  }

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          role="alert"
          aria-live="polite"
          className={`
            fixed z-[var(--z-toast)] ${positionStyles[position]}
            flex items-center gap-3
            px-6 py-4 rounded-xl
            ${config.bg}
            text-white shadow-lg backdrop-blur-md
            max-w-md
          `.trim().replace(/\s+/g, ' ')}
          variants={toastVariants}
          initial="hidden"
          animate="visible"
          exit="exit"
          transition={{
            type: 'spring',
            stiffness: 500,
            damping: 40,
          }}
        >
          {/* Icon with animation */}
          <div className="flex-shrink-0">
            {config.icon}
          </div>

          {/* Message */}
          <motion.div
            className="flex-1 font-medium"
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
          >
            {message}
          </motion.div>

          {/* Close button */}
          {onClose && (
            <motion.button
              onClick={onClose}
              aria-label="關閉通知"
              className="flex-shrink-0 p-1 hover:bg-white/20 rounded-lg transition-colors"
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </motion.button>
          )}

          {/* Progress bar for auto-dismiss */}
          {duration > 0 && (
            <motion.div
              className="absolute bottom-0 left-0 h-1 bg-white/30 rounded-b-xl"
              initial={{ width: '100%' }}
              animate={{ width: '0%' }}
              transition={{ duration: duration / 1000, ease: 'linear' }}
            />
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
