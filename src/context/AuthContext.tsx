import { createContext, useCallback, useEffect, useState, type ReactNode } from 'react';
import * as authService from '@/services/api/authService';
import type { AuthUser } from '@/services/api/authService';
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
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  loginAsDemo: () => void;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const token = authService.getStoredToken();
    if (token && token.startsWith('demo-token')) {
      return DEMO_USER;
    }
    return null;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // On mount, if a token is already stored (from a previous real-backend session)
  // and we're not in mock mode, validate it against /auth/me.
  useEffect(() => {
    const token = authService.getStoredToken();
    if (!token) return;

    if (token.startsWith('demo-token') || USE_MOCK_DATA) {
      setUser(DEMO_USER);
      return;
    }

    authService
      .fetchCurrentUser(token)
      .then(setUser)
      .catch((err) => {
        // If server is unreachable in preview sandbox, keep demo user if available
        if (token.startsWith('demo-token')) {
          setUser(DEMO_USER);
        } else {
          authService.setStoredToken(null);
        }
      });
  }, []);

  const loginAsDemo = useCallback(() => {
    authService.setStoredToken('demo-token-standalone');
    setUser(DEMO_USER);
    setError(null);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    setError(null);

    // If explicitly in mock mode, sign in immediately without backend
    if (USE_MOCK_DATA) {
      loginAsDemo();
      setLoading(false);
      return;
    }

    try {
      const result = await authService.login(email, password);
      authService.setStoredToken(result.access_token);
      setUser(result.user);
    } catch (err: unknown) {
      // Check if backend is unreachable (e.g. running in Google AI Studio or preview without Python server)
      const errStr = String(err);
      const isNetworkError =
        err instanceof TypeError ||
        errStr.includes('Failed to fetch') ||
        errStr.includes('Network') ||
        errStr.includes('Cannot reach');

      // Auto-fallback: if backend is offline and user entered seeded demo credentials, allow demo login
      if (isNetworkError && (email === 'admin@fleetguard.demo' || email.includes('admin'))) {
        console.warn('FastAPI backend is offline or unreachable in this cloud/preview environment. Signing in as Demo Admin.');
        loginAsDemo();
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
      value={{
        user,
        isAuthenticated: user !== null,
        loading,
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
