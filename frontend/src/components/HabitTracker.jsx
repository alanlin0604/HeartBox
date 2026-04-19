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

  const loadHabits = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getHabits();
      setHabits(res.data || []);
    } catch (error) {
      console.error('Failed to load habits:', error);
      toast?.error(t('habit.loadError'));
    } finally {
      setLoading(false);
    }
  }, [t, toast]);

  useEffect(() => {
    loadHabits();
  }, [loadHabits]);

  const handleCreate = async (data) => {
    try {
      await createHabit(data);
      toast?.success(t('habit.createSuccess'));
      setShowForm(false);
      await loadHabits();
    } catch (error) {
      console.error('Failed to create habit:', error);
      toast?.error(t('common.operationFailed'));
      throw error;
    }
  };

  const handleUpdate = async (id, data) => {
    try {
      await updateHabit(id, data);
      toast?.success(t('common.saveSuccess'));
      setEditingHabit(null);
      await loadHabits();
    } catch (error) {
      console.error('Failed to update habit:', error);
      toast?.error(t('common.operationFailed'));
      throw error;
    }
  };

  const handleDelete = async (id) => {
    try {
      await deleteHabit(id);
      toast?.success(t('habit.deleteSuccess'));
      setDeleteConfirm(null);
      await loadHabits();
    } catch (error) {
      console.error('Failed to delete habit:', error);
      toast?.error(t('common.operationFailed'));
    }
  };

  const handleCheckIn = async (id) => {
    try {
      await checkInHabit(id);
      toast?.success(t('habit.checkInSuccess'));
      await loadHabits();
    } catch (error) {
      console.error('Failed to check in:', error);
      toast?.error(t('common.operationFailed'));
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
              onEdit={handleEdit}
              onDelete={(id) => setDeleteConfirm(id)}
            />
          ))}
        </div>
      )}

      {/* Correlation Analytics */}
      {habits.length > 0 && (
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
