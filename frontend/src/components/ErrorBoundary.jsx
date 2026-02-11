import { Component } from 'react'

const TEXTS = {
  'zh-TW': { title: '發生了一些問題', desc: '應用程式遇到了未預期的錯誤，請嘗試重新整理頁面。', reload: '重新整理', home: '回首頁' },
  en: { title: 'Something went wrong', desc: 'The app encountered an unexpected error. Please try refreshing.', reload: 'Refresh', home: 'Go Home' },
  ja: { title: '問題が発生しました', desc: 'アプリで予期しないエラーが発生しました。ページを更新してみてください。', reload: '更新する', home: 'ホームへ' },
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
  }

  render() {
    if (this.state.hasError) {
      const lang = localStorage.getItem('language') || 'zh-TW'
      const txt = TEXTS[lang] || TEXTS['zh-TW']

      return (
        <div className="min-h-screen flex items-center justify-center p-4">
          <div className="glass p-8 w-full max-w-md text-center space-y-4">
            <div className="text-4xl">😢</div>
            <h1 className="text-xl font-bold">{txt.title}</h1>
            <p className="text-sm opacity-60">{txt.desc}</p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => window.location.reload()}
                className="btn-primary"
              >
                {txt.reload}
              </button>
              <button
                onClick={() => {
                  this.setState({ hasError: false, error: null })
                  window.location.href = '/'
                }}
                className="btn-secondary"
              >
                {txt.home}
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
