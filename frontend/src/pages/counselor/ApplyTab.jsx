export default function ApplyTab({
  t,
  myProfile,
  applySuccess,
  applyError,
  applyLoading,
  handleApply,
  STATUS_MAP,
  licenseNumber,
  setLicenseNumber,
  specialty,
  setSpecialty,
  introduction,
  setIntroduction,
  applyRate,
  setApplyRate,
  applyCurrency,
  setApplyCurrency,
}) {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{t('counselor.applyTitle')}</h2>

      {myProfile ? (
        <div className="glass-card p-6 space-y-3">
          <p className="text-lg font-semibold">{t('counselor.yourStatus')}</p>
          <div className="space-y-2">
            <p>
              <span className="text-slate-400">{t('counselor.licenseNumber')}</span>
              {myProfile.license_number}
            </p>
            <p>
              <span className="text-slate-400">{t('counselor.specialtyLabel')}</span>
              {myProfile.specialty}
            </p>
            <p>
              <span className="text-slate-400">{t('counselor.statusLabel')}</span>
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
            <p className="text-sm text-slate-400">
              {t('counselor.rejectedMsg')}
            </p>
          )}
          {myProfile.status === 'pending' && (
            <p className="text-sm text-slate-400">
              {t('counselor.pendingMsg')}
            </p>
          )}
        </div>
      ) : applySuccess ? (
        <div className="glass-card p-6 text-center space-y-2">
          <p className="text-lg font-semibold text-green-500">{t('counselor.applySuccess')}</p>
          <p className="text-slate-400">{t('counselor.applySuccessMsg')}</p>
        </div>
      ) : (
        <form onSubmit={handleApply} className="glass p-6 space-y-4">
          <p className="text-sm text-slate-400">
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
              <label className="text-sm text-slate-400 block mb-1">{t('pricing.hourlyRate')} ({t('pricing.optional')})</label>
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
              <label className="text-sm text-slate-400 block mb-1">{t('pricing.currency')}</label>
              <select
                value={applyCurrency}
                onChange={(e) => setApplyCurrency(e.target.value)}
                className="glass-input"
              >
                <option value="TWD">TWD (NT$)</option>
                <option value="USD">USD ($)</option>
                <option value="JPY">JPY ({'¥'})</option>
              </select>
            </div>
          </div>
          <button type="submit" disabled={applyLoading} className="btn-primary">
            {applyLoading ? t('counselor.submitting') : t('counselor.submitApply')}
          </button>
        </form>
      )}
    </div>
  )
}
