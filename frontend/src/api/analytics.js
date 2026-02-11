import api from './axios';
import { getCached, setCache } from './cache';

export const getAnalytics = (period = 'week', lookbackDays = 30) => {
  const key = `analytics:${period}:${lookbackDays}`;
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get(`/analytics/?period=${period}&lookback_days=${lookbackDays}`).then(res => {
    setCache(key, res, 60_000);
    return res;
  });
};

export const getCalendarData = (year, month) => {
  const key = `calendar:${year}:${month}`;
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get(`/analytics/calendar/?year=${year}&month=${month}`).then(res => {
    setCache(key, res, 60_000);
    return res;
  });
};
