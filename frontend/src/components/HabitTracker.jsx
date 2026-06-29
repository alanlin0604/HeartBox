import { useState, useEffect, useCallback } from 'react';
import { AnimatePresence } from 'framer-motion';
import { useLang } from '../context/LanguageContext';
import { useToast } from '../context/ToastContext';
import {
  getHabits,
  createHabit,
  updateHabit,
  deleteHabit,
  checkInHabit,
  uncheckInHabit,
} from '../api/habits';
import LoadingSpinner from './LoadingSpinner';
import EmptyState from './EmptyState';
import HabitCard from './HabitCard';
import HabitForm from './HabitForm';
import HabitCorrelation from './HabitCorrelation';
import ConfirmModal from './ConfirmModal';

export default function HabitTracker() {
  const { t } = useLang();
  const toast = useToast();
  const [habits, setHabits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingHabit, setEditingHabit] = useState(null);
  const [deleteConfirm, setDeleteConfirm] = useState(null);

  // `force=true` bypasses the 30s GET cache. We use it after every mutation
  // so the UI reflects the change without a manual page refresh — relying on
  // invalidate() alone left a window where the stale cached entry came back.
  // The `silent` flag skips the loading spinner so an optimistic UI update
  // (e.g. just-flipped check-in) isn't blanked out during the background sync.
  const loadHabits = useCallback(async (force = false, silent = false) => {
    if (!silent) setLoading(true);
    try {
      const res = await getHabits(force);
      // DRF global pagination wraps list responses in {count, results: [...]};
      // tolerate both shapes so the page doesn't crash if pagination is toggled.
      const list = Array.isArray(res.data) ? res.data : (res.data?.results || []);
      setHabits(list);
    } catch (error) {
      console.error('Failed to load habits:', error);
      toast?.error(t('habit.loadError'));
    } finally {
      if (!silent) setLoading(false);
    }
  }, [t, toast]);

  useEffect(() => {
    loadHabits();
  }, [loadHabits]);

  // All mutation handlers patch the in-memory list directly using either the
  // optimistic value (instant feedback) or the API response (authoritative).
  // No follow-up GET, so the page never goes through a re-fetch render.

  const handleCreate = async (data) => {
    try {
      const res = await createHabit(data);
      // Backend returns the full HabitSerializer payload — append it.
      setHabits((prev) => [...prev, res.data]);
      toast?.success(t('habit.createSuccess'));
      setShowForm(false);
    } catch (error) {
      console.error('Failed to create habit:', error);
      toast?.error(t('common.operationFailed'));
      throw error;
    }
  };

  const handleUpdate = async (id, data) => {
    try {
      const res = await updateHabit(id, data);
      setHabits((prev) => prev.map((h) => (h.id === id ? res.data : h)));
      toast?.success(t('common.saveSuccess'));
      setEditingHabit(null);
    } catch (error) {
      console.error('Failed to update habit:', error);
      toast?.error(t('common.operationFailed'));
      throw error;
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteHabit(id);
      setHabits((prev) => prev.filter((h) => h.id !== id));
      toast?.success(t('habit.deleteSuccess'));
      setDeleteConfirm(null);
    } catch (error) {
      console.error('Failed to delete habit:', error);
      toast?.error(t('common.operationFailed'));
    }
  };

  // Check-in returns a HabitLog (not a Habit), so streak / completion_rate
  // can drift up to 1 entry. Bump them client-side too — close enough until
  // the next mount-time refresh or until the user navigates back.
  const handleCheckIn = async (id, note = '') => {
    setHabits((prev) =>
      prev.map((h) =>
        h.id === id
          ? {
              ...h,
              checked_today: true,
              streak: (h.streak || 0) + 1,
            }
          : h,
      ),
    );
    try {
      await checkInHabit(id, note);
      toast?.success(t('habit.checkInSuccess'));
    } catch (error) {
      // Roll back on failure
      setHabits((prev) =>
        prev.map((h) =>
          h.id === id
            ? { ...h, checked_today: false, streak: Math.max(0, (h.streak || 1) - 1) }
            : h,
        ),
      );
      console.error('Failed to check in:', error);
      toast?.error(t('habit.checkInFailed'));
    }
  };

  const handleUncheckIn = async (id) => {
    setHabits((prev) =>
      prev.map((h) =>
        h.id === id
          ? { ...h, checked_today: false, streak: Math.max(0, (h.streak || 1) - 1) }
          : h,
      ),
    );
    try {
      await uncheckInHabit(id);
      toast?.success(t('habit.uncheckInSuccess') || t('common.saveSuccess'));
    } catch (error) {
      setHabits((prev) =>
        prev.map((h) =>
          h.id === id ? { ...h, checked_today: true, streak: (h.streak || 0) + 1 } : h,
        ),
      );
      console.error('Failed to undo check-in:', error);
      toast?.error(t('habit.checkInFailed'));
    }
  };

  const handleEdit = (habit) => {
    setEditingHabit(habit);
    setShowForm(true);
  };

  const handleCloseForm = () => {
    setShowForm(false);
    setEditingHabit(null);
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-[var(--text-primary)]">
            {t('habit.title')}
          </h1>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">
            {t('habit.subtitle')}
          </p>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="btn-primary"
          aria-label={t('habit.createNew')}
        >
          <svg
            className="w-5 h-5 mr-2"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 4v16m8-8H4"
            />
          </svg>
          {t('habit.createNew')}
        </button>
      </div>

      {/* Habits Grid */}
      {habits.length === 0 ? (
        <EmptyState
          title={t('habit.emptyTitle')}
          description={t('habit.emptyDescription')}
          actionText={t('habit.createNew')}
          onAction={() => setShowForm(true)}
          icon={() => (
            <svg
              className="w-12 h-12"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          )}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {habits.map((habit) => (
            <HabitCard
              key={habit.id}
              habit={habit}
              onCheckIn={handleCheckIn}
              onUncheckIn={handleUncheckIn}
              onEdit={handleEdit}
              onDelete={(id) => setDeleteConfirm(id)}
            />
          ))}
        </div>
      )}

      {/* Correlation Analytics — temporarily hidden pre-defense. The chart
          is technically correct but with only 1 habit per user the X-axis
          shows a single bar which made the chart look broken. Re-enable
          once we have multi-habit users or restructure to show per-habit
          summary cards instead of one chart. */}
      {false && habits.length > 0 && (
        <div className="mt-12">
          <HabitCorrelation />
        </div>
      )}

      {/* Create/Edit Form Modal */}
      <AnimatePresence>
        {showForm && (
          <HabitForm
            habit={editingHabit}
            onSubmit={editingHabit ? handleUpdate : handleCreate}
            onClose={handleCloseForm}
          />
        )}
      </AnimatePresence>

      {/* Delete Confirmation */}
      <ConfirmModal
        open={!!deleteConfirm}
        title={t('habit.deleteConfirm')}
        message={t('habit.deleteConfirmMessage')}
        confirmText={t('common.delete')}
        cancelText={t('common.cancel')}
        onConfirm={() => handleDelete(deleteConfirm)}
        onCancel={() => setDeleteConfirm(null)}
      />
    </div>
  );
}
