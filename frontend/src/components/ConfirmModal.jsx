import { useEffect, useRef } from 'react'

export default function ConfirmModal({
  open: openProp,
  isOpen,
  title,
  message,
  confirmText,
  cancelText,
  loading = false,
  // `variant` prop is accepted (older callers pass "danger") but currently
  // unused since the modal only renders the danger style. Swallow via rest
  // so ESLint doesn't flag it.
  onConfirm,
  onCancel,
  // eslint-disable-next-line no-unused-vars
  ...rest
}) {
  // Some callers pass `open`, others `isOpen` (or rely on conditional
  // rendering without passing either). Default to true if rendered at
  // all — callers conditionally render the component itself, so being
  // mounted = should display.
  const open = openProp ?? isOpen ?? true
  const modalRef = useRef(null)

  useEffect(() => {
    if (!open) return

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onCancel()
        return
      }
      // Focus trap
      if (e.key === 'Tab') {
        const focusable = modalRef.current?.querySelectorAll(
          'button:not([disabled]), [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
        if (!focusable || focusable.length === 0) return
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault()
            last.focus()
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault()
            first.focus()
          }
        }
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    // Auto-focus first button
    const firstBtn = modalRef.current?.querySelector('button')
    firstBtn?.focus()

    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onCancel])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div ref={modalRef} className="popup-panel w-full max-w-md rounded-xl p-6 space-y-4" role="dialog" aria-modal="true" aria-labelledby="confirm-modal-title">
        <h3 id="confirm-modal-title" className="text-lg font-semibold">{title}</h3>
        <p className="text-sm opacity-75">{message}</p>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onCancel} className="btn-secondary" disabled={loading}>
            {cancelText}
          </button>
          <button type="button" onClick={onConfirm} className="btn-danger" disabled={loading}>
            {loading ? '...' : confirmText}
          </button>
        </div>
      </div>
    </div>
  )
}
