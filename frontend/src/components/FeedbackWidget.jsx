import { useState } from 'react'
import { submitFeedback } from '../api/feedback'
import { useLang } from '../context/LanguageContext'
import { useToast } from '../context/ToastContext'

const STARS = [1, 2, 3, 4, 5]

export default function FeedbackWidget() {
  const { t } = useLang()
  const toast = useToast()
  const [open, setOpen] = useState(false)
  const [rating, setRating] = useState(0)
  const [hover, setHover] = useState(0)
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  const handleSubmit = async () => {
    if (rating === 0 || !content.trim()) return
    setLoading(true)
    try {
      await submitFeedback(rating, content.trim())
      toast?.success(t('feedback.success'))
      setSubmitted(true)
      setTimeout(() => {
        setOpen(false)
        setSubmitted(false)
        setRating(0)
        setContent('')
      }, 2000)
    } catch {
      toast?.error(t('feedback.failed'))
    } finally {
      setLoading(false)
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="glass-card p-4 w-full text-left hover:bg-white/10 transition-colors cursor-pointer group"
      >
        <div className="flex items-center gap-2">
          <span className="text-xl">💬</span>
          <div>
            <p className="text-sm font-semibold group-hover:text-purple-400 transition-colors">
              {t('feedback.title')}
            </p>
            <p className="text-xs opacity-50 mt-0.5">{t('feedback.subtitle')}</p>
          </div>
        </div>
      </button>
    )
  }

  return (
    <div className="glass-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">{t('feedback.title')}</h3>
        <button
          onClick={() => { setOpen(false); setRating(0); setContent('') }}
          className="text-xs opacity-50 hover:opacity-100 cursor-pointer"
        >
          ✕
        </button>
      </div>

      {submitted ? (
        <p className="text-sm text-green-400 text-center py-2">{t('feedback.thanks')}</p>
      ) : (
        <>
          {/* Star rating */}
          <div className="flex gap-1 justify-center">
            {STARS.map((star) => (
              <button
                key={star}
                onClick={() => setRating(star)}
                onMouseEnter={() => setHover(star)}
                onMouseLeave={() => setHover(0)}
                className="text-2xl cursor-pointer transition-transform hover:scale-110"
                aria-label={`${star} / 5`}
              >
                {star <= (hover || rating) ? '★' : '☆'}
              </button>
            ))}
          </div>

          {/* Content */}
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder={t('feedback.placeholder')}
            rows={3}
            maxLength={1000}
            className="glass-input text-sm w-full resize-none"
          />

          <button
            onClick={handleSubmit}
            disabled={loading || rating === 0 || !content.trim()}
            className="btn-primary w-full text-sm disabled:opacity-30"
          >
            {loading ? t('feedback.submitting') : t('feedback.submit')}
          </button>
        </>
      )}
    </div>
  )
}
