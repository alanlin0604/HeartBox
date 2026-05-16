// =============================================================================
// HIDDEN PRE-LAUNCH — Not imported anywhere. /counselors route redirects to /.
// Kept on disk for fast restoration when the counselor feature ships.
// Re-enable steps: see TODO.md section "諮商師功能反向恢復計畫".
// =============================================================================
import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom'
import {
  getCounselors,
  getRecommendedCounselors,
  applyCounselor,
  getMyCounselorProfile,
  updateMyCounselorProfile,
  createConversation,
  getConversations,
  deleteConversation,
  createReview,
} from '../api/counselors'
import { getSharedNotes } from '../api/notes'
import { getSharedAssessments, createTherapistReport, getTherapistReports } from '../api/wellness'
import { getBookings, bookingAction, cancelBooking } from '../api/schedule'
import { useLang } from '../context/LanguageContext'
import SkeletonCard from '../components/SkeletonCard'
import BookingPanel from '../components/BookingPanel'
import ConfirmModal from '../components/ConfirmModal'
import { useToast } from '../context/ToastContext'
import { useAuth } from '../context/AuthContext'
import CounselorDirectoryTab from './counselor/CounselorDirectoryTab'
import ChatsTab from './counselor/ChatsTab'
import BookingsTab from './counselor/BookingsTab'
import ReportsTab from './counselor/ReportsTab'
import ScheduleTab from './counselor/ScheduleTab'
import SharedNotesTab from './counselor/SharedNotesTab'
import AssessmentsTab from './counselor/AssessmentsTab'
import PricingTab from './counselor/PricingTab'
import ApplyTab from './counselor/ApplyTab'

