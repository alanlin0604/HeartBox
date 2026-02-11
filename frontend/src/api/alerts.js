import api from './axios';
import { getCached, setCache } from './cache';

export const getAlerts = () => {
  const cached = getCached('alerts');
  if (cached) return Promise.resolve(cached);
  return api.get('/alerts/').then(res => {
    setCache('alerts', res, 60_000);
    return res;
  });
};
