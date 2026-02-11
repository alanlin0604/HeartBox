import api from './axios';

export const login = (username, password) =>
  api.post('/auth/login/', { username, password });

export const register = (username, email, password) =>
  api.post('/auth/register/', { username, email, password });

export const getProfile = () => api.get('/auth/profile/');

export const updateProfile = (data) => api.patch('/auth/profile/', data);

export const logoutOtherDevices = () => api.post('/auth/logout-other-devices/');

export const forgotPassword = (email) => api.post('/auth/password/forgot/', { email });

export const resetPassword = (uid, token, newPassword) =>
  api.post('/auth/password/reset/', { uid, token, new_password: newPassword });
