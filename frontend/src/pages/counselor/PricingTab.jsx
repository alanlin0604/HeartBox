export default function PricingTab({
  t,
  editDisplayName,
  setEditDisplayName,
  editSpecialty,
  setEditSpecialty,
  editIntroduction,
  setEditIntroduction,
  pricingRate,
  setPricingRate,
  pricingCurrency,
  setPricingCurrency,
  pricingSaving,
  handleSaveProfile,
}) {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{t('counselor.editProfile')}</h2>
      <p className="text-sm text-slate-400">{t('counselor.editProfileDesc')}</p>
      <form onSubmit={handleSaveProfile} className="glass p-6 space-y-4 max-w-lg">
        <div>
          <label className="text-sm text-slate-400 block mb-1">{t('counselor.displayNameLabel')}</label>
          <input
            type="text"
            value={editDisplayName}
            onChange={(e) => setEditDisplayName(e.target.value)}
            placeholder={t('counselor.displayNamePlaceholder')}
            className="glass-input"
            maxLength={50}
          />
        </div>
        <div>
          <label className="text-sm text-slate-400 block mb-1">{t('counselor.specialtyLabel')}</label>
          <input
            type="text"
            value={editSpecialty}
            onChange={(e) => setEditSpecialty(e.target.value)}
            placeholder={t('counselor.specialtyPlaceholder')}
            className="glass-input"
          />
        </div>
        <div>
          <label className="text-sm text-slate-400 block mb-1">{t('counselor.introPlaceholder')}</label>
          <textarea
            value={editIntroduction}
            onChange={(e) => setEditIntroduction(e.target.value)}
            placeholder={t('counselor.introPlaceholder')}
            className="glass-input min-h-[120px] resize-y"
          />
        </div>
        <div>
          <label className="text-sm text-slate-400 block mb-1">{t('pricing.hourlyRate')}</label>
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
          <label className="text-sm text-slate-400 block mb-1">{t('pricing.currency')}</label>
          <select
            value={pricingCurrency}
            onChange={(e) => setPricingCurrency(e.target.value)}
            className="glass-input"
          >
            <option value="TWD">TWD (NT$)</option>
            <option value="USD">USD ($)</option>
            <option value="JPY">JPY ({'¥'})</option>
          </select>
        </div>
        <button type="submit" disabled={pricingSaving} className="btn-primary">
          {pricingSaving ? t('settings.saving') : t('settings.save')}
        </button>
      </form>
    </div>
  )
}
