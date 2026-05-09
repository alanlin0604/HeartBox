import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLang } from '../../../context/LanguageContext';
import { useAuth } from '../../../context/AuthContext';
import { LOCALE_MAP } from '../../../utils/locales';
import { getWidgetData } from '../../../api/dashboard';
import MoodBadge from '../../MoodBadge';

export default function OnThisDayWidget({ widgetId, isEditMode, onSettings }) {
  const { t, lang } = useLang();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
      console.error('Failed to load on this day data:', err);
      setError(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="glass p-4 rounded-xl h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-400 border-t-transparent"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass p-4 rounded-xl h-full flex flex-col">
        <header className="flex justify-between items-center mb-3">
          <h3 className="font-semibold text-blue-400">{t('dashboard.widget.onThisDay.title')}</h3>
          <button
            className="w-10 h-10 flex items-center justify-center hover:bg-white/10 rounded transition-colors"
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

  if (!data || !data.notes || data.notes.length === 0) {
    return (
      <div className="glass p-4 rounded-xl h-full flex flex-col">
        <header className="flex justify-between items-center mb-3">
          <h3 className="font-semibold text-blue-400">{t('dashboard.widget.onThisDay.title')}</h3>
          <button
            className="w-10 h-10 flex items-center justify-center hover:bg-white/10 rounded transition-colors"
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

  const handleNoteClick = (noteId) => {
    navigate(`/notes/${noteId}`);
  };

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
        <h3 className="font-semibold text-blue-400">{t('dashboard.widget.onThisDay.title')}</h3>
        <button
          className="w-10 h-10 flex items-center justify-center hover:bg-white/10 rounded transition-colors"
          onClick={onSettings}
          aria-label={t('dashboard.settings')}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>
            <circle cx="12" cy="12" r="3"/>
          </svg>
        </button>
      </header>
      <main className="flex-1 overflow-auto space-y-3">
        {data.notes.map((note) => {
          const date = new Date(note.created_at);
          const yearsAgo = new Date().getFullYear() - date.getFullYear();
          const dateStr = date.toLocaleDateString(LOCALE_MAP[lang] || lang, {
            timeZone: user?.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone,
            year: 'numeric',
            month: 'short',
            day: 'numeric',
          });

          return (
            <button
              key={note.id}
              onClick={() => handleNoteClick(note.id)}
              className="w-full text-left p-3 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
            >
              <div className="flex items-center justify-between mb-1">
                <p className="text-xs text-blue-400">
                  {yearsAgo > 0 ? t('dashboard.widget.onThisDay.yearsAgo', { years: yearsAgo }) : dateStr}
                </p>
                <MoodBadge score={note.sentiment_score} />
              </div>
              <p className="text-sm line-clamp-2 opacity-80">{note.content_preview || '...'}</p>
            </button>
          );
        })}
      </main>
    </div>
  );
}
