import api from './axios';
import { getCached, setCache, invalidate } from './cache';

// Drop all habit-related cached responses (list, single, calendar, analytics)
// after any mutation so the next read sees the freshly updated state. Without
// this, creating a habit and immediately calling loadHabits() returns the
// 30s-cached list and the new habit appears to be missing until refresh.
const invalidateHabitCaches = () => invalidate('habit');

// Get all habits. Pass `force=true` to bypass the 30s cache after a mutation
// (HabitTracker does this after create/update/delete/check-in so the UI
// reflects the change immediately without a full page refresh).
export const getHabits = (force = false) => {
  const key = 'habits:list';
  if (!force) {
    const cached = getCached(key);
    if (cached) return Promise.resolve(cached);
  }
  return api.get('/habits/').then(res => {
    setCache(key, res, 30_000); // 30s cache
    return res;
  });
};

// Create new habit
export const createHabit = (data) => {
  return api.post('/habits/', data).then(res => {
    invalidateHabitCaches();
    return res;
  });
};

// Get single habit
export const getHabit = (id) => {
  const key = `habit:${id}`;
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get(`/habits/${id}/`).then(res => {
    setCache(key, res, 30_000);
    return res;
  });
};

// Update habit
export const updateHabit = (id, data) => {
  return api.patch(`/habits/${id}/`, data).then(res => {
    invalidateHabitCaches();
    return res;
  });
};

// Delete habit
export const deleteHabit = (id) => {
  return api.delete(`/habits/${id}/`).then(res => {
    invalidateHabitCaches();
    return res;
  });
};

// Check in (mark as completed today)
export const checkInHabit = (id, note = '') => {
  return api.post(`/habits/${id}/check_in/`, { note }).then(res => {
    invalidateHabitCaches();
    return res;
  });
};

// Undo today's check-in
export const uncheckInHabit = (id) => {
  return api.delete(`/habits/${id}/check_in/`).then(res => {
    invalidateHabitCaches();
    return res;
  });
};

// Get 90-day calendar
export const getHabitCalendar = (id) => {
  const key = `habit:${id}:calendar`;
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get(`/habits/${id}/calendar/`).then(res => {
    setCache(key, res, 60_000); // 1min cache
    return res;
  });
};

// Get habit-mood analytics
export const getHabitAnalytics = () => {
  const key = 'habits:analytics';
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get('/habits/analytics/').then(res => {
    setCache(key, res, 120_000); // 2min cache
    return res;
  });
};
