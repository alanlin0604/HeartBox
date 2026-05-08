import EmptyState from '../../components/EmptyState'
import { formatPrice } from './utils'

export default function CounselorDirectoryTab({
  t,
  navigate,
  counselors,
  recommended,
  failedAvatars,
  setFailedAvatars,
  handleStartChat,
  setBookingTarget,
}) {
  return (
    <div className="space-y-4">
      {/* Recommended counselors */}
      {recommended.length > 0 && (
        <>
          <h2 className="text-xl font-semibold">{t('counselor.recommendedTitle')}</h2>
          <div className="grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {recommended.map((c) => (
              <div key={c.id} className="glass-card p-5 space-y-3 border-purple-500/30">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-3">
                    {c.avatar && !failedAvatars.has(c.id) ? (
                      <img
                        src={c.avatar}
                        alt={c.username}
                        loading="lazy"
                        decoding="async"
                        className="w-10 h-10 rounded-full object-cover border border-purple-500/40"
                        onError={() => setFailedAvatars(prev => new Set(prev).add(c.id))}
                      />
                    ) : (
                      <div className="w-10 h-10 rounded-full bg-purple-500/25 flex items-center justify-center text-sm font-semibold">
                        {String(c.display_name || c.username || '?').slice(0, 1).toUpperCase()}
                      </div>
                    )}
                    <div>
                      <h3 className="text-lg font-semibold">{c.display_name || c.username}</h3>
                      <p className="text-sm text-slate-400">{c.specialty}</p>
                    </div>
                  </div>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-400 border border-purple-500/20">
                    {t('counselor.recommendedBadge')}
                  </span>
                </div>
                <p className="text-sm leading-relaxed opacity-80 whitespace-pre-line">{c.introduction}</p>
                <div className="flex gap-2">
                  <button onClick={() => handleStartChat(c.id)} className="btn-primary text-sm">{t('counselor.startChat')}</button>
                  <button onClick={() => setBookingTarget({ id: c.id, username: c.username, hourly_rate: c.hourly_rate, currency: c.currency })} className="btn-secondary text-sm">{t('booking.book')}</button>
                </div>
              </div>
            ))}
          </div>
        </>
      )}

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
                  {c.avatar && !failedAvatars.has(c.id) ? (
                    <img
                      src={c.avatar}
                      alt={c.username}
                      loading="lazy"
                      decoding="async"
                      className="w-10 h-10 rounded-full object-cover border border-white/20"
                      onError={() => setFailedAvatars(prev => new Set(prev).add(c.id))}
                    />
                  ) : (
                  <div
                    className="w-10 h-10 rounded-full bg-purple-500/25 flex items-center justify-center text-sm font-semibold"
                  >
                    {String(c.display_name || c.username || '?').slice(0, 1).toUpperCase()}
                  </div>
                  )}
                  <div>
                  <h3 className="text-lg font-semibold">{c.display_name || c.username}</h3>
                  <p className="text-sm text-slate-400">{c.specialty}</p>
                  </div>
                </div>
              </div>
              <p className="text-sm leading-relaxed opacity-80 whitespace-pre-line">{c.introduction}</p>
              <div className="flex items-center gap-3">
                <div className="text-sm font-medium">
                  {c.hourly_rate ? (
                    <span className="text-purple-500">
                      {formatPrice(c.hourly_rate, c.currency)} / {t('pricing.perHour')}
                    </span>
                  ) : (
                    <span className="opacity-50">{t('pricing.notSet')}</span>
                  )}
                </div>
                {c.review_count > 0 && (
                  <span className="text-sm text-yellow-400 font-medium">
                    ★ {c.avg_rating?.toFixed(1)} ({c.review_count})
                  </span>
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
  )
}
