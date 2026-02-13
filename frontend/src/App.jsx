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
const ComingSoonPage = lazy(() => import('./pages/ComingSoonPage'))
const CounselorListPage = lazy(() => import('./pages/CounselorListPage'))
const ChatPage = lazy(() => import('./pages/ChatPage'))
const AdminPage = lazy(() => import('./pages/AdminPage'))
const SettingsPage = lazy(() => import('./pages/SettingsPage'))

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
        <Route
          path="/"
          element={
            <PrivateRoute>
              <Layout />
            </PrivateRoute>
          }
        >
          <Route index element={<Suspense fallback={<LoadingSpinner />}><JournalPage /></Suspense>} />
          <Route path="dashboard" element={<Suspense fallback={<LoadingSpinner />}><DashboardPage /></Suspense>} />
          <Route path="notes/:id" element={<Suspense fallback={<LoadingSpinner />}><NoteDetailPage /></Suspense>} />
          <Route path="counselors" element={<Suspense fallback={<LoadingSpinner />}><CounselorListPage /></Suspense>} />
          <Route path="chat/:id" element={<Suspense fallback={<LoadingSpinner />}><ChatPage /></Suspense>} />
          <Route path="settings" element={<Suspense fallback={<LoadingSpinner />}><SettingsPage /></Suspense>} />
          <Route
            path="admin"
            element={
              <AdminRoute>
                <Suspense fallback={<LoadingSpinner />}><AdminPage /></Suspense>
              </AdminRoute>
            }
          />
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </ErrorBoundary>
  )
}
