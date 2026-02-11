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
    const timerId = window.setTimeout(() => removeToast(id), timeoutMs)
    return () => clearTimeout(timerId)
  }, [removeToast])

  const api = useMemo(() => ({
    success: (message) => pushToast('success', message),
    error: (message) => pushToast('error', message, 3200),
    info: (message) => pushToast('info', message),
  }), [pushToast])

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="fixed top-6 left-1/2 -translate-x-1/2 z-[100] w-[400px] max-w-[calc(100vw-2rem)] space-y-2">
        {toasts.map((toast) => (
          <button
            key={toast.id}
            type="button"
            onClick={() => removeToast(toast.id)}
            className={`w-full text-left rounded-xl border-2 px-5 py-4 shadow-2xl backdrop-blur transition-all ${
              toast.type === 'success'
                ? 'bg-emerald-600/40 border-emerald-400/70 text-white'
                : toast.type === 'error'
                  ? 'bg-red-600/40 border-red-400/70 text-white'
                  : 'bg-blue-600/40 border-blue-400/70 text-white'
            }`}
          >
            <div className="flex items-center gap-3">
              <span className="text-xl">{toast.type === 'success' ? '✅' : toast.type === 'error' ? '❌' : 'ℹ️'}</span>
              <p className="text-base font-bold">{toast.message}</p>
            </div>
          </button>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  return useContext(ToastContext)
}
