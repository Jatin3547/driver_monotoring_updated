import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { homePathForRole, isDriverRole, isManagerRole } from '@/utils/roles';

type Allowed = 'manager' | 'driver';

export function RequireRole({ allow, children }: { allow: Allowed; children: ReactNode }) {
  const { user } = useAuth();
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  const ok = allow === 'manager' ? isManagerRole(user.role) : isDriverRole(user.role);
  if (!ok) {
    return <Navigate to={homePathForRole(user.role)} replace />;
  }
  return <>{children}</>;
}
