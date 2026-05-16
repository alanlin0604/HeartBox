// HIDDEN PRE-LAUNCH — Sub-tab of CounselorListPage (also hidden). Re-enable
// via TODO.md "諮商師功能反向恢復計畫".
import EmptyState from '../../components/EmptyState'

export default function BookingsTab({
  t,
  bookings,
  isCounselor,
  setTab,
  setContextMenu,
  BOOKING_STATUS_MAP,
  handleBookingAction,
  handleUserCancel,
  reviewingBookingId,
  setReviewingBookingId,
  reviewRating,
  setReviewRating,
  reviewContent,
  setReviewContent,
  reviewSubmitting,
  handleSubmitReview,
}) {
  return (
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
            <div
              key={b.id}
              className="glass-card p-4"
              onContextMenu={(e) => {
                if (b.status === 'pending' || b.status === 'confirmed') {
                  e.preventDefault()
                  setContextMenu({ x: e.clientX, y: e.clientY, type: 'booking', id: b.id, status: b.status })
                }
              }}
            >
              <div className="flex justify-between items-center">
              <div>
                <p className="font-medium">
                  {b.counselor_name} — {b.date}
                </p>
                <p className="text-sm text-slate-400">
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
              <div className="flex gap-2">
                {isCounselor && (b.status === 'pending' || b.status === 'confirmed') && (
                  <>
                    {b.status === 'pending' && (
                      <button
                        onClick={() => handleBookingAction(b.id, 'confirm')}
                        className="btn-primary text-xs"
                      >
                        {t('booking.confirm')}
                      </button>
                    )}
                    <button
                      onClick={() => handleBookingAction(b.id, 'cancel')}
                      className="btn-danger text-xs"
                    >
                      {t('booking.cancel')}
                    </button>
                  </>
                )}
                {!isCounselor && (b.status === 'pending' || b.status === 'confirmed') && (
                  <button
                    onClick={() => handleUserCancel(b.id)}
                    className="btn-danger text-xs"
                  >
                    {t('booking.cancel')}
                  </button>
                )}
                {b.status === 'completed' && !isCounselor && !b.has_review && (
                  <button
                    onClick={() => {
                      setReviewingBookingId(reviewingBookingId === b.id ? null : b.id)
                      setReviewRating(0)
                      setReviewContent('')
                    }}
                    className="btn-secondary text-xs"
                  >
                    {t('review.leaveReview')}
                  </button>
                )}
                {b.status === 'completed' && b.has_review && (
                  <span className="text-xs text-green-500 font-medium">{t('review.alreadyReviewed')}</span>
                )}
              </div>
              </div>
              {reviewingBookingId === b.id && (
                <div className="mt-3 p-3 rounded-xl bg-white/5 border border-white/10 space-y-3">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setReviewRating(star)}
                        className={`text-xl cursor-pointer transition-colors ${star <= reviewRating ? 'text-yellow-400' : 'text-white/20'}`}
                      >
                        ★
                      </button>
                    ))}
                  </div>
                  <textarea
                    value={reviewContent}
                    onChange={(e) => setReviewContent(e.target.value)}
                    placeholder={t('review.contentPlaceholder')}
                    className="glass-input text-sm min-h-[60px] resize-y"
                  />
                  <button
                    onClick={() => handleSubmitReview(b.id)}
                    disabled={reviewSubmitting || reviewRating < 1}
                    className="btn-primary text-xs"
                  >
                    {reviewSubmitting ? t('common.loading') : t('review.submit')}
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
