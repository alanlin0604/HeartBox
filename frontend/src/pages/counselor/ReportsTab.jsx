// HIDDEN PRE-LAUNCH — Sub-tab of CounselorListPage (also hidden). Re-enable
// via TODO.md "諮商師功能反向恢復計畫".
import { LOCALE_MAP } from '../../utils/locales'

export default function ReportsTab({
  t,
  lang,
  user,
  reports,
  reportTitle,
  setReportTitle,
  reportStartDate,
  setReportStartDate,
  reportEndDate,
  setReportEndDate,
  reportGenerating,
  handleGenerateReport,
  handleCopyReportLink,
}) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">{t('report.title')}</h2>
        <p className="text-sm text-slate-400 mt-1">{t('report.description')}</p>
      </div>

      <div className="glass p-4 space-y-2">
        <p className="text-sm font-medium">{t('report.includesTitle')}</p>
        <ul className="text-sm text-slate-400 space-y-1 list-disc list-inside">
          <li>{t('report.includesMoodTrend')}</li>
          <li>{t('report.includesStress')}</li>
          <li>{t('report.includesAssessments')}</li>
          <li>{t('report.includesShareable')}</li>
        </ul>
      </div>

      <form onSubmit={handleGenerateReport} className="glass p-6 space-y-4 max-w-lg">
        <input
          type="text"
          value={reportTitle}
          onChange={(e) => setReportTitle(e.target.value)}
          placeholder={t('report.reportTitle')}
          className="glass-input"
          required
        />
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-sm text-slate-400 block mb-1">{t('report.startDate')}</label>
            <input
              type="date"
              value={reportStartDate}
              onChange={(e) => setReportStartDate(e.target.value)}
              className="glass-input"
              required
            />
          </div>
          <div>
            <label className="text-sm text-slate-400 block mb-1">{t('report.endDate')}</label>
            <input
              type="date"
              value={reportEndDate}
              onChange={(e) => setReportEndDate(e.target.value)}
              className="glass-input"
              required
            />
          </div>
        </div>
        <button type="submit" disabled={reportGenerating} className="btn-primary">
          {reportGenerating ? t('common.loading') : t('report.generate')}
        </button>
      </form>

      {reports.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-lg font-semibold">{t('report.existingReports')}</h3>
          {reports.map((r) => (
            <div key={r.id} className="glass-card p-4 flex justify-between items-center">
              <div>
                <p className="font-medium">{r.title}</p>
                <p className="text-sm text-slate-400">
                  {r.period_start} — {r.period_end}
                </p>
                <p className="text-xs opacity-40">
                  {t('report.expires')}: {new Date(r.expires_at).toLocaleDateString(LOCALE_MAP[lang] || lang, {
                    timeZone: user?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric',
                  })}
                </p>
              </div>
              <button
                onClick={() => handleCopyReportLink(r.token)}
                className="btn-secondary text-xs"
              >
                {t('report.copyLink')}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
