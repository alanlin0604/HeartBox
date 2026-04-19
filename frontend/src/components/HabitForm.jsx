import { useState, useEffect } from 'react';
import { useLang } from '../context/LanguageContext';

const COLORS = [
  '#8b5cf6', // purple-500
  '#ec4899', // pink-500
  '#3b82f6', // blue-500
  '#10b981', // green-500
  '#f59e0b', // amber-500
  '#ef4444', // red-500
  '#06b6d4', // cyan-500
  '#f97316', // orange-500
];

const ICONS = ['✓', '🏃', '📚', '🧘', '💪', '🎯', '💧', '🌙', '☀️', '🍎', '🎨', '✍️'];

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
      });
    }
  }, [habit]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (habit) {
        await onSubmit(habit.id, formData);
      } else {
        await onSubmit(formData);
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
                    ${formData.color === color ? 'ring-2 ring-offset-2 ring-purple-500 scale-110' : 'hover:scale-105'}
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
                    w-12 h-12 rounded-lg text-2xl transition-all duration-200
                    ${formData.icon === icon ? 'bg-purple-500/20 ring-2 ring-purple-500 scale-110' : 'bg-[var(--card-bg)] hover:bg-purple-500/10 hover:scale-105'}
                  `}
                >
                  {icon}
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
                        ? 'bg-purple-500 text-white'
                        : 'bg-[var(--card-bg)] text-[var(--text-secondary)] hover:bg-purple-500/10'
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
                ${formData.is_active ? 'bg-purple-500' : 'bg-gray-600'}
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
