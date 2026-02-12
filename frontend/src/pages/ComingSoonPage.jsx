import { useNavigate } from 'react-router-dom'
import { useLang } from '../context/LanguageContext'

export default function ComingSoonPage() {
  const navigate = useNavigate()
  const { t } = useLang()

  return (
    <div className="flex flex-col items-center justify-center flex-1 text-center space-y-6 py-20">
      <div className="text-6xl opacity-30">🚧</div>
      <h2 className="text-2xl font-bold">{t('comingSoon.title')}</h2>
      <p className="opacity-60 max-w-md">{t('comingSoon.desc')}</p>
      <button
        onClick={() => navigate('/')}
        className="btn-primary"
      >
        {t('comingSoon.home')}
      </button>
    </div>
  )
}
