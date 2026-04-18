/**
 * Toast Context with Professional Toast System
 * Features:
 * - SVG icons (no emoji)
 * - Swipe-to-dismiss
 * - Auto-dismiss with progress bar
 * - Stack management (max 3 toasts)
 * - 4 types: success, error, info, warning
 */

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { useLang } from './LanguageContext'
import { ToastContainer } from '../components/ui/Toast'

const ToastContext = createContext(null)

let toastSeq = 1

export function ToastProvider({ children }) {
  const { t } = useLang()
  const [toasts, setToasts] = useState([])

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id))
  }, [])

  const pushToast = useCallback((type, message, duration = 3000, options = {}) => {
    const id = toastSeq++
    setToasts((prev) => [...prev, {
      id,
      type,
      message,
      duration,
      showProgress: options.showProgress !== false,
      ...options
    }])
    return id
  }, [])

  const api = useMemo(() => ({
    success: (message, options) => pushToast('success', message, 3000, options),
    error: (message, options) => pushToast('error', message, 4000, options),
    info: (message, options) => pushToast('info', message, 3000, options),
    warning: (message, options) => pushToast('warning', message, 3500, options),
    dismiss: (id) => removeToast(id),
    dismissAll: () => setToasts([]),
  }), [pushToast, removeToast])

  // Listen for global API error events from axios interceptor
  useEffect(() => {
    const handler = (e) => {
      const msg = e.detail?.messageKey ? t(e.detail.messageKey) : (e.detail?.message || 'Server error')
      api.error(msg)
    }
    window.addEventListener('api-error', handler)
    return () => window.removeEventListener('api-error', handler)
  }, [api, t])

  return (
    <ToastContext.Provider value={api}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  )
}

export function useToast() {
  return useContext(ToastContext)
}
