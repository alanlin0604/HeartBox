import { useState } from 'react';
import { useLang } from '../context/LanguageContext';

export default function HabitCard({ habit, onCheckIn, onEdit, onDelete }) {
  const { t } = useLang();
  const [checking, setChecking] = useState(false);
  const today = new Date().toISOString().split('T')[0];

  // Check if already checked in today
  const isCheckedToday = habit.last_check_in === today;

  const handleCheckIn = async () => {
    if (checking || isCheckedToday) return;
    setChecking(true);
    try {
      await onCheckIn(habit.id);
    } finally {
      setChecking(false);
    }
  };

  return (
    <div className="glass-card p-6 hover:shadow-lg transition-shadow duration-300">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl"
            style={{
              backgroundColor: `${habit.color}20`,
              color: habit.color,
            }}
          >
            {habit.icon || '✓'}
          </div>
          <div>
            <h3 className="font-semibold text-lg text-[var(--text-primary)]">
              {habit.name}
            </h3>
            {habit.category && (
              <span className="text-xs text-[var(--text-secondary)]">
                {habit.category}
              </span>
            )}
          </div>
        </div>

        {/* Actions Menu */}
        <div className="flex space-x-1">
          <button
            onClick={() => onEdit(habit)}
            className="p-2 hover:bg-orange-500/10 rounded-lg transition-colors"
            aria-label={t('common.edit')}
          >
            <svg
              className="w-4 h-4 text-[var(--text-secondary)]"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
              />
            </svg>
          </button>
          <button
            onClick={() => onDelete(habit.id)}
            className="p-2 hover:bg-red-500/10 rounded-lg transition-colors"
            aria-label={t('common.delete')}
          >
            <svg
              className="w-4 h-4 text-red-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Description */}
      {habit.description && (
        <p className="text-sm text-[var(--text-secondary)] mb-4 line-clamp-2">
          {habit.description}
        </p>
      )}

      {/* Stats */}
      <div className="flex items-center justify-between mb-4">
        {/* Streak */}
        <div className="flex items-center space-x-2">
          <span className="text-2xl">🔥</span>
          <div>
            <div className="text-2xl font-bold text-[var(--text-primary)]">
              {habit.streak || 0}
            </div>
            <div className="text-xs text-[var(--text-secondary)]">
              {t('habit.streak')}
            </div>
          </div>
        </div>

        {/* Completion Rate */}
        <div className="text-right">
          <div className="text-2xl font-bold text-orange-400">
            {Math.round(habit.completion_rate || 0)}%
          </div>
          <div className="text-xs text-[var(--text-secondary)]">
            {t('habit.completionRate')}
          </div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="h-2 bg-[var(--card-bg)] rounded-full mb-4 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-orange-500 to-rose-500 rounded-full transition-all duration-1000"
          style={{ width: `${habit.completion_rate || 0}%` }}
        />
      </div>

      {/* Check-in Button */}
      <button
        onClick={handleCheckIn}
        disabled={checking || isCheckedToday}
        className={`
          w-full py-3 rounded-xl font-medium transition-all duration-300
          flex items-center justify-center space-x-2
          ${
            isCheckedToday
              ? 'bg-green-500/20 text-green-400 cursor-default'
              : 'bg-orange-500 hover:bg-orange-600 text-white'
          }
          ${checking ? 'opacity-50 cursor-wait' : ''}
          disabled:opacity-50
        `}
      >
        {isCheckedToday ? (
          <>
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                clipRule="evenodd"
              />
            </svg>
            <span>{t('habit.checked')}</span>
          </>
        ) : (
          <>
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span>{checking ? t('common.loading') : t('habit.checkIn')}</span>
          </>
        )}
      </button>
    </div>
  );
}
