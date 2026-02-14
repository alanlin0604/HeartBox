import { Component } from 'react'
import zhTW from '../locales/zh-TW.json'
import en from '../locales/en.json'
import ja from '../locales/ja.json'

const LOCALES = { 'zh-TW': zhTW, en, ja }

function getLocaleText(key) {
  const lang = localStorage.getItem('language') || 'zh-TW'
  const locale = LOCALES[lang] || LOCALES['zh-TW']
  return locale[key] || LOCALES['zh-TW'][key] || key
}

function reportError(error, errorInfo) {
  try {
    const payload = {
      message: error?.message || String(error),
      stack: error?.stack?.slice(0, 2000),
      componentStack: errorInfo?.componentStack?.slice(0, 2000),
      url: window.location.href,
      userAgent: navigator.userAgent,
      timestamp: new Date().toISOString(),
    }
    // Send to backend error reporting endpoint (fire-and-forget)
    const apiBase = import.meta.env.VITE_API_URL || ''
    if (apiBase) {
      fetch(`${apiBase}/api/error-report/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }).catch(() => {})
    }
    // Always log structured error for monitoring
    console.error('[ErrorBoundary]', payload)
  } catch {
    // Silently ignore reporting failures
  }
}

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
    reportError(error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center p-4">
          <div className="glass p-8 w-full max-w-md text-center space-y-4">
            <div className="text-4xl">😢</div>
            <h1 className="text-xl font-bold">{getLocaleText('errorBoundary.title')}</h1>
            <p className="text-sm opacity-60">{getLocaleText('errorBoundary.desc')}</p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => window.location.reload()}
                className="btn-primary"
              >
                {getLocaleText('errorBoundary.reload')}
              </button>
              <button
                onClick={() => {
                  this.setState({ hasError: false, error: null })
                  window.location.href = '/'
                }}
                className="btn-secondary"
              >
                {getLocaleText('errorBoundary.home')}
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
