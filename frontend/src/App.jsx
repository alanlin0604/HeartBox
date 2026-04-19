import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import LoadingSpinner from './components/LoadingSpinner'
import PageTransition from './components/PageTransition'
import OfflineIndicator from './components/OfflineIndicator'
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
const PersonalDashboardPage = lazy(() => import('./pages/PersonalDashboardPage'))
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
const LandingPage = lazy(() => import('./pages/LandingPage'))
const VerifyEmailPage = lazy(() => import('./pages/VerifyEmailPage'))
const PricingPage = lazy(() => import('./pages/PricingPage'))
const DataImportPage = lazy(() => import('./pages/DataImportPage'))
const HabitsPage = lazy(() => import('./pages/HabitsPage'))
const FriendsPage = lazy(() => import('./pages/FriendsPage'))
const SleepAnalysisPage = lazy(() => import('./pages/SleepAnalysisPage'))
const CommunityPage = lazy(() => import('./pages/CommunityPage'))

function PrivateRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingSpinner />
  return user ? children : <Navigate to="/login" />
}

function HomeRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingSpinner />
  return user ? children : <LazyRoute><LandingPage /></LazyRoute>
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
  const location = useLocation()
  return (
    <>
      <OfflineIndicator />
      <ErrorBoundary key={location.pathname}>
      <AnimatePresence mode="wait" initial={false}>
        <Routes location={location} key={location.pathname}>
          <Route path="/login" element={<PageTransition><LoginPage /></PageTransition>} />
          <Route path="/register" element={<PageTransition><RegisterPage /></PageTransition>} />
          <Route path="/forgot-password" element={<PageTransition><ForgotPasswordPage /></PageTransition>} />
          <Route path="/reset-password" element={<PageTransition><ResetPasswordPage /></PageTransition>} />
          <Route path="/privacy" element={<PageTransition><PrivacyPage /></PageTransition>} />
          <Route path="/terms" element={<PageTransition><TermsPage /></PageTransition>} />
          {/* Public therapist report (no auth required) */}
          <Route path="/report/:token" element={<LazyRoute><PageTransition><TherapistReportPublicPage /></PageTransition></LazyRoute>} />
          <Route path="/verify-email" element={<LazyRoute><PageTransition><VerifyEmailPage /></PageTransition></LazyRoute>} />
          <Route path="/pricing" element={<LazyRoute><PageTransition><PricingPage /></PageTransition></LazyRoute>} />
          <Route
            path="/"
            element={
              <HomeRoute>
                <Layout />
              </HomeRoute>
            }
          >
            <Route index element={<LazyRoute><PageTransition><JournalPage /></PageTransition></LazyRoute>} />
            <Route path="dashboard" element={<LazyRoute><PageTransition><DashboardPage /></PageTransition></LazyRoute>} />
            <Route path="personal-dashboard" element={<LazyRoute><PageTransition><PersonalDashboardPage /></PageTransition></LazyRoute>} />
            <Route path="notes/:id" element={<LazyRoute><PageTransition><NoteDetailPage /></PageTransition></LazyRoute>} />
            <Route path="counselors" element={<LazyRoute><PageTransition><CounselorListPage /></PageTransition></LazyRoute>} />
            <Route path="ai-chat" element={<LazyRoute><PageTransition><AIChatPage /></PageTransition></LazyRoute>} />
            <Route path="achievements" element={<LazyRoute><PageTransition><AchievementsPage /></PageTransition></LazyRoute>} />
            <Route path="chat/:id" element={<LazyRoute><PageTransition><ChatPage /></PageTransition></LazyRoute>} />
            <Route path="settings" element={<LazyRoute><PageTransition><SettingsPage /></PageTransition></LazyRoute>} />
            <Route path="assessments" element={<LazyRoute><PageTransition><AssessmentsPage /></PageTransition></LazyRoute>} />
            <Route path="weekly-summary" element={<LazyRoute><PageTransition><WeeklySummaryPage /></PageTransition></LazyRoute>} />
            <Route path="breathe" element={<LazyRoute><PageTransition><BreathingPage /></PageTransition></LazyRoute>} />
            <Route path="learn" element={<LazyRoute><PageTransition><PsychoContentPage /></PageTransition></LazyRoute>} />
            <Route path="learn/courses/:courseId" element={<LazyRoute><PageTransition><CourseDetailPage /></PageTransition></LazyRoute>} />
            <Route path="learn/courses/:courseId/lessons/:lessonId" element={<LazyRoute><PageTransition><LessonPage /></PageTransition></LazyRoute>} />
            <Route path="guide" element={<LazyRoute><PageTransition><GuidePage /></PageTransition></LazyRoute>} />
            <Route path="import" element={<LazyRoute><PageTransition><DataImportPage /></PageTransition></LazyRoute>} />
            <Route path="habits" element={<LazyRoute><PageTransition><HabitsPage /></PageTransition></LazyRoute>} />
            <Route path="friends" element={<LazyRoute><PageTransition><FriendsPage /></PageTransition></LazyRoute>} />
            <Route path="sleep-analysis" element={<LazyRoute><PageTransition><SleepAnalysisPage /></PageTransition></LazyRoute>} />
            <Route path="community" element={<LazyRoute><PageTransition><CommunityPage /></PageTransition></LazyRoute>} />
            <Route
              path="admin"
              element={
                <AdminRoute>
                  <LazyRoute><PageTransition><AdminPage /></PageTransition></LazyRoute>
                </AdminRoute>
              }
            />
          </Route>
          <Route path="*" element={<PageTransition><NotFoundPage /></PageTransition>} />
        </Routes>
      </AnimatePresence>
    </ErrorBoundary>
    </>
  )
}
