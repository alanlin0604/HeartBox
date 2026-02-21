import axios from 'axios';
import { clearAuthTokens, getAccessToken, getRefreshToken, setAccessToken, setRefreshToken } from '../utils/tokenStorage';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE,
});

// --- GET request deduplication ---
const pendingGets = new Map();

api.interceptors.request.use((config) => {
  // Attach Bearer token
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // Send user language so Django returns translated error messages
  const lang = localStorage.getItem('language') || 'zh-TW';
  config.headers['Accept-Language'] = lang;
  // Cancel duplicate GET requests
  if (config.method === 'get') {
    const key = `${config.method}:${config.baseURL}${config.url}`;
    if (pendingGets.has(key)) {
      pendingGets.get(key).abort();
    }
    const controller = new AbortController();
    config.signal = controller.signal;
    pendingGets.set(key, controller);
  }
  return config;
});

// --- Response interceptors ---
api.interceptors.response.use(
  (res) => {
    // Clean up completed GET requests
    if (res.config.method === 'get') {
      const key = `${res.config.method}:${res.config.baseURL}${res.config.url}`;
      pendingGets.delete(key);
    }
    return res;
  },
  async (error) => {
    // Clean up failed GET requests
    if (error.config?.method === 'get') {
      const key = `${error.config.method}:${error.config.baseURL}${error.config.url}`;
      pendingGets.delete(key);
    }

    // Don't treat aborted requests as errors
    if (axios.isCancel(error)) {
      return Promise.reject(error);
    }

    const original = error.config;

    // Auto-refresh on 401
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = getRefreshToken();
      if (refresh) {
        try {
          const { data } = await axios.post(`${API_BASE}/auth/refresh/`, { refresh });
          setAccessToken(data.access);
          if (data.refresh) {
            setRefreshToken(data.refresh);
          }
          original.headers.Authorization = `Bearer ${data.access}`;
          return api(original);
        } catch {
          clearAuthTokens();
          window.location.href = '/login';
        }
      }
    }

    // Attach backend error code to the error for i18n lookup via t(`error.${code}`)
    const code = error.response?.data?.code;
    if (code) {
      error.errorCode = code;
    }

    // Global toast for 5xx server errors
    if (error.response?.status >= 500) {
      window.dispatchEvent(new CustomEvent('api-error', {
        detail: { messageKey: 'common.serverError' },
      }));
    }

    return Promise.reject(error);
  }
);

export default api;
