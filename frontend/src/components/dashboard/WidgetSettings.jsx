import { useLang } from '../../context/LanguageContext';
import Modal from '../ui/Modal';

export default function WidgetSettings({ widget, isOpen, onClose, onToggle }) {
  const { t } = useLang();

  if (!widget) return null;

  const widgetInfo = {
    streak: {
      name: t('dashboard.widget.streak.title'),
      description: t('dashboard.widget.streak.description'),
    },
    mood_trends: {
      name: t('dashboard.widget.moodTrends.title'),
      description: t('dashboard.widget.moodTrends.description'),
    },
    on_this_day: {
      name: t('dashboard.widget.onThisDay.title'),
      description: t('dashboard.widget.onThisDay.description'),
    },
    habit_checkin: {
      name: t('dashboard.widget.habitCheckin.title'),
      description: t('dashboard.widget.habitCheckin.description'),
    },
    ai_suggestions: {
      name: t('dashboard.widget.aiSuggestions.title'),
      description: t('dashboard.widget.aiSuggestions.description'),
    },
    sleep_stats: {
      name: t('dashboard.widget.sleepStats.title'),
      description: t('dashboard.widget.sleepStats.description'),
    },
  };

  const info = widgetInfo[widget.id] || { name: widget.id, description: '' };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t('dashboard.widgetSettings')}>
      <div className="space-y-4">
        <div>
          <h3 className="font-semibold mb-1">{info.name}</h3>
          <p className="text-sm text-slate-400">{info.description}</p>
        </div>

        <div className="flex items-center justify-between p-3 bg-white/5 rounded-lg">
          <div>
            <p className="font-medium text-sm">{t('dashboard.widgetEnabled')}</p>
            <p className="text-xs text-slate-400">{t('dashboard.widgetEnabledHint')}</p>
          </div>
          <button
            onClick={() => onToggle(widget.id)}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
              widget.enabled ? 'bg-orange-500' : 'bg-slate-600'
            }`}
            aria-label={widget.enabled ? t('dashboard.disable') : t('dashboard.enable')}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                widget.enabled ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors"
          >
            {t('common.close')}
          </button>
        </div>
      </div>
    </Modal>
  );
}
