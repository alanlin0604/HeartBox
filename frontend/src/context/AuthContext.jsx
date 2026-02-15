import { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import { login as apiLogin, register as apiRegister, getProfile } from '../api/auth';
import { clearAll as clearCache } from '../api/cache';
import { clearAuthTokens, getAccessToken, setAuthTokens } from '../utils/tokenStorage';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getAccessToken();
    if (token) {
      getProfile()
        .then((res) => setUser(res.data))
        .catch(() => {
          clearAuthTokens();
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = useCallback(async (username, password, rememberMe = true) => {
    const { data } = await apiLogin(username, password);
    setAuthTokens(data.access, data.refresh, rememberMe);
    const profile = await getProfile();
    setUser(profile.data);
  }, []);

  const registerUser = useCallback(async (username, email, password) => {
    await apiRegister(username, email, password);
    await login(username, password, true);
  }, [login]);

  const logout = useCallback(() => {
    clearAuthTokens();
    clearCache();
    if ('caches' in window) {
      caches.keys().then(keys => keys.forEach(k => caches.delete(k)));
    }
    setUser(null);
    window.location.href = '/login';
  }, []);

  const value = useMemo(() => ({ user, loading, login, register: registerUser, logout }), [user, loading, login, registerUser, logout]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
