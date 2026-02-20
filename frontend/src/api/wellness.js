import api from './axios'

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

// Psycho Education Articles
export const getArticles = (category) =>
  api.get(`/articles/${category ? `?category=${category}` : ''}`)

export const getArticleDetail = (id) =>
  api.get(`/articles/${id}/`)

// Courses
export const getCourses = () =>
  api.get('/courses/')

export const getCourseDetail = (id) =>
  api.get(`/courses/${id}/`)

export const completeLesson = (articleId) =>
  api.post(`/lessons/${articleId}/complete/`)

// Share assessment with counselor
export const shareAssessment = (assessmentId, counselorId) =>
  api.post(`/assessments/${assessmentId}/share/`, { counselor_id: counselorId })

// Shared assessments received (counselor)
export const getSharedAssessments = () =>
  api.get('/shared-assessments/')

// Weekly Summary PDF export (by summary ID for reliability)
export const exportWeeklySummaryPDF = (summaryId, lang) =>
  api.get(`/weekly-summary/?id=${summaryId}&format=pdf${lang ? `&lang=${lang}` : ''}`, { responseType: 'blob' })
