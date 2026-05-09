import { useState, useEffect } from 'react';
import { useLang } from '../../context/LanguageContext';
import { getMetrics, createMetric, deleteMetric, refreshMetrics } from '../../api/dashboard'
import Modal from '../ui/Modal';
import { LinearProgress } from '../ui/ProgressBar';

export default function MetricsManager({ isOpen, onClose }) {
  const { t } = useLang();
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    metric_type: 'daily_entries',
    target_value: '',
  });
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState({});

  useEffect(() => {
    if (isOpen) {
      loadMetrics();
    }
  }, [isOpen]);

  const loadMetrics = async () => {
    try {
      setLoading(true);
      const res = await getMetrics();
      setMetrics(res.data.metrics || []);
    } catch (err) {
      console.error('Failed to load metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    try {
      setRefreshing(true);
      await refreshMetrics();
      await loadMetrics();
      window.dispatchEvent(new CustomEvent('api-success', {
        detail: { messageKey: 'dashboard.metricsRefreshed' },
      }));
    } catch (err) {
      console.error('Failed to refresh metrics:', err);
      window.dispatchEvent(new CustomEvent('api-error', {
        detail: { messageKey: 'dashboard.refreshFailed' },
      }));
    } finally {
      setRefreshing(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.target_value || parseFloat(formData.target_value) <= 0) {
      window.dispatchEvent(new CustomEvent('api-error', {
        detail: { messageKey: 'dashboard.invalidTarget' },
      }));
      return;
    }

    try {
      setSubmitting(true);
      await createMetric({
        metric_type: formData.metric_type,
        target_value: parseFloat(formData.target_value),
      });
      setFormData({ metric_type: 'daily_entries', target_value: '' });
      setShowForm(false);
      await loadMetrics();
      window.dispatchEvent(new CustomEvent('api-success', {
        detail: { messageKey: 'dashboard.metricCreated' },
      }));
    } catch (err) {
      console.error('Failed to create metric:', err);
      window.dispatchEvent(new CustomEvent('api-error', {
        detail: { messageKey: 'dashboard.createFailed' },
      }));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id) => {
    if (deleting[id]) return;

    try {
      setDeleting(prev => ({ ...prev, [id]: true }));
      await deleteMetric(id);
      await loadMetrics();
      window.dispatchEvent(new CustomEvent('api-success', {
        detail: { messageKey: 'dashboard.metricDeleted' },
      }));
    } catch (err) {
      console.error('Failed to delete metric:', err);
      window.dispatchEvent(new CustomEvent('api-error', {
        detail: { messageKey: 'dashboard.deleteFailed' },
      }));
    } finally {
      setDeleting(prev => ({ ...prev, [id]: false }));
    }
  };

  const metricTypes = [
    { value: 'daily_entries', label: t('dashboard.metrics.types.daily_entries') },
    { value: 'avg_mood', label: t('dashboard.metrics.types.avg_mood') },
    { value: 'streak_days', label: t('dashboard.metrics.types.streak_days') },
    { value: 'habit_completion', label: t('dashboard.metrics.types.habit_completion') },
    { value: 'sleep_hours', label: t('dashboard.metrics.types.sleep_hours') },
    { value: 'exercise_minutes', label: t('dashboard.metrics.types.exercise_minutes') },
  ];

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t('dashboard.metrics.title')}>
      <div className="space-y-4">
        {/* Header Actions */}
        <div className="flex justify-between items-center">
          <button
            onClick={() => setShowForm(!showForm)}
            className="px-4 py-2 bg-orange-500 hover:bg-orange-600 rounded-lg transition-colors text-sm font-medium"
          >
            {showForm ? t('common.cancel') : t('dashboard.metrics.create')}
          </button>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors text-sm font-medium disabled:opacity-50 flex items-center gap-2"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className={refreshing ? 'animate-spin' : ''}
            >
              <path d="M21 2v6h-6M3 12a9 9 0 0 1 15-6.7L21 8M3 22v-6h6M21 12a9 9 0 0 1-15 6.7L3 16"/>
            </svg>
            {t('dashboard.metrics.refresh')}
          </button>
        </div>

        {/* Create Form */}
        {showForm && (
          <form onSubmit={handleSubmit} className="p-4 bg-white/5 rounded-lg space-y-3">
            <div>
              <label className="block text-sm font-medium mb-1">
                {t('dashboard.metrics.type')}
              </label>
              <select
                value={formData.metric_type}
                onChange={(e) => setFormData({ ...formData, metric_type: e.target.value })}
                className="w-full px-3 py-2 bg-white/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
              >
                {metricTypes.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                {t('dashboard.metrics.target')}
              </label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={formData.target_value}
                onChange={(e) => setFormData({ ...formData, target_value: e.target.value })}
                className="w-full px-3 py-2 bg-white/10 rounded-lg focus:outline-none focus:ring-2 focus:ring-orange-500"
                placeholder="0.0"
                required
              />
            </div>
            <button
              type="submit"
              disabled={submitting}
              className="w-full px-4 py-2 bg-orange-500 hover:bg-orange-600 rounded-lg transition-colors font-medium disabled:opacity-50"
            >
              {submitting ? t('common.saving') : t('common.save')}
            </button>
          </form>
        )}

        {/* Metrics List */}
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-2 border-orange-500 border-t-transparent"></div>
          </div>
        ) : metrics.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-sm text-slate-400">{t('dashboard.noMetrics')}</p>
          </div>
        ) : (
          <div className="space-y-3 max-h-96 overflow-auto">
            {metrics.map((metric) => (
              <div key={metric.id} className="p-4 bg-white/5 rounded-lg space-y-2">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 className="font-medium text-sm">
                      {metricTypes.find(t => t.value === metric.metric_type)?.label || metric.metric_type}
                    </h4>
                    <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
                      <span>
                        {t('dashboard.metrics.current')}: <span className="font-semibold">{metric.current_value?.toFixed(1) || 0}</span>
                      </span>
                      <span>
                        {t('dashboard.metrics.target')}: <span className="font-semibold">{metric.target_value?.toFixed(1)}</span>
                      </span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDelete(metric.id)}
                    disabled={deleting[metric.id]}
                    className="text-red-400 hover:text-red-300 transition-colors disabled:opacity-50"
                    aria-label={t('dashboard.metrics.delete')}
                  >
                    {deleting[metric.id] ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-red-400 border-t-transparent"></div>
                    ) : (
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M3 6h18M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>
                      </svg>
                    )}
                  </button>
                </div>
                <LinearProgress value={metric.progress || 0} max={100} variant="primary" size="md" />
                <p className="text-xs text-right text-slate-400">
                  {metric.progress?.toFixed(0) || 0}% {t('dashboard.metrics.progress')}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-end pt-2 border-t border-white/10">
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
