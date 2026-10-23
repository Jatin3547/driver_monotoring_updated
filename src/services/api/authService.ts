import { API_BASE_URL } from '../config';

export interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

export interface LoginResult {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

const TOKEN_KEY = 'fleetguard_token';

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
export async function login(email: string, password: string): Promise<LoginResult> {
  const body = new URLSearchParams();
  body.set('username', email);
  body.set('password', password);

  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });

  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.detail ?? `Login failed (${res.status})`);
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
    throw new Error(detail.detail ?? `Registration failed (${res.status})`);
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
