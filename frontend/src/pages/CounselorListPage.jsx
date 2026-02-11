import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  getCounselors,
  applyCounselor,
  getMyCounselorProfile,
  createConversation,
  getConversations,
} from '../api/counselors'
import { getSharedNotes } from '../api/notes'
import { getBookings, bookingAction } from '../api/schedule'
import { useLang } from '../context/LanguageContext'
import LoadingSpinner from '../components/LoadingSpinner'
import BookingPanel from '../components/BookingPanel'
import ScheduleManager from '../components/ScheduleManager'
import EmptyState from '../components/EmptyState'
import { useToast } from '../context/ToastContext'

const LOCALE_MAP = { 'zh-TW': 'zh-TW', en: 'en-US', ja: 'ja-JP' }
const TZ_MAP = { 'zh-TW': 'Asia/Taipei', en: 'UTC', ja: 'Asia/Tokyo' }

export default function CounselorListPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { lang, t } = useLang()
  const toast = useToast()
  const [counselors, setCounselors] = useState([])
  const [conversations, setConversations] = useState([])
  const [myProfile, setMyProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('list')

  // Booking panel state
  const [bookingTarget, setBookingTarget] = useState(null)

  // Bookings list
  const [bookings, setBookings] = useState([])

  // Shared notes received
  const [sharedNotes, setSharedNotes] = useState([])

  // Apply form state
  const [licenseNumber, setLicenseNumber] = useState('')
  const [specialty, setSpecialty] = useState('')
  const [introduction, setIntroduction] = useState('')
  const [applyLoading, setApplyLoading] = useState(false)
  const [applyError, setApplyError] = useState('')
  const [applySuccess, setApplySuccess] = useState(false)

  useEffect(() => {
    loadData()
  }, [])

  // Accept tab from notification navigation
  useEffect(() => {
    if (location.state?.tab) {
      const tabMap = { bookings: 'bookings', received: 'shared' }
      setTab(tabMap[location.state.tab] || location.state.tab)
    }
  }, [location.state])

  const loadData = async () => {
    setLoading(true)
    setError('')
    try {
      const [counselorRes, convRes, bookingRes] = await Promise.all([
        getCounselors(),
        getConversations(),
        getBookings(),
      ])
      setCounselors(counselorRes.data.results || counselorRes.data)
      setConversations(convRes.data.results || convRes.data)
      setBookings(bookingRes.data)

      try {
        const profileRes = await getMyCounselorProfile()
        setMyProfile(profileRes.data)
        // If counselor, load shared notes
        const sharedRes = await getSharedNotes()
        setSharedNotes(sharedRes.data.results || sharedRes.data)
      } catch {
        // User is not a counselor — that's fine
      }
    } catch (err) {
      console.error('Failed to load data', err)
      setError(t('counselor.loadFailed'))
    } finally {
      setLoading(false)
    }
  }

  const handleApply = async (e) => {
    e.preventDefault()
    setApplyLoading(true)
    setApplyError('')
    try {
      const res = await applyCounselor({
        license_number: licenseNumber,
        specialty,
        introduction,
      })
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
      toast?.error(err.response?.data?.error || t('counselor.createFailed'))
    }
  }

  const handleBookingAction = async (bookingId, action) => {
    try {
      const res = await bookingAction(bookingId, action)
      setBookings((prev) => prev.map((b) => (b.id === bookingId ? res.data : b)))
      toast?.success(t('booking.actionSuccess'))
    } catch (err) {
      toast?.error(err.response?.data?.error || t('booking.actionFailed'))
    }
  }

  if (loading) return <LoadingSpinner />

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
            tab === 'list' ? 'bg-purple-500/30 text-purple-500' : 'opacity-60 hover:opacity-100'
          }`}
        >
          {t('counselor.listTab')}
        </button>
        <button
          onClick={() => setTab('chats')}
          className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
            tab === 'chats' ? 'bg-purple-500/30 text-purple-500' : 'opacity-60 hover:opacity-100'
          }`}
        >
          {t('counselor.chatsTab')} {conversations.length > 0 && `(${conversations.length})`}
        </button>
        <button
          onClick={() => setTab('bookings')}
          className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
            tab === 'bookings' ? 'bg-purple-500/30 text-purple-500' : 'opacity-60 hover:opacity-100'
          }`}
        >
          {t('booking.myBookings')}
        </button>
        {isCounselor && (
          <button
            onClick={() => setTab('schedule')}
            className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
              tab === 'schedule' ? 'bg-purple-500/30 text-purple-500' : 'opacity-60 hover:opacity-100'
            }`}
          >
            {t('schedule.tab')}
          </button>
        )}
        {isCounselor && (
          <button
            onClick={() => setTab('shared')}
            className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
              tab === 'shared' ? 'bg-purple-500/30 text-purple-500' : 'opacity-60 hover:opacity-100'
            }`}
          >
            {t('share.receivedTab')} {sharedNotes.length > 0 && `(${sharedNotes.length})`}
          </button>
        )}
        <button
          onClick={() => setTab('apply')}
          className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
            tab === 'apply' ? 'bg-purple-500/30 text-purple-500' : 'opacity-60 hover:opacity-100'
          }`}
        >
          {t('counselor.applyTab')}
        </button>
      </div>

      {/* Counselor List Tab */}
      {tab === 'list' && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">{t('counselor.approvedList')}</h2>
          {counselors.length === 0 ? (
            <EmptyState
              title={t('counselor.noApproved')}
              description={t('counselor.noApprovedDesc')}
              actionText={t('journal.writeFirst')}
              onAction={() => navigate('/')}
            />
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {counselors.map((c) => (
                <div key={c.id} className="glass-card p-5 space-y-3">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-3">
                      {c.avatar ? (
                        <img src={c.avatar} alt={c.username} className="w-10 h-10 rounded-full object-cover border border-white/20" />
                      ) : (
                        <div className="w-10 h-10 rounded-full bg-purple-500/25 flex items-center justify-center text-sm font-semibold">
                          {String(c.username || '?').slice(0, 1).toUpperCase()}
                        </div>
                      )}
                      <div>
                      <h3 className="text-lg font-semibold">{c.username}</h3>
                      <p className="text-sm opacity-60">{c.specialty}</p>
                      </div>
                    </div>
                  </div>
                  <p className="text-sm leading-relaxed opacity-80">{c.introduction}</p>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleStartChat(c.id)}
                      className="btn-primary text-sm"
                    >
                      {t('counselor.startChat')}
                    </button>
                    <button
                      onClick={() => setBookingTarget({ id: c.id, username: c.username })}
                      className="btn-secondary text-sm"
                    >
                      {t('booking.book')}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* My Conversations Tab */}
      {tab === 'chats' && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">{t('counselor.myChats')}</h2>
          {conversations.length === 0 ? (
            <EmptyState
              title={t('counselor.noChats')}
              description={t('counselor.noChatsDesc')}
              actionText={t('counselor.listTab')}
              onAction={() => setTab('list')}
            />
          ) : (
            <div className="space-y-3">
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  onClick={() => navigate(`/chat/${conv.id}`)}
                  className="glass-card p-4 cursor-pointer hover:border-purple-500/30 transition-all flex justify-between items-center"
                >
                  <div>
                    <h3 className="font-semibold">{conv.other_user.username}</h3>
                    {conv.last_message && (
                      <p className="text-sm opacity-60 mt-1">
                        {conv.last_message.sender_name}：{conv.last_message.content}
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    {conv.unread_count > 0 && (
                      <span className="inline-block bg-purple-500 text-white text-xs font-bold px-2 py-1 rounded-full">
                        {conv.unread_count}
                      </span>
                    )}
                    <p className="text-xs opacity-40 mt-1">
                      {new Date(conv.updated_at).toLocaleDateString(LOCALE_MAP[lang] || lang, {
                        timeZone: TZ_MAP[lang] || 'Asia/Taipei',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* My Bookings Tab */}
      {tab === 'bookings' && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">{t('booking.myBookings')}</h2>
          {bookings.length === 0 ? (
            <EmptyState
              title={t('booking.noBookings')}
              description={t('booking.noBookingsDesc')}
              actionText={t('counselor.listTab')}
              onAction={() => setTab('list')}
            />
          ) : (
            <div className="space-y-3">
              {bookings.map((b) => (
                <div key={b.id} className="glass-card p-4 flex justify-between items-center">
                  <div>
                    <p className="font-medium">
                      {b.counselor_name} — {b.date}
                    </p>
                    <p className="text-sm opacity-60">
                      {b.start_time?.slice(0, 5)} - {b.end_time?.slice(0, 5)}
                    </p>
                    <span className={`text-xs font-medium ${
                      b.status === 'confirmed' ? 'text-green-500' :
                      b.status === 'cancelled' ? 'text-red-500' :
                      b.status === 'completed' ? 'text-blue-500' :
                      'text-yellow-500'
                    }`}>
                      {BOOKING_STATUS_MAP[b.status] || b.status}
                    </span>
                  </div>
                  {isCounselor && b.status === 'pending' && (
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleBookingAction(b.id, 'confirm')}
                        className="btn-primary text-xs"
                      >
                        {t('booking.confirm')}
                      </button>
                      <button
                        onClick={() => handleBookingAction(b.id, 'cancel')}
                        className="btn-danger text-xs"
                      >
                        {t('booking.cancel')}
                      </button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Schedule Management Tab (counselors only) */}
      {tab === 'schedule' && isCounselor && (
        <ScheduleManager />
      )}

      {/* Shared Notes Tab (counselors only) */}
      {tab === 'shared' && isCounselor && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">{t('share.receivedTitle')}</h2>
          {sharedNotes.length === 0 ? (
            <EmptyState
              title={t('share.noShared')}
              description={t('share.noSharedDesc')}
              actionText={t('schedule.tab')}
              onAction={() => setTab('schedule')}
            />
          ) : (
            <div className="space-y-3">
              {sharedNotes.map((sn) => (
                <div key={sn.id} className="glass-card p-4 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">
                      {sn.author || t('share.anonymousUser')}
                    </span>
                    <span className="text-xs opacity-40">
                      {new Date(sn.shared_at).toLocaleDateString(LOCALE_MAP[lang] || lang, {
                        timeZone: TZ_MAP[lang] || 'Asia/Taipei',
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </span>
                  </div>
                  <p className="text-sm opacity-80">{sn.note_preview}</p>
                  <div className="flex items-center gap-3 text-xs opacity-60">
                    {sn.sentiment_score != null && (
                      <span>{t('dashboard.avgSentiment')}: {sn.sentiment_score?.toFixed(2)}</span>
                    )}
                    {sn.stress_index != null && (
                      <span>{t('noteCard.stress')}: {sn.stress_index}/10</span>
                    )}
                    {sn.is_anonymous && (
                      <span className="text-purple-500">{t('share.anonymousLabel')}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Apply Tab */}
      {tab === 'apply' && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">{t('counselor.applyTitle')}</h2>

          {myProfile ? (
            <div className="glass-card p-6 space-y-3">
              <p className="text-lg font-semibold">{t('counselor.yourStatus')}</p>
              <div className="space-y-2">
                <p>
                  <span className="opacity-60">{t('counselor.licenseNumber')}</span>
                  {myProfile.license_number}
                </p>
                <p>
                  <span className="opacity-60">{t('counselor.specialtyLabel')}</span>
                  {myProfile.specialty}
                </p>
                <p>
                  <span className="opacity-60">{t('counselor.statusLabel')}</span>
                  <span
                    className={`font-semibold ${
                      myProfile.status === 'approved'
                        ? 'text-green-500'
                        : myProfile.status === 'rejected'
                          ? 'text-red-500'
                          : 'text-yellow-500'
                    }`}
                  >
                    {STATUS_MAP[myProfile.status]}
                  </span>
                </p>
              </div>
              {myProfile.status === 'rejected' && (
                <p className="text-sm opacity-60">
                  {t('counselor.rejectedMsg')}
                </p>
              )}
              {myProfile.status === 'pending' && (
                <p className="text-sm opacity-60">
                  {t('counselor.pendingMsg')}
                </p>
              )}
            </div>
          ) : applySuccess ? (
            <div className="glass-card p-6 text-center space-y-2">
              <p className="text-lg font-semibold text-green-500">{t('counselor.applySuccess')}</p>
              <p className="opacity-60">{t('counselor.applySuccessMsg')}</p>
            </div>
          ) : (
            <form onSubmit={handleApply} className="glass p-6 space-y-4">
              <p className="text-sm opacity-60">
                {t('counselor.applyDescription')}
              </p>
              {applyError && (
                <p className="text-red-500 text-sm">{applyError}</p>
              )}
              <input
                type="text"
                value={licenseNumber}
                onChange={(e) => setLicenseNumber(e.target.value)}
                placeholder={t('counselor.licensePlaceholder')}
                className="glass-input"
                required
              />
              <input
                type="text"
                value={specialty}
                onChange={(e) => setSpecialty(e.target.value)}
                placeholder={t('counselor.specialtyPlaceholder')}
                className="glass-input"
                required
              />
              <textarea
                value={introduction}
                onChange={(e) => setIntroduction(e.target.value)}
                placeholder={t('counselor.introPlaceholder')}
                className="glass-input min-h-[120px] resize-y"
                required
              />
              <button type="submit" disabled={applyLoading} className="btn-primary">
                {applyLoading ? t('counselor.submitting') : t('counselor.submitApply')}
              </button>
            </form>
          )}
        </div>
      )}

      {/* Booking Panel Modal */}
      {bookingTarget && (
        <BookingPanel
          counselorId={bookingTarget.id}
          counselorName={bookingTarget.username}
          onClose={() => { setBookingTarget(null); loadData() }}
        />
      )}
    </div>
  )
}
