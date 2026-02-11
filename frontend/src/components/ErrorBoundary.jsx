import { Component } from 'react'

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
      return (
        <div className="min-h-screen flex items-center justify-center p-4">
          <div className="glass p-8 w-full max-w-md text-center space-y-4">
            <div className="text-4xl">😢</div>
            <h1 className="text-xl font-bold">發生了一些問題</h1>
            <p className="text-sm opacity-60">
              應用程式遇到了未預期的錯誤，請嘗試重新整理頁面。
            </p>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => window.location.reload()}
                className="btn-primary"
              >
                重新整理
              </button>
              <button
                onClick={() => {
                  this.setState({ hasError: false, error: null })
                  window.location.href = '/'
                }}
                className="btn-secondary"
              >
                回首頁
              </button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
