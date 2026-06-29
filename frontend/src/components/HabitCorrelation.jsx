import { useState, useEffect, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
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

      // Sort by mood_difference (descending) and format for recharts
      const formattedData = analytics
        .filter((item) => item.days_completed >= 3) // Only show habits with enough data
        .sort((a, b) => b.mood_difference - a.mood_difference)
        .slice(0, 10) // Top 10
        .map((item) => ({
          name: item.habit_name,
          [t('habit.avgMoodCompleted')]: Number(item.avg_mood_completed?.toFixed(1)) || 0,
          [t('habit.avgMoodNotCompleted')]: Number(item.avg_mood_not_completed?.toFixed(1)) || 0,
          difference: Number(item.mood_difference?.toFixed(1)) || 0,
          days: item.days_completed,
        }));

      setData(formattedData);
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

  // Pass as a render function so React Compiler doesn't see a fresh
  // component being created on every render of HabitCorrelation.
  const renderCustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload || !payload.length) return null;
    return (
      <div className="glass-card p-4 shadow-lg">
        <p className="font-semibold text-[var(--text-primary)] mb-2">{label}</p>
        {payload.map((entry, index) => (
          <div key={index} className="flex items-center space-x-2 text-sm">
            <div className="w-3 h-3 rounded" style={{ backgroundColor: entry.color }} />
            <span className="text-[var(--text-secondary)]">{entry.name}:</span>
            <span className="font-medium text-[var(--text-primary)]">{entry.value}</span>
          </div>
        ))}
        {payload[0]?.payload?.days && (
          <p className="text-xs text-[var(--text-secondary)] mt-2">
            {t('habit.daysCompleted')}: {payload[0].payload.days}
          </p>
        )}
      </div>
    );
  };

  return (
    <div className="glass-card p-6">
      {/* Header */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-2">
          {t('habit.correlation')}
        </h2>
        <p className="text-sm text-[var(--text-secondary)]">
          {t('habit.correlationDescription')}
        </p>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={data}
          margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" opacity={0.3} />
          <XAxis
            dataKey="name"
            angle={-45}
            textAnchor="end"
            height={80}
            tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
          />
          <YAxis
            tick={{ fill: 'var(--text-secondary)', fontSize: 12 }}
            domain={[-1, 1]}
            tickFormatter={(v) => v.toFixed(1)}
            label={{
              value: t('habit.moodScore'),
              angle: -90,
              position: 'insideLeft',
              style: { fill: 'var(--text-secondary)', fontSize: 12 },
            }}
          />
          <Tooltip content={renderCustomTooltip} cursor={{ fill: 'var(--card-bg)', opacity: 0.5 }} />
          <Legend
            wrapperStyle={{ paddingTop: '20px' }}
            iconType="circle"
            formatter={(value) => (
              <span className="text-sm text-[var(--text-secondary)]">{value}</span>
            )}
          />
          <Bar
            dataKey={t('habit.avgMoodCompleted')}
            fill="#10b981"
            radius={[8, 8, 0, 0]}
            maxBarSize={60}
          />
          <Bar
            dataKey={t('habit.avgMoodNotCompleted')}
            fill="#ef4444"
            radius={[8, 8, 0, 0]}
            maxBarSize={60}
          />
        </BarChart>
      </ResponsiveContainer>

      {/* Legend Explanation */}
      <div className="mt-6 p-4 bg-orange-500/10 rounded-lg">
        <p className="text-sm text-[var(--text-secondary)]">
          💡 {t('habit.correlationTip')}
        </p>
      </div>
    </div>
  );
}
