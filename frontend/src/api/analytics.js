import api from './axios';
import { getCached, setCache } from './cache';

// Default lookback 180 days. A casual journaler doesn't accumulate
// enough tagged notes in 90d to populate the tag-driven widgets; 180d
// catches the long-tail without going to lifetime semantics. Backend
// auto-expands further (365d) on sparse and reports the actual span via
// actual_lookback_days.
export const getAnalytics = (period = 'week', lookbackDays = 180) => {
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
