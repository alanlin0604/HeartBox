import { useEffect, useState } from 'react'
import { useNavigate, useLocation, useSearchParams } from 'react-router-dom'
import {
  getCounselors,
  applyCounselor,
  getMyCounselorProfile,
  updateMyCounselorProfile,
  createConversation,
  getConversations,
} from '../api/counselors'
import { getSharedNotes } from '../api/notes'
import { getBookings, bookingAction } from '../api/schedule'
import { useLang } from '../context/LanguageContext'
import SkeletonCard from '../components/SkeletonCard'
import BookingPanel from '../components/BookingPanel'
import ScheduleManager from '../components/ScheduleManager'
import EmptyState from '../components/EmptyState'
import { useToast } from '../context/ToastContext'
import { LOCALE_MAP, TZ_MAP } from '../utils/locales'

function formatPrice(amount, currency = 'TWD') {
  const num = Number(amount)
  if (isNaN(num)) return ''
  const symbols = { TWD: 'NT$', USD: '$', JPY: '\u00A5' }
  const prefix = symbols[currency] || currency + ' '
  return `${prefix} ${num.toLocaleString()}`
}

export default function CounselorListPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams, setSearchParams] = useSearchParams()
  const { lang, t } = useLang()
  const toast = useToast()
  const [counselors, setCounselors] = useState([])
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

  // Edit profile form state (pricing tab upgrade)
  const [editSpecialty, setEditSpecialty] = useState('')
  const [editIntroduction, setEditIntroduction] = useState('')
  const [pricingRate, setPricingRate] = useState('')
  const [pricingCurrency, setPricingCurrency] = useState('TWD')
  const [pricingSaving, setPricingSaving] = useState(false)

  useEffect(() => { document.title = `${t('nav.counselors')} — ${t('app.name')}` }, [t])

  useEffect(() => {
    loadData()
  }, [])

  // Sync tab state with URL search params
  useEffect(() => {
    if (location.state?.tab) {
      const tabMap = { bookings: 'bookings', received: 'shared' }
      const newTab = tabMap[location.state.tab] || location.state.tab
      setTab(newTab)
      setSearchParams({ tab: newTab }, { replace: true })
    }
  }, [location.state])

  // Update URL when tab changes
  useEffect(() => {
    const current = searchParams.get('tab')
    if (tab !== 'list' && current !== tab) {
      setSearchParams({ tab }, { replace: true })
    } else if (tab === 'list' && current) {
      setSearchParams({}, { replace: true })
    }
  }, [tab])

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
        setEditSpecialty(profileRes.data.specialty || '')
        setEditIntroduction(profileRes.data.introduction || '')
        setPricingRate(profileRes.data.hourly_rate || '')
        setPricingCurrency(profileRes.data.currency || 'TWD')
        // If counselor, load shared notes
        const sharedRes = await getSharedNotes()
        setSharedNotes(sharedRes.data.results || sharedRes.data)
      } catch {
        // User is not a counselor — that's fine
      }
    } catch (err) {
      toast?.error(t('common.operationFailed'))
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

  const handleSaveProfile = async (e) => {
    e.preventDefault()
    setPricingSaving(true)
    try {
      const res = await updateMyCounselorProfile({
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
        <button
          onClick={() => setTab('apply')}
          className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
            tab === 'apply' ? 'bg-purple-500/30 text-purple-500' : 'opacity-60 hover:opacity-100'
          }`}
        >
          {t('counselor.applyTab')}
        </button>
        {isCounselor && (
          <button
            onClick={() => setTab('pricing')}
            className={`px-4 py-2 rounded-xl font-medium transition-all cursor-pointer ${
              tab === 'pricing' ? 'bg-purple-500/30 text-purple-500' : 'opacity-60 hover:opacity-100'
            }`}
          >
            {t('counselor.editProfile')}
          </button>
        )}
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
            <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
              {counselors.map((c) => (
                <div key={c.id} className="glass-card p-5 space-y-3">
                  <div className="flex justify-between items-start">
                    <div className="flex items-center gap-3">
                      {c.avatar ? (
                        <img
                          src={c.avatar}
                          alt={c.username}
                          loading="lazy"
                          decoding="async"
                          className="w-10 h-10 rounded-full object-cover border border-white/20"
                          onError={(e) => {
                            e.target.style.display = 'none'
                            e.target.nextElementSibling.style.display = 'flex'
                          }}
                        />
                      ) : null}
                      <div
                        className="w-10 h-10 rounded-full bg-purple-500/25 items-center justify-center text-sm font-semibold"
                        style={{ display: c.avatar ? 'none' : 'flex' }}
                      >
                        {String(c.username || '?').slice(0, 1).toUpperCase()}
                      </div>
                      <div>
                      <h3 className="text-lg font-semibold">{c.username}</h3>
                      <p className="text-sm opacity-60">{c.specialty}</p>
                      </div>
                    </div>
                  </div>
                  <p className="text-sm leading-relaxed opacity-80 whitespace-pre-line">{c.introduction}</p>
                  <div className="text-sm font-medium">
                    {c.hourly_rate ? (
                      <span className="text-purple-500">
                        {formatPrice(c.hourly_rate, c.currency)} / {t('pricing.perHour')}
                      </span>
                    ) : (
                      <span className="opacity-50">{t('pricing.notSet')}</span>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleStartChat(c.id)}
                      className="btn-primary text-sm"
                    >
                      {t('counselor.startChat')}
                    </button>
                    <button
                      onClick={() => setBookingTarget({ id: c.id, username: c.username, hourly_rate: c.hourly_rate, currency: c.currency })}
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
                        {conv.last_message.sender_name}: {conv.last_message.content}
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

      {/* Edit Profile Tab (counselors only) */}
      {tab === 'pricing' && isCounselor && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">{t('counselor.editProfile')}</h2>
          <p className="text-sm opacity-60">{t('counselor.editProfileDesc')}</p>
          <form onSubmit={handleSaveProfile} className="glass p-6 space-y-4 max-w-lg">
            <div>
              <label className="text-sm opacity-60 block mb-1">{t('counselor.specialtyLabel')}</label>
              <input
                type="text"
                value={editSpecialty}
                onChange={(e) => setEditSpecialty(e.target.value)}
                placeholder={t('counselor.specialtyPlaceholder')}
                className="glass-input"
              />
            </div>
            <div>
              <label className="text-sm opacity-60 block mb-1">{t('counselor.introPlaceholder')}</label>
              <textarea
                value={editIntroduction}
                onChange={(e) => setEditIntroduction(e.target.value)}
                placeholder={t('counselor.introPlaceholder')}
                className="glass-input min-h-[120px] resize-y"
              />
            </div>
            <div>
              <label className="text-sm opacity-60 block mb-1">{t('pricing.hourlyRate')}</label>
              <input
                type="number"
                min="0"
                step="0.01"
                value={pricingRate}
                onChange={(e) => setPricingRate(e.target.value)}
                placeholder="1500"
                className="glass-input"
              />
            </div>
            <div>
              <label className="text-sm opacity-60 block mb-1">{t('pricing.currency')}</label>
              <select
                value={pricingCurrency}
                onChange={(e) => setPricingCurrency(e.target.value)}
                className="glass-input"
              >
                <option value="TWD">TWD (NT$)</option>
                <option value="USD">USD ($)</option>
                <option value="JPY">JPY ({'\u00A5'})</option>
              </select>
            </div>
            <button type="submit" disabled={pricingSaving} className="btn-primary">
              {pricingSaving ? t('settings.saving') : t('settings.save')}
            </button>
          </form>
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
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-sm opacity-60 block mb-1">{t('pricing.hourlyRate')} ({t('pricing.optional')})</label>
                  <input
                    type="number"
                    min="0"
                    step="0.01"
                    value={applyRate}
                    onChange={(e) => setApplyRate(e.target.value)}
                    placeholder="1500"
                    className="glass-input"
                  />
                </div>
                <div>
                  <label className="text-sm opacity-60 block mb-1">{t('pricing.currency')}</label>
                  <select
                    value={applyCurrency}
                    onChange={(e) => setApplyCurrency(e.target.value)}
                    className="glass-input"
                  >
                    <option value="TWD">TWD (NT$)</option>
                    <option value="USD">USD ($)</option>
                    <option value="JPY">JPY ({'\u00A5'})</option>
                  </select>
                </div>
              </div>
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
          hourlyRate={bookingTarget.hourly_rate}
          currency={bookingTarget.currency}
          onClose={() => { setBookingTarget(null); loadData() }}
        />
      )}
    </div>
  )
}
