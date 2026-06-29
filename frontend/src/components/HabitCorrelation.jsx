import { useState, useEffect, useCallback } from 'react';
import { useLang } from '../context/LanguageContext';
import { useToast } from '../context/ToastContext';
import { getHabitAnalytics } from '../api/habits';
import LoadingSpinner from './LoadingSpinner';

export default function HabitCorrelation() {
  const { t } = useLang();
  const toast = useToast();
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadAnalytics = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getHabitAnalytics();
      const analytics = res.data?.analytics || [];

      // Sort by absolute mood_difference (largest impact first) so the
      // habit that matters most is at the top.
      const formatted = analytics
        .filter((item) => item.days_completed >= 3)
        .sort((a, b) => Math.abs(b.mood_difference) - Math.abs(a.mood_difference))
        .slice(0, 10)
        .map((item) => ({
          name: item.habit_name,
          completed: Number(item.avg_mood_completed?.toFixed(2)) || 0,
          notCompleted: Number(item.avg_mood_not_completed?.toFixed(2)) || 0,
          difference: Number(item.mood_difference?.toFixed(2)) || 0,
          days: item.days_completed,
        }));

      setData(formatted);
    } catch (error) {
      console.error('Failed to load analytics:', error);
      toast?.error(t('habit.loadError'));
    } finally {
      setLoading(false);
    }
  }, [t, toast]);

  useEffect(() => {
    loadAnalytics();
  }, [loadAnalytics]);

  if (loading) {
    return (
      <div className="glass-card p-8 flex items-center justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="glass-card p-8 text-center">
        <p className="text-[var(--text-secondary)]">{t('habit.noAnalytics')}</p>
      </div>
    );
  }

  // Card-based rendering — the prior BarChart with a single bar per
  // habit looked broken when the user only had one or two habits
  // (axes, legend, tooltip framing 1-2 bars made the empty chart
  // dominate the card). Render one row per habit with the two averages
  // and a diff badge; clearer at small N and still ordered by impact.
  return (
    <div className="glass-card p-6">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-2">
          {t('habit.correlation')}
        </h2>
        <p className="text-sm text-[var(--text-secondary)]">
          {t('habit.correlationDescription')}
        </p>
      </div>

      <div className="space-y-3">
        {data.map((row) => {
          const positive = row.difference > 0
          const diffPrefix = positive ? '+' : ''
          const diffColor = positive ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-500 dark:text-red-400'
          return (
            <div key={row.name} className="rounded-xl border border-[var(--card-border)] p-4 bg-[var(--surface-secondary)]">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="min-w-0">
                  <div className="font-semibold text-[var(--text-primary)] truncate">{row.name}</div>
                  <div className="text-xs text-[var(--text-secondary)] mt-0.5">
                    {t('habit.daysCompleted')}：{row.days}
                  </div>
                </div>
                <div className={`text-sm font-bold whitespace-nowrap ${diffColor}`}>
                  {diffPrefix}{row.difference.toFixed(2)}
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-lg p-3 bg-emerald-500/10 border border-emerald-500/20">
                  <div className="text-xs text-[var(--text-secondary)] mb-1">
                    {t('habit.avgMoodCompleted')}
                  </div>
                  <div className="font-semibold text-emerald-700 dark:text-emerald-400">
                    {row.completed.toFixed(2)}
                  </div>
                </div>
                <div className="rounded-lg p-3 bg-red-500/10 border border-red-500/20">
                  <div className="text-xs text-[var(--text-secondary)] mb-1">
                    {t('habit.avgMoodNotCompleted')}
                  </div>
                  <div className="font-semibold text-red-600 dark:text-red-400">
                    {row.notCompleted.toFixed(2)}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      <div className="mt-6 p-4 bg-orange-500/10 rounded-lg">
        <p className="text-sm text-[var(--text-secondary)]">
          💡 {t('habit.correlationTip')}
        </p>
      </div>
    </div>
  );
}
