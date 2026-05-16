import api from './axios';

export const getStats = () => api.get('/admin/stats/');

export const getUsers = (search = '') =>
  api.get('/admin/users/', { params: search ? { search } : {} });

export const getUser = (id) => api.get(`/admin/users/${id}/`);

export const updateUser = (id, data) => api.patch(`/admin/users/${id}/`, data);

export const getCounselors = (status = '') =>
  api.get('/admin/counselors/', { params: status ? { status } : {} });

export const counselorAction = (id, action) =>
  api.post(`/admin/counselors/${id}/action/`, { action });

export const getFeedback = () => api.get('/admin/feedback/');

// Community moderation (staff-only)
export const getCommunityReports = (status = 'open') =>
  api.get('/community/reports/', { params: { status } });

export const moderateCommunityPost = (postId, action) =>
  api.post(`/community/posts/${postId}/moderate/`, { action });

// Audit log feed (staff-only)
export const getAuditLogs = (params = {}) =>
  api.get('/admin/audit-logs/', { params });
