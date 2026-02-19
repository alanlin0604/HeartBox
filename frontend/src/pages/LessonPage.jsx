import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import DOMPurify from 'dompurify'
import { getArticleDetail, getCourseDetail, completeLesson } from '../api/wellness'
import { useLang } from '../context/LanguageContext'
import LoadingSpinner from '../components/LoadingSpinner'

/** Minimal markdown → HTML */
function mdToHtml(md) {
  if (!md) return ''
  return md
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>')
    .replace(/\n{2,}/g, '</p><p>')
    .replace(/\n/g, '<br/>')
    .replace(/^/, '<p>')
    .replace(/$/, '</p>')
    .replace(/<p><h([123])>/g, '<h$1>')
    .replace(/<\/h([123])><\/p>/g, '</h$1>')
    .replace(/<p><ul>/g, '<ul>')
    .replace(/<\/ul><\/p>/g, '</ul>')
    .replace(/<p><\/p>/g, '')
}

const LANG_FIELD_MAP = { 'zh-TW': 'zh', en: 'en', ja: 'ja' }

export default function LessonPage() {
  const { courseId, lessonId } = useParams()
  const navigate = useNavigate()
  const { t, lang } = useLang()
  const [article, setArticle] = useState(null)
  const [course, setCourse] = useState(null)
  const [loading, setLoading] = useState(true)
  const [completing, setCompleting] = useState(false)
  const [completed, setCompleted] = useState(false)

  const langKey = LANG_FIELD_MAP[lang] || 'en'

  useEffect(() => {
    setLoading(true)
    Promise.all([
      getArticleDetail(lessonId),
      getCourseDetail(courseId),
    ])
      .then(([articleRes, courseRes]) => {
        setArticle(articleRes.data)
        setCourse(courseRes.data)
        // Check if this lesson is already completed
        const lessons = courseRes.data?.lessons || []
        const thisLesson = lessons.find(l => l.id === Number(lessonId))
        if (thisLesson?.is_completed) setCompleted(true)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [courseId, lessonId])

  useEffect(() => {
    if (article) {
      const title = article[`title_${langKey}`] || article.title_en
      document.title = `${title} — ${t('app.name')}`
    }
  }, [article, langKey, t])

  const handleComplete = async () => {
    setCompleting(true)
    try {
      await completeLesson(lessonId)
      setCompleted(true)
    } catch {}
    setCompleting(false)
  }

  if (loading) return <LoadingSpinner />
  if (!article) return (
    <div className="text-center py-20 opacity-60">
      <p>{t('learn.lessonNotFound')}</p>
      <button onClick={() => navigate(`/learn/courses/${courseId}`)} className="btn-primary mt-4">{t('common.goBack')}</button>
    </div>
  )

  const title = article[`title_${langKey}`] || article.title_en
  const content = article[`content_${langKey}`] || article.content_en
  const courseTitle = course ? (course[`title_${langKey}`] || course.title_en) : ''
  const lessons = course?.lessons || []
  const currentIdx = lessons.findIndex(l => l.id === Number(lessonId))
  const prevLesson = currentIdx > 0 ? lessons[currentIdx - 1] : null
  const nextLesson = currentIdx < lessons.length - 1 ? lessons[currentIdx + 1] : null

  return (
    <div className="space-y-6 mt-4 max-w-3xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm opacity-60 flex-wrap">
        <Link to="/learn" className="hover:opacity-100 transition-opacity">{t('nav.learn')}</Link>
        <span>/</span>
        <Link to={`/learn/courses/${courseId}`} className="hover:opacity-100 transition-opacity">{courseTitle}</Link>
        <span>/</span>
        <span>{title}</span>
      </div>

      {/* Article content */}
      <div className="glass p-6">
        <h1 className="text-2xl font-bold mb-4">{title}</h1>
        <div className="flex items-center gap-3 text-xs opacity-50 mb-6">
          <span className="px-2 py-0.5 rounded bg-purple-500/15 text-purple-400">
            {t(`learn.${article.category}`)}
          </span>
          <span>{article.reading_time} {t('learn.minRead')}</span>
        </div>
        <div
          className="prose prose-invert max-w-none text-sm leading-relaxed opacity-80"
          dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(mdToHtml(content)) }}
        />
        {article.source && (
          <p className="text-xs opacity-40 mt-6 pt-3 border-t border-[var(--card-border)]">
            {t('learn.source')}: {article.source}
          </p>
        )}
      </div>

      {/* Complete button */}
      <div className="flex justify-center">
        {completed ? (
          <div className="flex items-center gap-2 text-green-400 text-sm font-medium">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            {t('learn.lessonCompleted')}
          </div>
        ) : (
          <button
            onClick={handleComplete}
            disabled={completing}
            className="btn-primary"
          >
            {completing ? t('common.saving') : t('learn.markComplete')}
          </button>
        )}
      </div>

      {/* Prev / Next navigation */}
      <div className="flex items-center justify-between gap-4">
        {prevLesson ? (
          <button
            onClick={() => navigate(`/learn/courses/${courseId}/lessons/${prevLesson.id}`)}
            className="glass px-4 py-3 flex items-center gap-2 hover:bg-purple-500/5 transition-colors cursor-pointer text-sm"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
            <span className="opacity-60">{prevLesson[`title_${langKey}`] || prevLesson.title_en}</span>
          </button>
        ) : <div />}
        {nextLesson ? (
          <button
            onClick={() => navigate(`/learn/courses/${courseId}/lessons/${nextLesson.id}`)}
            className="glass px-4 py-3 flex items-center gap-2 hover:bg-purple-500/5 transition-colors cursor-pointer text-sm"
          >
            <span className="opacity-60">{nextLesson[`title_${langKey}`] || nextLesson.title_en}</span>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
        ) : <div />}
      </div>
    </div>
  )
}
