import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getCourseDetail } from '../api/wellness'
import { useLang } from '../context/LanguageContext'
import LoadingSpinner from '../components/LoadingSpinner'

const LANG_FIELD_MAP = { 'zh-TW': 'zh', en: 'en', ja: 'ja' }

export default function CourseDetailPage() {
  const { courseId } = useParams()
  const navigate = useNavigate()
  const { t, lang } = useLang()
  const [course, setCourse] = useState(null)
  const [loading, setLoading] = useState(true)

  const langKey = LANG_FIELD_MAP[lang] || 'en'

  useEffect(() => {
    setLoading(true)
    getCourseDetail(courseId)
      .then((res) => setCourse(res.data))
      .catch(() => setCourse(null))
      .finally(() => setLoading(false))
  }, [courseId])

  useEffect(() => {
    if (course) {
      const title = course[`title_${langKey}`] || course.title_en
      document.title = `${title} — ${t('app.name')}`
    }
  }, [course, langKey, t])

  if (loading) return <LoadingSpinner />
  if (!course) return (
    <div className="text-center py-20 opacity-60">
      <p>{t('learn.courseNotFound')}</p>
      <button onClick={() => navigate('/learn')} className="btn-primary mt-4">{t('common.goBack')}</button>
    </div>
  )

  const title = course[`title_${langKey}`] || course.title_en
  const desc = course[`description_${langKey}`] || course.description_en
  const lessons = course.lessons || []
  const pct = course.progress_pct || 0

  return (
    <div className="space-y-6 mt-4 max-w-3xl mx-auto">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm opacity-60">
        <Link to="/learn" className="hover:opacity-100 transition-opacity">{t('nav.learn')}</Link>
        <span>/</span>
        <span>{title}</span>
      </div>

      {/* Course header */}
      <div className="glass p-6">
        <div className="flex items-start gap-4">
          <span className="text-4xl">{course.icon_emoji}</span>
          <div className="flex-1">
            <h1 className="text-2xl font-bold">{title}</h1>
            <p className="text-sm opacity-60 mt-2">{desc}</p>
            <div className="mt-4 flex items-center gap-3">
              <div className="flex-1 h-2.5 rounded-full bg-[var(--card-border)] overflow-hidden">
                <div
                  className="h-full rounded-full bg-purple-500 transition-all"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="text-sm font-medium">{Math.round(pct)}%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Lesson list */}
      <div className="space-y-2">
        {lessons.map((lesson, idx) => {
          const lessonTitle = lesson[`title_${langKey}`] || lesson.title_en
          return (
            <button
              key={lesson.id}
              onClick={() => navigate(`/learn/courses/${courseId}/lessons/${lesson.id}`)}
              className="glass w-full p-4 flex items-center gap-4 hover:bg-purple-500/5 transition-colors cursor-pointer text-left"
            >
              <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                lesson.is_completed
                  ? 'bg-green-500/20 text-green-400'
                  : 'bg-[var(--card-border)] opacity-60'
              }`}>
                {lesson.is_completed ? (
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                ) : (
                  idx + 1
                )}
              </span>
              <div className="flex-1 min-w-0">
                <h3 className="font-medium">{lessonTitle}</h3>
                <span className="text-xs opacity-50">{lesson.reading_time} {t('learn.minRead')}</span>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
