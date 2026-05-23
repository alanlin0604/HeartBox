import { useState, useEffect } from 'react';
import { useLang } from '../context/LanguageContext';

// User-pickable habit accent colors. Brand orange/rose first so the
// default-most-used selections match the rest of the app.
const COLORS = [
  '#f97316', // orange-500 (brand)
  '#fb923c', // orange-400
  '#f43f5e', // rose-500 (brand)
  '#ec4899', // pink-500
  '#f59e0b', // amber-500
  '#10b981', // emerald-500
  '#3b82f6', // blue-500
  '#06b6d4', // cyan-500
];

// Habit icon options — strings stored on Habit.icon. New entries are SVG
// paths (start with "/"); existing habits in DB may still hold the old
// emoji characters, which the renderer falls back to displaying as text.
// The 12 slots roughly match the original set (check / run / book(art) /
// meditate / muscle / target / water / brush(/clean) / sun / apple /
// banana / cooking).
const ICONS = [
  '/icons/habit-check.svg',
  '/icons/habit-runner.svg',
  '/icons/habit-art.svg',
  '/icons/habit-meditate.svg',
  '/icons/habit-muscle.svg',
  '/icons/habit-target.svg',
  '/icons/habit-water.svg',
  '/icons/habit-brush.svg',
  '/icons/habit-sun.svg',
  '/icons/habit-apple.svg',
  '/icons/habit-banana.svg',
  '/icons/act-cooking.svg',
];

const FREQUENCIES = [
  { value: 'daily', label: 'habit.frequencyDaily' },
  { value: 'weekly', label: 'habit.frequencyWeekly' },
  { value: 'custom', label: 'habit.frequencyCustom' },
];

