import api from './axios'
import { getCached, setCache, invalidate } from './cache'

// Year Pixels
export const getYearPixels = (year) =>
  api.get(`/analytics/year-pixels/?year=${year}`)

// Daily Prompt
export const getDailyPrompt = () =>
  api.get('/daily-prompt/')

// Self Assessments
export const getAssessments = (type) =>
  api.get(`/assessments/${type ? `?type=${type}` : ''}`)

export const createAssessment = (data) =>
  api.post('/assessments/', data)

// Weekly Summary
export const getWeeklySummary = (weekStart) =>
  api.get(`/weekly-summary/?week_start=${weekStart}`)

export const getWeeklySummaryList = () =>
  api.get('/weekly-summary/list/')

// Therapist Reports
export const createTherapistReport = (data) =>
  api.post('/reports/', data)

export const getTherapistReports = () =>
  api.get('/reports/list/')

export const getPublicReport = (token) =>
  api.get(`/reports/public/${token}/`)

// Psycho Education Articles — fully editorial, cache aggressively client-side
export const getArticles = (category) => {
  const key = `articles:${category || 'all'}`
  const cached = getCached(key)
  if (cached) return Promise.resolve(cached)
  return api
    .get(`/articles/${category ? `?category=${category}` : ''}`)
    .then((res) => {
      setCache(key, res, 10 * 60_000)
      return res
    })
}

export const getArticleDetail = (id) => {
  const key = `article:${id}`
  const cached = getCached(key)
  if (cached) return Promise.resolve(cached)
  return api.get(`/articles/${id}/`).then((res) => {
    setCache(key, res, 10 * 60_000)
    return res
  })
}

// Courses
export const getCourses = () => {
  const key = 'courses:list'
  const cached = getCached(key)
  if (cached) return Promise.resolve(cached)
  return api.get('/courses/').then((res) => {
    setCache(key, res, 10 * 60_000)
    return res
  })
}

export const getCourseDetail = (id) => {
  const key = `course:${id}`
  const cached = getCached(key)
  if (cached) return Promise.resolve(cached)
  return api.get(`/courses/${id}/`).then((res) => {
    // Course progress changes per user — shorter cache, invalidate on completeLesson.
    setCache(key, res, 2 * 60_000)
    return res
  })
}

export const completeLesson = (articleId) => {
  // Invalidate cached course detail/list so the new completion state shows
  // up on the next read without waiting for the 2-minute TTL.
  invalidate('course:')
  invalidate('courses:')
  return api.post(`/lessons/${articleId}/complete/`)
}

// Share assessment with counselor
export const shareAssessment = (assessmentId, counselorId) =>
  api.post(`/assessments/${assessmentId}/share/`, { counselor_id: counselorId })

// Shared assessments received (counselor)
export const getSharedAssessments = () =>
  api.get('/shared-assessments/')

// Weekly Summary PDF export (use 'export' param — DRF intercepts 'format')
export const exportWeeklySummaryPDF = (weekStart, lang) =>
  api.get(`/weekly-summary/?week_start=${weekStart}&export=pdf${lang ? `&lang=${lang}` : ''}`, { responseType: 'blob' })
