import EmptyState from '../../components/EmptyState'
import { LOCALE_MAP } from '../../utils/locales'

export default function AssessmentsTab({
  t,
  lang,
  user,
  sharedAssessments,
  expandedAssessmentId,
  setExpandedAssessmentId,
  setTab,
}) {
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">{t('share.assessmentsTitle')}</h2>
      {sharedAssessments.length === 0 ? (
        <EmptyState
          title={t('share.noAssessments')}
          description={t('share.noAssessmentsDesc')}
          actionText={t('schedule.tab')}
          onAction={() => setTab('schedule')}
        />
      ) : (
        <div className="space-y-3">
          {sharedAssessments.map((sa) => {
            const isExpanded = expandedAssessmentId === sa.id
            return (
              <div
                key={sa.id}
                className="glass-card p-4 space-y-2 cursor-pointer hover:border-orange-500/30 transition-all"
                onClick={() => setExpandedAssessmentId(isExpanded ? null : sa.id)}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">{sa.username}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-xs opacity-40">
                      {new Date(sa.shared_at).toLocaleDateString(LOCALE_MAP[lang] || lang, {
                        timeZone: user?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </span>
                    <span className="text-xs opacity-40">{isExpanded ? '▲' : '▼'}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs px-2 py-1 rounded-full bg-orange-500/15 text-orange-400 border border-orange-500/20 font-medium">
                    {(sa.assessment_type || '').toUpperCase()}
                  </span>
                  <span className="text-lg font-bold">{sa.total_score}</span>
                </div>
                {isExpanded && sa.responses ? (
                  <div className="space-y-2 mt-2">
                    {sa.responses.map((r, i) => (
                      <div key={i} className="flex items-start gap-2 text-sm">
                        <span className={`shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                          r === 0 ? 'bg-green-500/20 text-green-400' :
                          r === 1 ? 'bg-yellow-500/20 text-yellow-400' :
                          r === 2 ? 'bg-orange-500/20 text-orange-400' :
                          'bg-red-500/20 text-red-400'
                        }`}>
                          {r}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="opacity-80">{t(`assessment.${sa.assessment_type}_q${i + 1}`)}</p>
                          <p className={`text-xs mt-0.5 ${
                            r === 0 ? 'text-green-400' :
                            r === 1 ? 'text-yellow-400' :
                            r === 2 ? 'text-orange-400' :
                            'text-red-400'
                          }`}>
                            {t(`assessment.option${r}`)}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : sa.responses ? (
                  <div className="flex flex-wrap gap-1.5">
                    {sa.responses.map((r, i) => (
                      <span key={i} className={`text-xs w-6 h-6 rounded-full flex items-center justify-center font-medium ${
                        r === 0 ? 'bg-green-500/20 text-green-400' :
                        r === 1 ? 'bg-yellow-500/20 text-yellow-400' :
                        r === 2 ? 'bg-orange-500/20 text-orange-400' :
                        'bg-red-500/20 text-red-400'
                      }`}>
                        {r}
                      </span>
                    ))}
                  </div>
                ) : null}
                <p className="text-xs opacity-50">
                  {t('share.assessmentDate')}: {new Date(sa.assessment_date).toLocaleDateString(LOCALE_MAP[lang] || lang)}
                </p>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
