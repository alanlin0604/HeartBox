import api from './axios';
import { getCached, setCache } from './cache';

// Get dashboard layout
export const getDashboardLayout = () => {
  const key = 'dashboard:layout';
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get('/dashboard/layout/').then(res => {
    setCache(key, res, 60_000); // 1min cache
    return res;
  });
};

// Update dashboard layout
export const updateDashboardLayout = (layoutConfig) => {
  return api.put('/dashboard/layout/', { layout_config: layoutConfig });
};

// Reset dashboard layout to default
export const resetDashboardLayout = () => {
  return api.post('/dashboard/layout/reset/');
};

// Get all user metrics
export const getMetrics = () => {
  const key = 'dashboard:metrics';
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get('/dashboard/metrics/').then(res => {
    setCache(key, res, 60_000); // 1min cache
    return res;
  });
};

// Create new metric
export const createMetric = (data) => {
  return api.post('/dashboard/metrics/', data);
};

// Update metric
export const updateMetric = (id, data) => {
  return api.patch(`/dashboard/metrics/${id}/`, data);
};

// Delete metric
export const deleteMetric = (id) => {
  return api.delete(`/dashboard/metrics/${id}/`);
};

// Get widget data by widget ID
export const getWidgetData = (widgetId) => {
  const key = `dashboard:widget:${widgetId}`;
  const cached = getCached(key);
  if (cached) return Promise.resolve(cached);
  return api.get(`/dashboard/widget-data/${widgetId}/`).then(res => {
    setCache(key, res, 30_000); // 30s cache
    return res;
  });
};

// Refresh all metrics (recalculate current values)
export const refreshMetrics = () => {
  return api.post('/dashboard/metrics/refresh/');
};
