import api from './axios';
import { getCached, setCache } from './cache';

// Default lookback widened 30 -> 90 days because the analytics widgets
// (correlation / tag aggregation) need >=3 paired observations to render
// anything, and a casual journaler often doesn't hit that in 30 days.
// Backend also auto-expands to 180d / 365d when the requested span is too
// sparse, and reports the actually-used window via actual_lookback_days.
export const getAnalytics = (period = 'week', lookbackDays = 90) => {
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
