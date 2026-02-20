import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import LoadingSpinner from './components/LoadingSpinner'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import PrivacyPage from './pages/PrivacyPage'
import TermsPage from './pages/TermsPage'
import NotFoundPage from './pages/NotFoundPage'

// Lazy-load heavy pages for code splitting
const JournalPage = lazy(() => import('./pages/JournalPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const NoteDetailPage = lazy(() => import('./pages/NoteDetailPage'))
const CounselorListPage = lazy(() => import('./pages/CounselorListPage'))
const ChatPage = lazy(() => import('./pages/ChatPage'))
const AIChatPage = lazy(() => import('./pages/AIChatPage'))
const AchievementsPage = lazy(() => import('./pages/AchievementsPage'))
const AdminPage = lazy(() => import('./pages/AdminPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))
const AssessmentsPage = lazy(() => import('./pages/AssessmentsPage'))
const WeeklySummaryPage = lazy(() => import('./pages/WeeklySummaryPage'))
const PsychoContentPage = lazy(() => import('./pages/PsychoContentPage'))
const BreathingPage = lazy(() => import('./pages/BreathingPage'))
const CourseDetailPage = lazy(() => import('./pages/CourseDetailPage'))
const LessonPage = lazy(() => import('./pages/LessonPage'))
const GuidePage = lazy(() => import('./pages/GuidePage'))
const TherapistReportPublicPage = lazy(() => import('./pages/TherapistReportPublicPage'))

function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingSpinner />
  return user ? children : <Navigate to="/login" />
}

function AdminRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingSpinner />
  if (!user) return <Navigate to="/login" />
  return user.is_staff ? children : <Navigate to="/" />
}

function LazyRoute({ children }) {
  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingSpinner />}>
        {children}
      </Suspense>
    </ErrorBoundary>
  )
}

export default function App() {
  return (
    <ErrorBoundary>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/privacy" element={<PrivacyPage />} />
        <Route path="/terms" element={<TermsPage />} />
        {/* Public therapist report (no auth required) */}
        <Route path="/report/:token" element={<LazyRoute><TherapistReportPublicPage /></LazyRoute>} />
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Layout />
            </PrivateRoute>
          }
        >
          <Route index element={<LazyRoute><JournalPage /></LazyRoute>} />
          <Route path="dashboard" element={<LazyRoute><DashboardPage /></LazyRoute>} />
          <Route path="notes/:id" element={<LazyRoute><NoteDetailPage /></LazyRoute>} />
          <Route path="counselors" element={<LazyRoute><CounselorListPage /></LazyRoute>} />
          <Route path="ai-chat" element={<LazyRoute><AIChatPage /></LazyRoute>} />
          <Route path="achievements" element={<LazyRoute><AchievementsPage /></LazyRoute>} />
          <Route path="chat/:id" element={<LazyRoute><ChatPage /></LazyRoute>} />
          <Route path="settings" element={<LazyRoute><SettingsPage /></LazyRoute>} />
          <Route path="assessments" element={<LazyRoute><AssessmentsPage /></LazyRoute>} />
          <Route path="weekly-summary" element={<LazyRoute><WeeklySummaryPage /></LazyRoute>} />
          <Route path="breathe" element={<LazyRoute><BreathingPage /></LazyRoute>} />
          <Route path="learn" element={<LazyRoute><PsychoContentPage /></LazyRoute>} />
          <Route path="learn/courses/:courseId" element={<LazyRoute><CourseDetailPage /></LazyRoute>} />
          <Route path="learn/courses/:courseId/lessons/:lessonId" element={<LazyRoute><LessonPage /></LazyRoute>} />
          <Route path="guide" element={<LazyRoute><GuidePage /></LazyRoute>} />
          <Route
            path="admin"
            element={
              <AdminRoute>
                <LazyRoute><AdminPage /></LazyRoute>
              </AdminRoute>
            }
          />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </ErrorBoundary>
  )
}
