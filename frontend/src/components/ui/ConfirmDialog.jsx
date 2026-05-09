/**
 * Professional ConfirmDialog Component
 *
 * Features:
 * - Danger vs Normal variants
 * - Customizable actions
 * - Async action support with loading state
 * - Keyboard shortcuts (Enter/Escape)
 * - Auto-focus on primary action
 * - Accessible (ARIA, focus management)
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import Modal from './Modal'
import Button from './Button'

// Warning Icon (for danger variant)
const WarningIcon = () => (
  <svg
    className="w-12 h-12"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    aria-hidden="true"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
    />
  </svg>
)

// Info Icon (for normal variant)
const InfoIcon = () => (
  <svg
    className="w-12 h-12"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.5"
    aria-hidden="true"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M11.25 11.25l.041-.02a.75.75 0 011.063.852l-.708 2.836a.75.75 0 001.063.853l.041-.021M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9-3.75h.008v.008H12V8.25z"
    />
  </svg>
)

export default function ConfirmDialog({
  open = false,
  onClose,
  onConfirm,
  title = '確認操作',
  message = '您確定要執行此操作嗎？',
  confirmText = '確認',
  cancelText = '取消',
  variant = 'normal', // 'normal' | 'danger'
  showIcon = true,
  loading = false,
}) {
  const [isProcessing, setIsProcessing] = useState(false)
  const confirmButtonRef = useRef(null)

  // Handle async confirm. Wrapped in useCallback so the keydown effect below
  // doesn't re-bind the document listener on every render.
  const handleConfirm = useCallback(async () => {
    if (!onConfirm) return

    setIsProcessing(true)
    try {
      await onConfirm()
      onClose?.()
    } catch (error) {
      console.error('Confirm action failed:', error)
      // Keep dialog open on error
    } finally {
      setIsProcessing(false)
    }
  }, [onConfirm, onClose])

  // Keyboard shortcuts
  useEffect(() => {
    if (!open) return

    const handleKeyDown = (e) => {
      // Enter key confirms (only if confirm button is focused or no specific element is focused)
      if (
        e.key === 'Enter' &&
        (document.activeElement === confirmButtonRef.current ||
          document.activeElement === document.body)
      ) {
        e.preventDefault()
        handleConfirm()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, handleConfirm])

  const isDanger = variant === 'danger'
  const Icon = isDanger ? WarningIcon : InfoIcon

  const iconColorClass = isDanger
    ? 'text-red-500'
    : 'text-blue-500'

  const confirmButtonVariant = isDanger ? 'danger' : 'primary'

  return (
    <Modal
      open={open}
      onClose={onClose}
      size="sm"
      showCloseButton={false}
      swipeToDismiss={false}
      className="!p-0"
    >
      <div className="p-6">
        {/* Icon & Title */}
        <div className="flex flex-col items-center text-center mb-4">
          {showIcon && (
            <div className={`mb-4 ${iconColorClass}`}>
              <Icon />
            </div>
          )}

          <h2
            id="confirm-dialog-title"
            className="text-xl font-semibold text-[var(--text-primary)] mb-2"
          >
            {title}
          </h2>

          {message && (
            <p className="text-sm text-[var(--text-secondary)] leading-relaxed max-w-sm">
              {message}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-col-reverse sm:flex-row gap-3 mt-6">
          <Button
            variant="secondary"
            fullWidth
            onClick={onClose}
            disabled={isProcessing || loading}
            type="button"
          >
            {cancelText}
          </Button>

          <Button
            ref={confirmButtonRef}
            variant={confirmButtonVariant}
            fullWidth
            onClick={handleConfirm}
            loading={isProcessing || loading}
            disabled={isProcessing || loading}
            type="button"
            autoFocus
          >
            {confirmText}
          </Button>
        </div>
      </div>

      {/* Danger variant warning */}
      {isDanger && (
        <div className="bg-red-500/10 border-t border-red-500/20 px-6 py-3">
          <p className="text-xs text-red-400 text-center">
            ⚠️ 此操作無法撤銷，請謹慎確認
          </p>
        </div>
      )}
    </Modal>
  )
}

// Hook for easier usage
// eslint-disable-next-line react-refresh/only-export-components
export function useConfirmDialog() {
  const [dialog, setDialog] = useState({
    open: false,
    title: '',
    message: '',
    onConfirm: null,
    variant: 'normal',
  })

  const confirm = (options) => {
    return new Promise((resolve, reject) => {
      setDialog({
        open: true,
        title: options.title || '確認操作',
        message: options.message || '',
        variant: options.variant || 'normal',
        confirmText: options.confirmText,
        cancelText: options.cancelText,
        onConfirm: async () => {
          try {
            if (options.onConfirm) {
              await options.onConfirm()
            }
            resolve(true)
          } catch (error) {
            reject(error)
          }
        },
      })
    })
  }

  const close = () => {
    setDialog((prev) => ({ ...prev, open: false }))
  }

  const DialogComponent = (
    <ConfirmDialog
      {...dialog}
      onClose={close}
    />
  )

  return {
    confirm,
    close,
    ConfirmDialog: DialogComponent,
  }
}
