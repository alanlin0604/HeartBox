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
