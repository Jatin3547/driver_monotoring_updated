export const MANAGER_ROLES = new Set(['fleet_admin', 'admin', 'manager']);

export function isManagerRole(role: string | undefined | null): boolean {
  return !!role && MANAGER_ROLES.has(role);
}

export function isDriverRole(role: string | undefined | null): boolean {
  return role === 'driver';
}

export function homePathForRole(role: string | undefined | null): string {
  return isDriverRole(role) ? '/driver' : '/';
}
