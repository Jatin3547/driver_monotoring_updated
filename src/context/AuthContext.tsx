import { createContext, useCallback, useEffect, useState, type ReactNode } from 'react';
import * as authService from '@/services/api/authService';
import type { AuthUser } from '@/services/api/authService';
import { USE_MOCK_DATA } from '@/services/config';

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // On mount, if a token is already stored (from a previous real-backend
  // session) and we're not in mock mode, validate it against /auth/me.
  useEffect(() => {
    if (USE_MOCK_DATA) return;
    const token = authService.getStoredToken();
    if (!token) return;
    authService
      .fetchCurrentUser(token)
      .then(setUser)
      .catch(() => authService.setStoredToken(null));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await authService.login(email, password);
      authService.setStoredToken(result.access_token);
      setUser(result.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const register = useCallback(async (email: string, password: string, fullName: string) => {
    setLoading(true);
    setError(null);
    try {
      await authService.register(email, password, fullName);
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [login]);

  const logout = useCallback(() => {
    authService.setStoredToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, isAuthenticated: user !== null, loading, error, login, register, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}
