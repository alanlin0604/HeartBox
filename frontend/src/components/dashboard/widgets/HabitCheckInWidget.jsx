import { useState, useEffect } from 'react';
import { useLang } from '../../../context/LanguageContext';
import { getWidgetData } from '../../../api/dashboard';
import { checkInHabit } from '../../../api/habits';

export default function HabitCheckInWidget({ widgetId, isEditMode, onSettings }) {
  const { t } = useLang();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [checking, setChecking] = useState({});

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getWidgetData(widgetId);
      setData(res.data);
    } catch (err) {
      console.error('Failed to load habit check-in data:', err);
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCheckIn = async (habitId) => {
    if (checking[habitId]) return;

    try {
      setChecking(prev => ({ ...prev, [habitId]: true }));
      await checkInHabit(habitId);
      // Reload data to get updated streak
      await loadData();
    } catch (err) {
      console.error('Failed to check in habit:', err);
      window.dispatchEvent(new CustomEvent('api-error', {
        detail: { messageKey: 'dashboard.habitCheckInFailed' },
      }));
    } finally {
      setChecking(prev => ({ ...prev, [habitId]: false }));
    }
  };

  if (loading) {
    return (
      <div className="glass p-4 rounded-xl h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-green-400 border-t-transparent"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass p-4 rounded-xl h-full flex flex-col">
        <header className="flex justify-between items-center mb-3">
          <h3 className="font-semibold text-green-400">{t('dashboard.widget.habitCheckin.title')}</h3>
          <button
            className="w-8 h-8 flex items-center justify-center hover:bg-white/10 rounded transition-colors"
            onClick={onSettings}
            aria-label={t('dashboard.settings')}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </button>
        </header>
        <div className="flex-1 flex items-center justify-center">
          <p className="text-sm text-red-400">{t('dashboard.loadError')}</p>
        </div>
      </div>
    );
  }

  if (!data || !data.habits || data.habits.length === 0) {
    return (
      <div className="glass p-4 rounded-xl h-full flex flex-col">
        <header className="flex justify-between items-center mb-3">
          <h3 className="font-semibold text-green-400">{t('dashboard.widget.habitCheckin.title')}</h3>
          <button
            className="w-8 h-8 flex items-center justify-center hover:bg-white/10 rounded transition-colors"
            onClick={onSettings}
            aria-label={t('dashboard.settings')}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
          </button>
        </header>
        <div className="flex-1 flex flex-col items-center justify-center text-center p-4">
          <p className="text-sm text-slate-400">{t('dashboard.noData')}</p>
        </div>
      </div>
    );
  }

  const allChecked = data.habits.every(h => h.checked_today);

  return (
    <div className="glass p-4 rounded-xl h-full flex flex-col relative">
      {isEditMode && (
        <div className="absolute top-2 right-2 cursor-move p-1 bg-white/10 rounded drag-handle">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="9" cy="5" r="1.5"/>
            <circle cx="15" cy="5" r="1.5"/>
            <circle cx="9" cy="12" r="1.5"/>
            <circle cx="15" cy="12" r="1.5"/>
            <circle cx="9" cy="19" r="1.5"/>
            <circle cx="15" cy="19" r="1.5"/>
          </svg>
        </div>
      )}
      <header className="flex justify-between items-center mb-3">
        <h3 className="font-semibold text-green-400">{t('dashboard.widget.habitCheckin.title')}</h3>
        <button
          className="w-8 h-8 flex items-center justify-center hover:bg-white/10 rounded transition-colors"
          onClick={onSettings}
          aria-label={t('dashboard.settings')}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
        </button>
      </header>
      <main className="flex-1 overflow-auto">
        {allChecked ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-green-400 mb-2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <p className="text-sm text-green-400">{t('dashboard.widget.habitCheckin.allDone')}</p>
          </div>
        ) : (
          <div className="space-y-2">
            {data.habits.map((habit) => (
              <div key={habit.id} className="flex items-center justify-between p-2 bg-white/5 rounded-lg">
                <div className="flex-1">
                  <p className="text-sm font-medium">{habit.name}</p>
                  <p className="text-xs text-slate-400">
                    {t('dashboard.widget.habitCheckin.streak')}: {habit.streak || 0} {t('streak.days')}
                  </p>
                </div>
                <button
                  onClick={() => handleCheckIn(habit.id)}
                  disabled={habit.checked_today || checking[habit.id]}
                  className={`w-10 h-10 flex items-center justify-center rounded-lg transition-all ${
                    habit.checked_today
                      ? 'bg-green-500/20 text-green-400 cursor-default'
                      : 'bg-white/10 hover:bg-green-500/20 hover:text-green-400'
                  }`}
                  aria-label={habit.checked_today ? t('dashboard.widget.habitCheckin.checked') : t('dashboard.widget.habitCheckin.checkIn')}
                >
                  {checking[habit.id] ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-2 border-green-400 border-t-transparent"></div>
                  ) : habit.checked_today ? (
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12"/>
                    </svg>
                  ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <circle cx="12" cy="12" r="10"/>
                    </svg>
                  )}
                </button>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
