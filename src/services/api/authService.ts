import { API_BASE_URL } from '../config';

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  driver_code?: string | null;
}

export type LoginPortal = 'manager' | 'driver';

export interface LoginResult {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

const TOKEN_KEY = 'fleetguard_token';

function responseMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== 'object') return fallback;
  const detail = (payload as { detail?: unknown }).detail;
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      if (typeof item === 'string') return item;
      if (item && typeof item === 'object') {
        const message = (item as { msg?: unknown }).msg;
        return typeof message === 'string' ? message : null;
      }
      return null;
    }).filter((message): message is string => Boolean(message));
    if (messages.length) return messages.join('; ');
  }
  if (detail && typeof detail === 'object') {
    const message = (detail as { message?: unknown }).message;
    if (typeof message === 'string' && message.trim()) return message;
  }
  return fallback;
}

export function getStoredToken(): string | null {
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string | null): void {
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

/** Real backend call. The FastAPI login route uses OAuth2PasswordRequestForm,
 * which expects application/x-www-form-urlencoded — not JSON — so this
 * bypasses the shared JSON apiClient and builds the request directly. */
export async function login(
  email: string,
  password: string,
  portal?: LoginPortal,
): Promise<LoginResult> {
  const body = new URLSearchParams();
  body.set('username', email);
  body.set('password', password);
  if (portal) body.set('scope', portal);

  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(responseMessage(detail, `Login failed (${res.status})`));
  }
  return res.json() as Promise<LoginResult>;
}

export async function register(email: string, password: string, fullName: string): Promise<AuthUser> {
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(responseMessage(detail, `Registration failed (${res.status})`));
  }
  return res.json() as Promise<AuthUser>;
}

export async function fetchCurrentUser(token: string): Promise<AuthUser> {
  const res = await fetch(`${API_BASE_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error('Session expired');
  return res.json() as Promise<AuthUser>;
}
