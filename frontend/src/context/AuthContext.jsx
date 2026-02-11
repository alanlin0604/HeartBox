import { createContext, useContext, useState, useEffect } from 'react';
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

  const login = async (username, password, rememberMe = true) => {
    const { data } = await apiLogin(username, password);
    setAuthTokens(data.access, data.refresh, rememberMe);
    const profile = await getProfile();
    setUser(profile.data);
  };

  const registerUser = async (username, email, password) => {
    await apiRegister(username, email, password);
    await login(username, password, true);
  };

  const logout = () => {
    clearAuthTokens();
    clearCache();
    setUser(null);
    window.location.href = '/login';
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register: registerUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
