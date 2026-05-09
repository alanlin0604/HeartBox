import { useLang } from '../../context/LanguageContext';

export default function DashboardHeader({
  isEditMode,
  onToggleEdit,
  onReset,
  onManageMetrics,
  onSave,
  hasUnsavedChanges,
}) {
  const { t } = useLang();

  return (
    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
      <h1 className="text-2xl font-bold">{t('dashboard.title')}</h1>

      <div className="flex flex-wrap items-center gap-2">
        {hasUnsavedChanges && (
          <button
            onClick={onSave}
            className="px-4 py-2 bg-green-500 hover:bg-green-600 rounded-lg transition-colors text-sm font-medium flex items-center gap-2"
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/>
              <polyline points="17 21 17 13 7 13 7 21"/>
              <polyline points="7 3 7 8 15 8"/>
            </svg>
            {t('dashboard.saveLayout')}
          </button>
        )}

        <button
          onClick={onToggleEdit}
          className={`px-4 py-2 rounded-lg transition-colors text-sm font-medium flex items-center gap-2 ${
            isEditMode
              ? 'bg-orange-500 hover:bg-orange-600'
              : 'bg-white/10 hover:bg-white/20'
          }`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>
            <path d="m15 5 4 4"/>
          </svg>
          {isEditMode ? t('dashboard.exitEditMode') : t('dashboard.editMode')}
        </button>

        <button
          onClick={onManageMetrics}
          className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors text-sm font-medium flex items-center gap-2"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="20" x2="12" y2="10"/>
            <line x1="18" y1="20" x2="18" y2="4"/>
            <line x1="6" y1="20" x2="6" y2="16"/>
          </svg>
          {t('dashboard.manageMetrics')}
        </button>

        <button
          onClick={onReset}
          className="px-4 py-2 bg-white/10 hover:bg-red-500/20 text-red-400 hover:text-red-300 rounded-lg transition-colors text-sm font-medium flex items-center gap-2"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16"/>
          </svg>
          {t('dashboard.resetLayout')}
        </button>
      </div>
    </div>
  );
}
