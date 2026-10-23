// Single source of truth for whether services return mock data or call the
// real FastAPI backend. In Phase 1 this is always true; Phase 2 flips the
// VITE_USE_MOCK env var without touching any component or page.
export const USE_MOCK_DATA: boolean = import.meta.env.VITE_USE_MOCK !== 'false';

export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api';

// Simulated network latency so loading states are visible and realistic
// even while backed by mock data.
export const MOCK_LATENCY_MS = 450;

export function mockDelay<T>(value: T, ms: number = MOCK_LATENCY_MS): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), ms));
}