export default function HabitForm({ habit, onSubmit, onClose }) {
  const { t } = useLang();
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    category: '',
    color: COLORS[0],
    icon: ICONS[0],
    target_frequency: 'daily',
    target_count: 1,
    is_active: true,
    reminder_enabled: false,
    reminder_time: '',
  });
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (habit) {
      setFormData({
        name: habit.name || '',
        description: habit.description || '',
        category: habit.category || '',
        color: habit.color || COLORS[0],
        icon: habit.icon || ICONS[0],
        target_frequency: habit.target_frequency || 'daily',
        target_count: habit.target_count || 1,
        is_active: habit.is_active ?? true,
        reminder_enabled: habit.reminder_enabled ?? false,
        reminder_time: habit.reminder_time ? habit.reminder_time.slice(0, 5) : '',
      });
    }
  }, [habit]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      // Backend TimeField is nullable — send null instead of '' so DRF accepts it.
      // Also: if reminder is toggled on but no time chosen, treat as disabled.
      const hasTime = !!formData.reminder_time;
      const payload = {
        ...formData,
        reminder_enabled: formData.reminder_enabled && hasTime,
        reminder_time: hasTime ? formData.reminder_time : null,
      };
      if (habit) {
        await onSubmit(habit.id, payload);
      } else {
        await onSubmit(payload);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="glass-card p-6 max-w-lg w-full max-h-[90vh] overflow-y-auto"
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-bold text-[var(--text-primary)]">
            {habit ? t('habit.editHabit') : t('habit.createNew')}
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-[var(--card-bg)] rounded-lg transition-colors"
            aria-label={t('common.close')}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
              {t('habit.name')} <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              className="glass-input w-full"
              placeholder={t('habit.namePlaceholder')}
              required
              maxLength={100}
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
              {t('habit.description')}
            </label>
            <textarea
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              className="glass-input w-full resize-none"
              rows={3}
              placeholder={t('habit.descriptionPlaceholder')}
              maxLength={500}
            />
          </div>

          {/* Category */}
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
              {t('habit.category')}
            </label>
            <input
              type="text"
              value={formData.category}
              onChange={(e) => handleChange('category', e.target.value)}
              className="glass-input w-full"
              placeholder={t('habit.categoryPlaceholder')}
              maxLength={50}
            />
          </div>

          {/* Color Picker */}
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
              {t('habit.color')}
            </label>
            <div className="grid grid-cols-8 gap-2">
              {COLORS.map((color) => (
                <button
                  key={color}
                  type="button"
                  onClick={() => handleChange('color', color)}
                  className={`
                    w-10 h-10 rounded-lg transition-all duration-200
                    ${formData.color === color ? 'ring-2 ring-offset-2 ring-orange-500 scale-110' : 'hover:scale-105'}
                  `}
                  style={{ backgroundColor: color }}
                  aria-label={`Color ${color}`}
                />
              ))}
            </div>
          </div>

          {/* Icon Picker */}
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
              {t('habit.icon')}
            </label>
            <div className="grid grid-cols-6 gap-2">
              {ICONS.map((icon) => (
                <button
                  key={icon}
                  type="button"
                  onClick={() => handleChange('icon', icon)}
                  className={`
                    w-12 h-12 rounded-lg text-2xl transition-all duration-200 flex items-center justify-center
                    ${formData.icon === icon ? 'bg-orange-500/20 ring-2 ring-orange-500 scale-110' : 'bg-[var(--card-bg)] hover:bg-orange-500/10 hover:scale-105'}
                  `}
                >
                  {icon.startsWith('/')
                    ? <img src={icon} alt="" aria-hidden="true" className="w-7 h-7 object-contain" />
                    : icon}
                </button>
              ))}
            </div>
          </div>

          {/* Target Frequency */}
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
              {t('habit.targetFrequency')}
            </label>
            <div className="grid grid-cols-3 gap-3">
              {FREQUENCIES.map((freq) => (
                <button
                  key={freq.value}
                  type="button"
                  onClick={() => handleChange('target_frequency', freq.value)}
                  className={`
                    py-2 px-4 rounded-lg text-sm font-medium transition-all duration-200
                    ${
                      formData.target_frequency === freq.value
                        ? 'bg-orange-500 text-white'
                        : 'bg-[var(--card-bg)] text-[var(--text-secondary)] hover:bg-orange-500/10'
                    }
                  `}
                >
                  {t(freq.label)}
                </button>
              ))}
            </div>
          </div>

          {/* Target Count */}
          {formData.target_frequency === 'custom' && (
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                {t('habit.targetCount')}
              </label>
              <input
                type="number"
                value={formData.target_count}
                onChange={(e) => handleChange('target_count', parseInt(e.target.value) || 1)}
                className="glass-input w-full"
                min={1}
                max={365}
              />
            </div>
          )}

          {/* Active Toggle */}
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-[var(--text-primary)]">
              {t('habit.isActive')}
            </label>
            <button
              type="button"
              onClick={() => handleChange('is_active', !formData.is_active)}
              className={`
                relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                ${formData.is_active ? 'bg-orange-500' : 'bg-gray-600'}
              `}
            >
              <span
                className={`
                  inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                  ${formData.is_active ? 'translate-x-6' : 'translate-x-1'}
                `}
              />
            </button>
          </div>

          {/* Reminder */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <label className="block text-sm font-medium text-[var(--text-primary)]">
                  {t('habit.reminder')}
                </label>
                <p className="text-xs text-[var(--text-secondary)] mt-0.5">
                  {t('habit.reminderHint')}
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleChange('reminder_enabled', !formData.reminder_enabled)}
                className={`
                  relative inline-flex h-6 w-11 items-center rounded-full transition-colors shrink-0
                  ${formData.reminder_enabled ? 'bg-orange-500' : 'bg-gray-600'}
                `}
                aria-label={t('habit.reminder')}
              >
                <span
                  className={`
                    inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                    ${formData.reminder_enabled ? 'translate-x-6' : 'translate-x-1'}
                  `}
                />
              </button>
            </div>
            {formData.reminder_enabled && (
              <input
                type="time"
                value={formData.reminder_time}
                onChange={(e) => handleChange('reminder_time', e.target.value)}
                className="glass-input w-full"
                required
              />
            )}
          </div>

          {/* Actions */}
          <div className="flex space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary flex-1"
              disabled={submitting}
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              className="btn-primary flex-1"
              disabled={submitting || !formData.name.trim()}
            >
              {submitting ? t('common.saving') : habit ? t('common.save') : t('common.create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
