import { API_BASE_URL } from '../config';
import { getStoredToken, setStoredToken } from './authService';

// Thin fetch wrapper used by every domain service (drivers, vehicles,
// incidents, alerts, gps, monitoring, analytics). Automatically attaches
// the JWT from authService when one is present — a no-op when the user
// hasn't logged in, since most read endpoints in this project are
// intentionally left open (see README "Authentication" section).
async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.headers ?? {}),
      },
      ...options,
    });
  } catch {
    // Network failure (backend unreachable) — surface a clear, catchable
    // error rather than an unhandled promise rejection, so pages using
    // useAsyncData show their existing ErrorState instead of crashing.
    throw new Error('Cannot reach the backend. Is it running?');
  }

  if (res.status === 401) {
    // Expired/invalid token: clear it so the app doesn't keep retrying
    // with a dead session, and let the caller's error state explain it.
    setStoredToken(null);
    window.dispatchEvent(new Event('fleetguard:unauthorized'));
    throw new Error('Your session has expired. Please sign in again.');
  }

  if (!res.ok) {
    throw new Error(`API request failed: ${res.status} ${res.statusText}`);
  }

  return res.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path, { method: 'GET' }),
  post: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};
