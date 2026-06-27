import axios from 'axios';
import { clearAuthTokens, getAccessToken, getRefreshToken, setAccessToken, setRefreshToken } from '../utils/tokenStorage';
import { dispatchCrisisShow } from '../context/CrisisBannerContext';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE,
});

// --- GET request deduplication ---
const pendingGets = new Map();

// --- Token refresh lock to prevent race conditions ---
let refreshPromise = null;

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
    const params = config.params ? '?' + new URLSearchParams(config.params).toString() : '';
    const key = `${config.method}:${config.baseURL}${config.url}${params}`;
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
      const resParams = res.config.params ? '?' + new URLSearchParams(res.config.params).toString() : '';
      const key = `${res.config.method}:${res.config.baseURL}${res.config.url}${resParams}`;
      pendingGets.delete(key);
    }
    // Crisis-keyword overlay: backend sets crisis_detected on note/community
    // POST responses when self-harm phrases are detected. Surface the hotline
    // banner globally so the user sees help regardless of which page they
    // were on. Detection is best-effort; never throw from this interceptor.
    try {
      if (res.data && res.data.crisis_detected) {
        dispatchCrisisShow(res.data.hotlines || {});
      }
    } catch { /* noop */ }
    return res;
  },
  async (error) => {
    // Clean up failed GET requests
    if (error.config?.method === 'get') {
      const errParams = error.config.params ? '?' + new URLSearchParams(error.config.params).toString() : '';
      const key = `${error.config.method}:${error.config.baseURL}${error.config.url}${errParams}`;
      pendingGets.delete(key);
    }

    // Don't treat aborted requests as errors
    if (axios.isCancel(error)) {
      return Promise.reject(error);
    }

    const original = error.config;

    // Transient-error retry (429 rate-limit / 503 service unavailable —
    // typical signatures of a Cloud Run cold start, scaling event, or a
    // brief upstream blip). Up to 2 retries with exponential backoff so
    // the demo doesn't show a "server error" toast on a transient hiccup.
    // Only safe HTTP methods + 503 (which means the server didn't process
    // anything) are auto-retried; we never blindly retry POST on a 429
    // because the action may have partially completed.
    const status = error.response?.status;
    const method = (original?.method || 'get').toLowerCase();
    const isSafeMethod = method === 'get' || method === 'head';
    const isRetryable = status === 503 || (status === 429 && isSafeMethod);
    if (original && isRetryable) {
      original._retryCount = (original._retryCount || 0);
      if (original._retryCount < 2) {
        original._retryCount += 1;
        // Honor Retry-After if the server hinted it; otherwise exp backoff
        const retryAfter = parseInt(error.response.headers?.['retry-after'], 10);
        const backoffMs = Number.isFinite(retryAfter) && retryAfter > 0
          ? Math.min(retryAfter * 1000, 5000)
          : 500 * Math.pow(2, original._retryCount - 1);  // 500ms, 1s
        await new Promise((resolve) => setTimeout(resolve, backoffMs));
        return api(original);
      }
    }

    // Auto-refresh on 401 with global lock to prevent race conditions
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = getRefreshToken();
      if (refresh) {
        try {
          // Global lock: only one refresh request at a time
          if (!refreshPromise) {
            refreshPromise = axios.post(`${API_BASE}/auth/refresh/`, { refresh })
              .then(({ data }) => {
                setAccessToken(data.access);
                if (data.refresh) {
                  setRefreshToken(data.refresh);
                }
                return data.access;
              })
              .catch((err) => {
                clearAuthTokens();
                window.location.href = '/login';
                throw err;
              })
              .finally(() => {
                refreshPromise = null;
              });
          }

          // Wait for the refresh to complete (either from this request or another)
          const newAccessToken = await refreshPromise;
          original.headers.Authorization = `Bearer ${newAccessToken}`;
          return api(original);
        } catch {
          // Error handling is done in the catch above
          return Promise.reject(error);
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
