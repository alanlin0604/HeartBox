import api from './axios';

export const login = (username, password) =>
  api.post('/auth/login/', { username, password });

export const register = (username, email, password, consent = {}) =>
  api.post('/auth/register/', {
    username,
    email,
    password,
    accepts_terms: !!consent.acceptsTerms,
    age_confirmed_13_plus: !!consent.age13Plus,
  });

export const getProfile = () => api.get('/auth/profile/');

export const updateProfile = (data) => api.patch('/auth/profile/', data);

export const logoutOtherDevices = () => api.post('/auth/logout-other-devices/');

export const forgotPassword = (email) => api.post('/auth/password/forgot/', { email });

export const resetPassword = (uid, token, newPassword) =>
  api.post('/auth/password/reset/', { uid, token, new_password: newPassword });

export const deleteAccount = (password) =>
  api.post('/auth/delete-account/', { password });

export const verifyEmail = (uid, token) =>
  api.get('/auth/verify-email/', { params: { uid, token } });

/**
 * Submit the 3-step consent gate (ToS + AI training opt-in + age band).
 * For users in the 13-17 age band, `guardian_email` is required and the
 * backend will email the guardian a verification link.
 */
export const submitConsent = ({ acceptsTerms, consentAiTraining, ageBand, guardianEmail }) =>
  api.post('/auth/consent/', {
    accepts_terms: !!acceptsTerms,
    consent_ai_training: !!consentAiTraining,
    age_band: ageBand,
    guardian_email: guardianEmail || '',
  });

export const guardianConfirm = (token) =>
  api.get('/auth/guardian-confirm/', { params: { token } });

export const resendVerification = () =>
  api.post('/auth/resend-verification/');

export const googleLogin = (credential) =>
  api.post('/auth/google/', { credential });
