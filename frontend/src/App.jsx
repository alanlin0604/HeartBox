import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import ErrorBoundary from './components/ErrorBoundary'
import LoadingSpinner from './components/LoadingSpinner'
import PageTransition from './components/PageTransition'
import OfflineIndicator from './components/OfflineIndicator'
import VersionBadge from './components/VersionBadge'

// All page modules are code-split. Logged-in users land on JournalPage (or whatever
// authed route they hit) and never download the auth/legal pages; first-time visitors
// hit LandingPage and only fetch LoginPage when they actually click "sign in".
const LoginPage = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))
const ForgotPasswordPage = lazy(() => import('./pages/ForgotPasswordPage'))
const ResetPasswordPage = lazy(() => import('./pages/ResetPasswordPage'))
const PrivacyPage = lazy(() => import('./pages/PrivacyPage'))
const TermsPage = lazy(() => import('./pages/TermsPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))
const JournalPage = lazy(() => import('./pages/JournalPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const PersonalDashboardPage = lazy(() => import('./pages/PersonalDashboardPage'))
const NoteDetailPage = lazy(() => import('./pages/NoteDetailPage'))
// Counselor & Pricing UI temporarily hidden — backend models/endpoints kept
// because Conversation/Message and achievement counters are coupled to them.
// const CounselorListPage = lazy(() => import('./pages/CounselorListPage'))
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
// const PricingPage = lazy(() => import('./pages/PricingPage'))
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
      <VersionBadge />
      <ErrorBoundary key={location.pathname}>
      <AnimatePresence mode="wait" initial={false}>
        <Routes location={location} key={location.pathname}>
          <Route path="/login" element={<LazyRoute><PageTransition><LoginPage /></PageTransition></LazyRoute>} />
          <Route path="/register" element={<LazyRoute><PageTransition><RegisterPage /></PageTransition></LazyRoute>} />
          <Route path="/forgot-password" element={<LazyRoute><PageTransition><ForgotPasswordPage /></PageTransition></LazyRoute>} />
          <Route path="/reset-password" element={<LazyRoute><PageTransition><ResetPasswordPage /></PageTransition></LazyRoute>} />
          <Route path="/privacy" element={<LazyRoute><PageTransition><PrivacyPage /></PageTransition></LazyRoute>} />
          <Route path="/terms" element={<LazyRoute><PageTransition><TermsPage /></PageTransition></LazyRoute>} />
          {/* Public therapist report (no auth required) */}
          <Route path="/report/:token" element={<LazyRoute><PageTransition><TherapistReportPublicPage /></PageTransition></LazyRoute>} />
          <Route path="/verify-email" element={<LazyRoute><PageTransition><VerifyEmailPage /></PageTransition></LazyRoute>} />
          {/* /pricing route hidden pre-launch — payment provider not yet integrated */}
          <Route path="/pricing" element={<Navigate to="/" replace />} />
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
            {/* /counselors hidden pre-launch — no approved counselors yet. Backend
                conversation/message infrastructure stays so achievements that count
                messages/conversations still work. */}
            <Route path="counselors" element={<Navigate to="/" replace />} />
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
          <Route path="*" element={<LazyRoute><PageTransition><NotFoundPage /></PageTransition></LazyRoute>} />
        </Routes>
      </AnimatePresence>
    </ErrorBoundary>
    </>
  )
}
