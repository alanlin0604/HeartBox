import { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import { login as apiLogin, register as apiRegister, getProfile } from '../api/auth';
import { clearAll as clearCache } from '../api/cache';
import { clearAuthTokens, getAccessToken, getRefreshToken, setAuthTokens } from '../utils/tokenStorage';

const AuthContext = createContext(null);

const USER_CACHE_KEY = 'heartbox_user_cache';

function getCachedUser() {
  try {
    const raw = localStorage.getItem(USER_CACHE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function setCachedUser(data) {
  try {
    if (data) localStorage.setItem(USER_CACHE_KEY, JSON.stringify(data));
    else localStorage.removeItem(USER_CACHE_KEY);
  } catch { /* ignore */ }
}

export function AuthProvider({ children }) {
  const cached = getCachedUser();
  const token = getAccessToken();
  const [user, setUser] = useState(token ? cached : null);
  const [loading, setLoading] = useState(token && !cached);

  useEffect(() => {
    if (token) {
      getProfile()
        .then((res) => {
          setUser(res.data);
          setCachedUser(res.data);
        })
        .catch(() => {
          clearAuthTokens();
          setCachedUser(null);
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setCachedUser(null);
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (username, password, rememberMe = true) => {
    const { data } = await apiLogin(username, password);
    if (data.requires_2fa) {
      return data; // Return 2FA data to caller without setting tokens
    }
    // Clear any in-memory cache from a previous session BEFORE storing the
    // new tokens. Otherwise a "log out + log in as another user on the same
    // tab" flow would still see the previous user's cached responses for up
    // to TTL seconds (60s default).
    clearCache();
    setAuthTokens(data.access, data.refresh, rememberMe);
    if (data.user) {
      setUser(data.user);
      setCachedUser(data.user);
    } else {
      const profile = await getProfile();
      setUser(profile.data);
      setCachedUser(profile.data);
    }
    return data;
  }, []);

  const registerUser = useCallback(async (username, email, password) => {
    await apiRegister(username, email, password);
    await login(username, password, true);
  }, [login]);

  const logout = useCallback(async () => {
    // Best-effort: tell the backend to blacklist this refresh token so a
    // stolen token from a "logged-out" device can't be used for 7 days.
    // Don't await — slow logout would feel broken; fire-and-forget is fine
    // because clearAuthTokens runs unconditionally below.
    try {
      const refresh = getRefreshToken();
      if (refresh) {
        const { default: api } = await import('../api/axios');
        api.post('/auth/logout/', { refresh }).catch(() => {});
      }
    } catch { /* network or import error — local clear still runs */ }
    clearAuthTokens();
    clearCache();
    setCachedUser(null);
    if ('caches' in window) {
      caches.keys().then(keys => keys.forEach(k => caches.delete(k)));
    }
    setUser(null);
    window.location.href = '/login';
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const res = await getProfile();
      setUser(res.data);
      setCachedUser(res.data);
    } catch { /* ignore */ }
  }, []);

  const value = useMemo(() => ({ user, loading, login, register: registerUser, logout, refreshUser }), [user, loading, login, registerUser, logout, refreshUser]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export const useAuth = () => useContext(AuthContext);
