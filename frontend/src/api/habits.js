import api from './axios';
import { getCached, setCache } from './cache';

// Get all habits
export const getHabits = () => {
  const key = 'habits:list';
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get('/habits/').then(res => {
    setCache(key, res, 30_000); // 30s cache
    return res;
  });
};

// Create new habit
export const createHabit = (data) => {
  return api.post('/habits/', data);
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
  return api.patch(`/habits/${id}/`, data);
};

// Delete habit
export const deleteHabit = (id) => {
  return api.delete(`/habits/${id}/`);
};

// Check in (mark as completed today)
export const checkInHabit = (id, note = '') => {
  return api.post(`/habits/${id}/check_in/`, { note });
};

// Undo today's check-in
export const uncheckInHabit = (id) => {
  return api.delete(`/habits/${id}/check_in/`);
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
