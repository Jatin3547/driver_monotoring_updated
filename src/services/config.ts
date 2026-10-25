// Single source of truth for whether services return mock data or call the
// real FastAPI backend. In Phase 1 this is always true; Phase 2 flips the
// VITE_USE_MOCK env var without touching any component or page.
export const USE_MOCK_DATA: boolean = import.meta.env.VITE_USE_MOCK !== 'false';

// Auto-detect API base URL:
// In browser environments loaded over HTTPS (such as Google AI Studio, cloud previews),
// use the proxied relative '/api' path to avoid Mixed Content (HTTPS -> HTTP) blocking.
const getDetectedApiBaseUrl = (): string => {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL;
  }
  if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
    return `${window.location.origin}/api`;
  }
  return 'http://localhost:8000/api';
};

export const API_BASE_URL: string = getDetectedApiBaseUrl();

// Simulated network latency so loading states are visible and realistic
// even while backed by mock data.
export const MOCK_LATENCY_MS = 450;

export function mockDelay<T>(value: T, ms: number = MOCK_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}
