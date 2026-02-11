import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="glass p-8 w-full max-w-md text-center space-y-4">
        <div className="text-6xl font-bold bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent">
          404
        </div>
        <h1 className="text-xl font-semibold">找不到頁面</h1>
        <p className="text-sm opacity-60">
          您要找的頁面不存在或已被移除。
        </p>
        <Link to="/" className="btn-primary inline-block">
          回到首頁
        </Link>
      </div>
    </div>
  )
}
