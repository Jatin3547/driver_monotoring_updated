import { createContext, useCallback, useEffect, useState, type ReactNode } from 'react';
import * as authService from '@/services/api/authService';
import type { AuthUser, LoginPortal } from '@/services/api/authService';
import { USE_MOCK_DATA } from '@/services/config';

export const DEMO_USER: AuthUser = {
  id: '2b90adf8-6a65-498d-aa4c-af83ec390b17',
  email: 'admin@fleetguard.demo',
  full_name: 'Fleet Admin',
  role: 'fleet_admin',
};

interface AuthContextValue {
  user: AuthUser | null;
  isAuthenticated: boolean;
  loading: boolean;
  restoring: boolean;
  error: string | null;
  login: (email: string, password: string, portal?: LoginPortal) => Promise<void>;
  loginAsDemo: (portal?: LoginPortal) => void;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const token = authService.getStoredToken();
    if (token === 'demo-token-standalone') return DEMO_USER;
    return null;
  });
  const [loading, setLoading] = useState(false);
  const [restoring, setRestoring] = useState(() => {
    const token = authService.getStoredToken();
    return Boolean(token) && token !== 'demo-token-standalone' && !USE_MOCK_DATA;
  });
  const [error, setError] = useState<string | null>(null);

  const logout = useCallback(() => {
    authService.setStoredToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    const onUnauthorized = () => logout();
    window.addEventListener('fleetguard:unauthorized', onUnauthorized);
    return () => window.removeEventListener('fleetguard:unauthorized', onUnauthorized);
  }, [logout]);

  useEffect(() => {
    const token = authService.getStoredToken();
    if (!token) {
      setRestoring(false);
      return;
    }

    if (token === 'demo-token-standalone') {
      setUser(DEMO_USER);
      setRestoring(false);
      return;
    }

    if (token === 'demo-token-driver') {
      authService.setStoredToken(null);
      setRestoring(false);
      return;
    }

    if (USE_MOCK_DATA) {
      setRestoring(false);
      return;
    }

    authService
      .fetchCurrentUser(token)
      .then(setUser)
      .catch(() => {
        authService.setStoredToken(null);
        setUser(null);
      })
      .finally(() => setRestoring(false));
  }, []);

  const loginAsDemo = useCallback((portal: LoginPortal = 'manager') => {
    if (portal === 'driver') {
      setError('Driver sign-in requires the FleetGuard backend.');
      return;
    }
    authService.setStoredToken('demo-token-standalone');
    setUser(DEMO_USER);
    setError(null);
  }, []);

  const login = useCallback(async (email: string, password: string, portal: LoginPortal = 'manager') => {
    setLoading(true);
    setError(null);

    if (USE_MOCK_DATA) {
      if (portal === 'driver') {
        const mockModeError = new Error('Driver sign-in requires the FleetGuard backend.');
        setError(mockModeError.message);
        setLoading(false);
        throw mockModeError;
      }
      loginAsDemo(portal);
      setLoading(false);
      return;
    }

    try {
      const result = await authService.login(email, password, portal);
      authService.setStoredToken(result.access_token);
      setUser(result.user);
    } catch (err: unknown) {
      const errStr = String(err);
      const isNetworkError =
        err instanceof TypeError ||
        errStr.includes('Failed to fetch') ||
        errStr.includes('Network') ||
        errStr.includes('Cannot reach');

      if (isNetworkError && portal === 'manager' && (email === 'admin@fleetguard.demo' || email.includes('admin'))) {
        console.warn('FastAPI backend is offline. Signing in as Demo Admin.');
        loginAsDemo('manager');
        return;
      }

      const msg = err instanceof Error ? err.message : 'Login failed';
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [loginAsDemo]);

  const register = useCallback(async (email: string, password: string, fullName: string) => {
    setLoading(true);
    setError(null);
    try {
      await authService.register(email, password, fullName);
      await login(email, password, 'manager');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [login]);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: user !== null,
        loading,
        restoring,
        error,
        login,
        loginAsDemo,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
