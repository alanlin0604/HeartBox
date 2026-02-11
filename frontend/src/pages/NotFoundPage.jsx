import { Link } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'

export default function NotFoundPage() {
  const { t } = useLang()

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="glass p-8 w-full max-w-md text-center space-y-4">
        <div className="text-6xl font-bold bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent">
          404
        </div>
        <h1 className="text-xl font-semibold">{t('notFound.title')}</h1>
        <p className="text-sm opacity-60">{t('notFound.desc')}</p>
        <Link to="/" className="btn-primary inline-block">
          {t('notFound.home')}
        </Link>
      </div>
    </div>
  )
}
