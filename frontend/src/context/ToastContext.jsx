import { createContext, useCallback, useContext, useMemo, useState } from 'react'

const ToastContext = createContext(null)

let toastSeq = 1

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id))
  }, [])

  const pushToast = useCallback((type, message, timeoutMs = 2600) => {
    const id = toastSeq++
    setToasts((prev) => [...prev, { id, type, message }])
    window.setTimeout(() => removeToast(id), timeoutMs)
  }, [removeToast])

  const api = useMemo(() => ({
    success: (message) => pushToast('success', message),
    error: (message) => pushToast('error', message, 3200),
    info: (message) => pushToast('info', message),
  }), [pushToast])

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="fixed top-4 right-4 z-[100] w-[320px] max-w-[calc(100vw-2rem)] space-y-2">
        {toasts.map((toast) => (
          <button
            key={toast.id}
            type="button"
            onClick={() => removeToast(toast.id)}
            className={`w-full text-left rounded-xl border px-4 py-3 shadow-lg backdrop-blur transition-all ${
              toast.type === 'success'
                ? 'bg-emerald-500/20 border-emerald-400/40 text-emerald-100'
                : toast.type === 'error'
                  ? 'bg-red-500/20 border-red-400/40 text-red-100'
                  : 'bg-blue-500/20 border-blue-400/40 text-blue-100'
            }`}
          >
            <p className="text-sm font-medium">{toast.message}</p>
          </button>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  return useContext(ToastContext)
}
