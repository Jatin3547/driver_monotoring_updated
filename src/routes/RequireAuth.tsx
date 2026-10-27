import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { USE_MOCK_DATA } from '@/services/config';

/**
 * In demo mode (VITE_USE_MOCK=true) every page stays open, matching the
 * original Phase 1 UX — there is no real session to protect. Once
 * connected to the real backend (VITE_USE_MOCK=false), pages require a
 * valid JWT session; unauthenticated visitors are redirected to /login.
 *
 * While the session is being restored (token validation in-flight),
 * render nothing to avoid a flash redirect to /login.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, restoring } = useAuth();

  if (USE_MOCK_DATA || isAuthenticated) {
    return <>{children}</>;
  }

  // Session restore in progress — don't redirect yet
  if (restoring) {
    return null;
  }

  return <Navigate to="/login" replace />;
}