export default function CounselorListPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const { user } = useAuth()
  const { lang, t } = useLang()
  const toast = useToast()
  const [counselors, setCounselors] = useState([])
  const [recommended, setRecommended] = useState([])
  const [conversations, setConversations] = useState([])
  const [myProfile, setMyProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState(() => searchParams.get('tab') || 'list')

  // Booking panel state
  const [bookingTarget, setBookingTarget] = useState(null)

  // Bookings list
  const [bookings, setBookings] = useState([])

  // Shared notes received
  const [sharedNotes, setSharedNotes] = useState([])

  // Shared assessments received
  const [sharedAssessments, setSharedAssessments] = useState([])

  // Apply form state
  const [licenseNumber, setLicenseNumber] = useState('')
  const [specialty, setSpecialty] = useState('')
  const [introduction, setIntroduction] = useState('')
  const [applyLoading, setApplyLoading] = useState(false)
  const [applyError, setApplyError] = useState('')
  const [applySuccess, setApplySuccess] = useState(false)

  // Apply form optional pricing
  const [applyRate, setApplyRate] = useState('')
  const [applyCurrency, setApplyCurrency] = useState('TWD')

  // Delete conversation state
  const [deleteConfirmId, setDeleteConfirmId] = useState(null)
  const [deletingConv, setDeletingConv] = useState(false)

  // Expanded shared note / assessment
  const [expandedNoteId, setExpandedNoteId] = useState(null)
  const [expandedAssessmentId, setExpandedAssessmentId] = useState(null)

  // Reports tab state
  const [reports, setReports] = useState([])
  const [reportTitle, setReportTitle] = useState('')
  const [reportStartDate, setReportStartDate] = useState('')
  const [reportEndDate, setReportEndDate] = useState('')
  const [reportGenerating, setReportGenerating] = useState(false)

  // Review state
  const [reviewingBookingId, setReviewingBookingId] = useState(null)
  const [reviewRating, setReviewRating] = useState(0)
  const [reviewContent, setReviewContent] = useState('')
  const [reviewSubmitting, setReviewSubmitting] = useState(false)

  // Context menu state
  const [contextMenu, setContextMenu] = useState(null) // { x, y, type, id }
  const [failedAvatars, setFailedAvatars] = useState(new Set())

  // Edit profile form state (pricing tab upgrade)
  const [editDisplayName, setEditDisplayName] = useState('')
  const [editSpecialty, setEditSpecialty] = useState('')
  const [editIntroduction, setEditIntroduction] = useState('')
  const [pricingRate, setPricingRate] = useState('')
  const [pricingCurrency, setPricingCurrency] = useState('TWD')
  const [pricingSaving, setPricingSaving] = useState(false)

  useEffect(() => { document.title = `${t('nav.counselors')} — ${t('app.name')}` }, [t])

  // Close context menu on click anywhere
  useEffect(() => {
    const close = () => setContextMenu(null)
    if (contextMenu) {
      window.addEventListener('click', close)
      return () => window.removeEventListener('click', close)
    }
  }, [contextMenu])

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [counselorRes, convRes, bookingRes, recRes, reportsRes] = await Promise.all([
        getCounselors(),
        getConversations(),
        getBookings(),
        getRecommendedCounselors().catch(() => ({ data: [] })),
        getTherapistReports().catch(() => ({ data: [] })),
      ])
      setCounselors(counselorRes.data.results || counselorRes.data)
      setConversations(convRes.data.results || convRes.data)
      setBookings(bookingRes.data.results || bookingRes.data || [])
      setRecommended(recRes.data.results || recRes.data || [])
      setReports(reportsRes.data.results || reportsRes.data || [])

      try {
        const profileRes = await getMyCounselorProfile()
        setMyProfile(profileRes.data)
        setEditDisplayName(profileRes.data.display_name || '')
        setEditSpecialty(profileRes.data.specialty || '')
        setEditIntroduction(profileRes.data.introduction || '')
        setPricingRate(profileRes.data.hourly_rate || '')
        setPricingCurrency(profileRes.data.currency || 'TWD')
        // If counselor, load shared notes and assessments
        const [sharedRes, sharedAssRes] = await Promise.all([
          getSharedNotes(),
          getSharedAssessments(),
        ])
        setSharedNotes(sharedRes.data.results || sharedRes.data)
        setSharedAssessments(sharedAssRes.data.results || sharedAssRes.data)
      } catch {
        // User is not a counselor — that's fine
      }
    } catch {
      toast?.error(t('common.operationFailed'))
      setError(t('counselor.loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [toast, t])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Sync tab state with URL search params.
  useEffect(() => {
    if (location.state?.tab) {
      const tabMap = { bookings: 'bookings', received: 'shared', assessments: 'assessments' }
      const newTab = tabMap[location.state.tab] || location.state.tab
      setTab(newTab)
      setSearchParams({ tab: newTab }, { replace: true })
    }
  }, [location.state, setSearchParams])

  useEffect(() => {
    const current = searchParams.get('tab')
    if (tab !== 'list' && current !== tab) {
      setSearchParams({ tab }, { replace: true })
    } else if (tab === 'list' && current) {
      setSearchParams({}, { replace: true })
    }
  }, [tab, searchParams, setSearchParams])

  const handleApply = async (e) => {
    e.preventDefault()
    setApplyLoading(true)
    setApplyError('')
    try {
      const payload = {
        license_number: licenseNumber,
        specialty,
        introduction,
      }
      if (applyRate) payload.hourly_rate = applyRate
      if (applyRate) payload.currency = applyCurrency
      const res = await applyCounselor(payload)
      setMyProfile(res.data)
      setApplySuccess(true)
    } catch (err) {
      const data = err.response?.data
      if (data) {
        const messages = Object.values(data).flat().join(', ')
        setApplyError(messages || t('counselor.applyFailed'))
      } else {
        setApplyError(t('counselor.applyFailed'))
      }
    } finally {
      setApplyLoading(false)
    }
  }

  const handleStartChat = async (counselorId) => {
    try {
      const res = await createConversation(counselorId)
      navigate(`/chat/${res.data.id}`)
    } catch (err) {
      toast?.error(err.response?.data?.detail || t('counselor.createFailed'))
    }
  }

  const handleBookingAction = async (bookingId, action) => {
    try {
      const res = await bookingAction(bookingId, action)
      setBookings((prev) => prev.map((b) => (b.id === bookingId ? res.data : b)))
      toast?.success(t('booking.actionSuccess'))
    } catch (err) {
      toast?.error(err.response?.data?.detail || t('booking.actionFailed'))
    }
  }

  const handleUserCancel = async (bookingId) => {
    try {
      const res = await cancelBooking(bookingId)
      setBookings((prev) => prev.map((b) => (b.id === bookingId ? res.data : b)))
      toast?.success(t('booking.actionSuccess'))
    } catch (err) {
      toast?.error(err.response?.data?.detail || t('booking.actionFailed'))
    }
  }

  const handleDeleteConversation = async () => {
    if (!deleteConfirmId) return
    setDeletingConv(true)
    try {
      await deleteConversation(deleteConfirmId)
      setConversations((prev) => prev.filter((c) => c.id !== deleteConfirmId))
      toast?.success(t('chat.deleted'))
    } catch {
      toast?.error(t('common.operationFailed'))
    } finally {
      setDeletingConv(false)
      setDeleteConfirmId(null)
    }
  }

  const handleSaveProfile = async (e) => {
    e.preventDefault()
    setPricingSaving(true)
    try {
      const res = await updateMyCounselorProfile({
        display_name: editDisplayName,
        specialty: editSpecialty,
        introduction: editIntroduction,
        hourly_rate: pricingRate || null,
        currency: pricingCurrency,
      })
      setMyProfile(res.data)
      toast?.success(t('counselor.editSuccess'))
    } catch {
      toast?.error(t('settings.saveFailed'))
    } finally {
      setPricingSaving(false)
    }
  }

  const handleGenerateReport = async (e) => {
    e.preventDefault()
    setReportGenerating(true)
    try {
      await createTherapistReport({
        title: reportTitle,
        period_start: reportStartDate,
        period_end: reportEndDate,
      })
      toast?.success(t('report.generateSuccess'))
      setReportTitle('')
      setReportStartDate('')
      setReportEndDate('')
      const res = await getTherapistReports()
      setReports(res.data.results || res.data || [])
    } catch {
      toast?.error(t('report.generateFailed'))
    } finally {
      setReportGenerating(false)
    }
  }

  const handleCopyReportLink = (token) => {
    const url = `${window.location.origin}/report/${token}`
    navigator.clipboard.writeText(url)
    toast?.success(t('report.linkCopied'))
  }

  const handleSubmitReview = async (bookingId) => {
    if (reviewRating < 1) return
    setReviewSubmitting(true)
    try {
      await createReview(bookingId, reviewRating, reviewContent)
      toast?.success(t('review.submitSuccess'))
      setReviewingBookingId(null)
      setReviewRating(0)
      setReviewContent('')
      // Mark booking as reviewed locally
      setBookings((prev) =>
        prev.map((b) => (b.id === bookingId ? { ...b, has_review: true } : b))
      )
    } catch {
      toast?.error(t('review.submitFailed'))
    } finally {
      setReviewSubmitting(false)
    }
  }

  if (loading) return (
    <div className="space-y-4 mt-4">
      {[1, 2, 3].map((i) => <SkeletonCard key={i} lines={3} showAvatar />)}
    </div>
  )

  const STATUS_MAP = {
    pending: t('counselor.statusPending'),
    approved: t('counselor.statusApproved'),
    rejected: t('counselor.statusRejected'),
  }

  const BOOKING_STATUS_MAP = {
    pending: t('booking.statusPending'),
    confirmed: t('booking.statusConfirmed'),
    cancelled: t('booking.statusCancelled'),
    completed: t('booking.statusCompleted'),
  }

  const isCounselor = myProfile?.status === 'approved'

  return (
    <div className="space-y-6 mt-4">
      {error && (
        <div className="glass-card p-4 text-red-500 text-sm border border-red-500/20">
          {error}
        </div>
      )}

      {/* Tab navigation */}
      <div className="glass p-2 flex gap-2 flex-wrap">
        <button
          onClick={() => setTab('list')}
          className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
            tab === 'list' ? 'bg-orange-500/30 text-orange-500' : 'opacity-60 hover:opacity-100'
          }`}
        >
          {t('counselor.listTab')}
        </button>
        <button
          onClick={() => setTab('chats')}
          className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
            tab === 'chats' ? 'bg-orange-500/30 text-orange-500' : 'opacity-60 hover:opacity-100'
          }`}
        >
          {t('counselor.chatsTab')} {conversations.length > 0 && `(${conversations.length})`}
        </button>
        <button
          onClick={() => setTab('bookings')}
          className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
            tab === 'bookings' ? 'bg-orange-500/30 text-orange-500' : 'opacity-60 hover:opacity-100'
          }`}
        >
          {t('booking.myBookings')}
        </button>
        <button
          onClick={() => setTab('reports')}
          className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
            tab === 'reports' ? 'bg-orange-500/30 text-orange-500' : 'opacity-60 hover:opacity-100'
          }`}
        >
          {t('report.tab')}
        </button>
        <button
          onClick={() => setTab('apply')}
          className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
            tab === 'apply' ? 'bg-orange-500/30 text-orange-500' : 'opacity-60 hover:opacity-100'
          }`}
        >
          {t('counselor.applyTab')}
        </button>
        {isCounselor && (
          <button
            onClick={() => setTab('pricing')}
            className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
              tab === 'pricing' ? 'bg-orange-500/30 text-orange-500' : 'opacity-60 hover:opacity-100'
            }`}
          >
            {t('counselor.editProfile')}
          </button>
        )}
        {isCounselor && (
          <button
            onClick={() => setTab('schedule')}
            className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
              tab === 'schedule' ? 'bg-orange-500/30 text-orange-500' : 'opacity-60 hover:opacity-100'
            }`}
          >
            {t('schedule.tab')}
          </button>
        )}
        {isCounselor && (
          <button
            onClick={() => setTab('shared')}
            className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
              tab === 'shared' ? 'bg-orange-500/30 text-orange-500' : 'opacity-60 hover:opacity-100'
            }`}
          >
            {t('share.receivedTab')} {sharedNotes.length > 0 && `(${sharedNotes.length})`}
          </button>
        )}
        {isCounselor && (
          <button
            onClick={() => setTab('assessments')}
            className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
              tab === 'assessments' ? 'bg-orange-500/30 text-orange-500' : 'opacity-60 hover:opacity-100'
            }`}
          >
            {t('share.assessmentsTab')} {sharedAssessments.length > 0 && `(${sharedAssessments.length})`}
          </button>
        )}
      </div>

      {/* Counselor List Tab */}
      {tab === 'list' && (
        <CounselorDirectoryTab
          t={t}
          navigate={navigate}
          counselors={counselors}
          recommended={recommended}
          failedAvatars={failedAvatars}
          setFailedAvatars={setFailedAvatars}
          handleStartChat={handleStartChat}
          setBookingTarget={setBookingTarget}
        />
      )}

      {/* My Conversations Tab */}
      {tab === 'chats' && (
        <ChatsTab
          t={t}
          lang={lang}
          user={user}
          navigate={navigate}
          conversations={conversations}
          setTab={setTab}
          setContextMenu={setContextMenu}
          setDeleteConfirmId={setDeleteConfirmId}
        />
      )}

      {/* My Bookings Tab */}
      {tab === 'bookings' && (
        <BookingsTab
          t={t}
          bookings={bookings}
          isCounselor={isCounselor}
          setTab={setTab}
          setContextMenu={setContextMenu}
          BOOKING_STATUS_MAP={BOOKING_STATUS_MAP}
          handleBookingAction={handleBookingAction}
          handleUserCancel={handleUserCancel}
          reviewingBookingId={reviewingBookingId}
          setReviewingBookingId={setReviewingBookingId}
          reviewRating={reviewRating}
          setReviewRating={setReviewRating}
          reviewContent={reviewContent}
          setReviewContent={setReviewContent}
          reviewSubmitting={reviewSubmitting}
          handleSubmitReview={handleSubmitReview}
        />
      )}

      {/* Reports Tab */}
      {tab === 'reports' && (
        <ReportsTab
          t={t}
          lang={lang}
          user={user}
          reports={reports}
          reportTitle={reportTitle}
          setReportTitle={setReportTitle}
          reportStartDate={reportStartDate}
          setReportStartDate={setReportStartDate}
          reportEndDate={reportEndDate}
          setReportEndDate={setReportEndDate}
          reportGenerating={reportGenerating}
          handleGenerateReport={handleGenerateReport}
          handleCopyReportLink={handleCopyReportLink}
        />
      )}

      {/* Schedule Management Tab (counselors only) */}
      {tab === 'schedule' && isCounselor && (
        <ScheduleTab />
      )}

      {/* Shared Notes Tab (counselors only) */}
      {tab === 'shared' && isCounselor && (
        <SharedNotesTab
          t={t}
          lang={lang}
          user={user}
          sharedNotes={sharedNotes}
          expandedNoteId={expandedNoteId}
          setExpandedNoteId={setExpandedNoteId}
          setTab={setTab}
        />
      )}

      {/* Shared Assessments Tab (counselors only) */}
      {tab === 'assessments' && isCounselor && (
        <AssessmentsTab
          t={t}
          lang={lang}
          user={user}
          sharedAssessments={sharedAssessments}
          expandedAssessmentId={expandedAssessmentId}
          setExpandedAssessmentId={setExpandedAssessmentId}
          setTab={setTab}
        />
      )}

      {/* Edit Profile Tab (counselors only) */}
      {tab === 'pricing' && isCounselor && (
        <PricingTab
          t={t}
          editDisplayName={editDisplayName}
          setEditDisplayName={setEditDisplayName}
          editSpecialty={editSpecialty}
          setEditSpecialty={setEditSpecialty}
          editIntroduction={editIntroduction}
          setEditIntroduction={setEditIntroduction}
          pricingRate={pricingRate}
          setPricingRate={setPricingRate}
          pricingCurrency={pricingCurrency}
          setPricingCurrency={setPricingCurrency}
          pricingSaving={pricingSaving}
          handleSaveProfile={handleSaveProfile}
        />
      )}

      {/* Apply Tab */}
      {tab === 'apply' && (
        <ApplyTab
          t={t}
          myProfile={myProfile}
          applySuccess={applySuccess}
          applyError={applyError}
          applyLoading={applyLoading}
          handleApply={handleApply}
          STATUS_MAP={STATUS_MAP}
          licenseNumber={licenseNumber}
          setLicenseNumber={setLicenseNumber}
          specialty={specialty}
          setSpecialty={setSpecialty}
          introduction={introduction}
          setIntroduction={setIntroduction}
          applyRate={applyRate}
          setApplyRate={setApplyRate}
          applyCurrency={applyCurrency}
          setApplyCurrency={setApplyCurrency}
        />
      )}

      {/* Context Menu */}
      {contextMenu && (
        <div
          className="fixed z-50 glass rounded-xl shadow-xl border border-[var(--card-border)] py-1 min-w-[140px]"
          style={{ left: contextMenu.x, top: contextMenu.y }}
        >
          {contextMenu.type === 'conversation' && (
            <button
              onClick={() => {
                setDeleteConfirmId(contextMenu.id)
                setContextMenu(null)
              }}
              className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
            >
              {t('chat.deleteConversation')}
            </button>
          )}
          {contextMenu.type === 'booking' && (
            <button
              onClick={() => {
                if (isCounselor) {
                  handleBookingAction(contextMenu.id, 'cancel')
                } else {
                  handleUserCancel(contextMenu.id)
                }
                setContextMenu(null)
              }}
              className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
            >
              {t('booking.cancel')}
            </button>
          )}
        </div>
      )}

      <ConfirmModal
        open={!!deleteConfirmId}
        title={t('chat.deleteConversation')}
        message={t('chat.deleteConfirm')}
        confirmText={t('noteDetail.delete')}
        cancelText={t('common.cancel')}
        loading={deletingConv}
        onConfirm={handleDeleteConversation}
        onCancel={() => setDeleteConfirmId(null)}
      />

      {/* Booking Panel Modal */}
      {bookingTarget && (
        <BookingPanel
          counselorId={bookingTarget.id}
          counselorName={bookingTarget.username}
          hourlyRate={bookingTarget.hourly_rate}
          currency={bookingTarget.currency}
          onClose={() => { setBookingTarget(null); loadData() }}
        />
      )}
    </div>
  )
}
